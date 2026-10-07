"""Exact geometric Brownian motion paths with explicit local random state."""

from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class GBMPaths:
    """Times in years and prices shaped (paths, steps + 1, assets).

    Prices use the same currency units as the supplied initial prices. The
    container is frozen; callers own the returned, writable NumPy arrays.
    """

    times: NDArray[np.float64]
    prices: NDArray[np.float64]


def _vector(
    value: ArrayLike, name: str, assets: int | None = None
) -> NDArray[np.float64]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        array = np.full(assets or 1, array.item(), dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite scalar or nonempty 1D vector")
    if assets is not None and array.size != assets:
        raise ValueError(f"{name} must have one value per asset ({assets})")
    return array


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _correlation_factor(
    correlation: ArrayLike | None, assets: int
) -> NDArray[np.float64]:
    if correlation is None:
        return np.eye(assets, dtype=np.float64)
    matrix = np.asarray(correlation, dtype=np.float64)
    tolerance = 1e-12
    if matrix.shape != (assets, assets) or not np.all(np.isfinite(matrix)):
        raise ValueError("correlation must be a finite assets-by-assets matrix")
    if not np.allclose(matrix, matrix.T, rtol=0.0, atol=tolerance):
        raise ValueError("correlation must be symmetric")
    if not np.allclose(np.diag(matrix), 1.0, rtol=0.0, atol=tolerance):
        raise ValueError("correlation must have unit diagonal")
    eigenvalues, eigenvectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    if np.min(eigenvalues) < -tolerance:
        raise ValueError("correlation must be positive semidefinite")
    # Eigensquare root also supports singular correlations, unlike Cholesky.
    return eigenvectors * np.sqrt(np.maximum(eigenvalues, 0.0))


def simulate_gbm(
    spot: ArrayLike,
    *,
    drift: ArrayLike,
    volatility: ArrayLike,
    horizon: float,
    steps: int,
    paths: int,
    correlation: ArrayLike | None = None,
    seed: int | None = None,
    rng: np.random.Generator | None = None,
) -> GBMPaths:
    """Simulate dS = mu*S*dt + sigma*S*dW using exact lognormal steps.

    ``spot`` is a positive scalar or 1D vector determining the asset count.
    ``drift`` and ``volatility`` are annualized scalars (shared by all assets)
    or matching vectors; sigma must be nonnegative. Negative drift is allowed.
    ``horizon`` is a finite nonnegative number of years; ``steps`` and ``paths``
    are positive integers. Returned times include zero and the horizon, with
    prices shaped (paths, steps + 1, assets), even for a single asset.

    ``correlation`` refers to Brownian increments, defaults to identity, and
    must be symmetric positive semidefinite with unit diagonal. Absolute
    tolerance 1e-12 accommodates floating-point eigensolver roundoff; only tiny
    negative eigenvalues within that tolerance are clipped to zero.

    Supply either a nonnegative integer ``seed`` for a fresh local generator or
    a caller-owned ``rng`` (whose state advances). With neither, use OS entropy.
    Global NumPy random state is never modified. Zero horizon or all-zero
    volatility consumes no random draws. Reproducibility assumes the same
    dependency versions, parameters and initial generator state.

    Raises ValueError for invalid parameters or nonfinite/nonpositive output
    caused by floating-point overflow/underflow. This models scenario drift;
    callers must explicitly choose r-q for risk-neutral simulations.
    """
    initial = _vector(spot, "spot")
    assets = initial.size
    mu = _vector(drift, "drift", assets)
    sigma = _vector(volatility, "volatility", assets)
    if np.any(initial <= 0.0) or np.any(sigma < 0.0):
        raise ValueError("spot must be positive and volatility nonnegative")
    if (
        isinstance(horizon, bool)
        or not isinstance(horizon, Real)
        or not np.isfinite(horizon)
        or horizon < 0.0
    ):
        raise ValueError("horizon must be finite and nonnegative")
    steps = _positive_integer(steps, "steps")
    paths = _positive_integer(paths, "paths")
    factor = _correlation_factor(correlation, assets)
    if seed is not None and (
        isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0
    ):
        raise ValueError("seed must be a nonnegative integer")
    if rng is not None and not isinstance(rng, np.random.Generator):
        raise ValueError("rng must be a numpy.random.Generator")
    if seed is not None and rng is not None:
        raise ValueError("provide either seed or rng, not both")
    generator = rng if rng is not None else np.random.default_rng(seed)
    times = np.linspace(0.0, horizon, steps + 1)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            if horizon == 0.0:
                prices = np.broadcast_to(initial, (paths, steps + 1, assets)).copy()
            else:
                log_growth = np.broadcast_to(
                    (mu - sigma**2 / 2.0) * times[:, None],
                    (paths, steps + 1, assets),
                ).copy()
                if np.any(sigma > 0.0):
                    shocks = (
                        generator.standard_normal((paths, steps, assets)) @ factor.T
                    )
                    shocks *= sigma * np.sqrt(horizon / steps)
                    log_growth[:, 1:, :] += np.cumsum(shocks, axis=1)
                prices = np.exp(np.log(initial) + log_growth)
                prices[:, 0, :] = initial
    except FloatingPointError as error:
        raise ValueError("parameters produce unrepresentable GBM prices") from error
    if not np.all(np.isfinite(prices)) or np.any(prices <= 0.0):
        raise ValueError("parameters produce unrepresentable GBM prices")
    return GBMPaths(times, prices)
