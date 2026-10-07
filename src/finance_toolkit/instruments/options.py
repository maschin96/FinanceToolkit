"""European options with continuous rates and dividend yields."""

from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import ndtr  # type: ignore[import-untyped]

from finance_toolkit._validation import finite_array

OptionKind = Literal["call", "put"]


def _kind(kind: OptionKind) -> None:
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")


def option_payoff(
    spot: ArrayLike, strike: ArrayLike, *, kind: OptionKind = "call"
) -> NDArray[np.float64]:
    """Payoff per underlying unit; broadcast spot/strike, return float64 array.

    Scalars return a zero-dimensional array. Spot must be nonnegative, strike
    positive, and both finite. Invalid parameters raise ValueError.
    """
    _kind(kind)
    s, k = np.broadcast_arrays(
        finite_array(spot, "spot"), finite_array(strike, "strike")
    )
    if np.any(s < 0) or np.any(k <= 0):
        raise ValueError("spot must be nonnegative and strike positive")
    return np.asarray(
        np.maximum(s - k if kind == "call" else k - s, 0), dtype=np.float64
    )


def black_scholes(
    spot: ArrayLike,
    strike: ArrayLike,
    maturity: ArrayLike,
    volatility: ArrayLike,
    rate: ArrayLike,
    *,
    dividend_yield: ArrayLike = 0.0,
    kind: OptionKind = "call",
) -> NDArray[np.float64]:
    """European option value per unit using Black-Scholes-Merton.

    All inputs broadcast; scalars return a zero-dimensional float64 array.
    Maturity is remaining years, sigma annualized nonnegative volatility, and
    rate/dividend_yield continuous annual decimal rates (may be negative).
    Spot can be zero; strike must be positive. At expiry return intrinsic value;
    at zero volatility return discounted deterministic forward payoff.
    This API accepts risk-free rate, never the real-world simulation drift.
    Raises ValueError for invalid inputs or unrepresentable numeric results.
    """
    _kind(kind)
    names = ("spot", "strike", "maturity", "volatility", "rate", "dividend_yield")
    values = (spot, strike, maturity, volatility, rate, dividend_yield)
    s, k, t, sigma, r, q = np.broadcast_arrays(
        *(finite_array(value, name) for value, name in zip(values, names, strict=True))
    )
    if np.any(s < 0) or np.any(k <= 0) or np.any(t < 0) or np.any(sigma < 0):
        raise ValueError(
            "spot/maturity/volatility must be nonnegative; strike positive"
        )
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            ds, dk = s * np.exp(-q * t), k * np.exp(-r * t)
            active = (s > 0) & (t > 0) & (sigma > 0)
            scale = np.where(active, sigma * np.sqrt(t), 1.0)
            # Evaluate only active inputs to avoid log(0) and sigma² overflow at T=0.
            safe_s = np.where(active, s, 1.0)
            safe_k = np.where(active, k, 1.0)
            safe_t = np.where(active, t, 0.0)
            safe_sigma = np.where(active, sigma, 0.0)
            d1 = (
                np.log(safe_s) - np.log(safe_k) + (r - q + safe_sigma**2 / 2) * safe_t
            ) / scale
            d2 = d1 - scale
            call = ds * ndtr(d1) - dk * ndtr(d2)
            put = dk * ndtr(-d2) - ds * ndtr(-d1)
            # Compute OTM directly, derive ITM through parity to reduce cancellation.
            call = np.where(ds <= dk, call, put + ds - dk)
            put = np.where(ds >= dk, put, call + dk - ds)
            analytic = call if kind == "call" else put
            deterministic = np.maximum(ds - dk if kind == "call" else dk - ds, 0)
            result = np.where(active, np.maximum(analytic, 0), deterministic)
    except FloatingPointError as error:
        raise ValueError("option parameters produce unrepresentable values") from error
    if not np.all(np.isfinite(result)):
        raise ValueError("option parameters produce unrepresentable values")
    return np.asarray(result, dtype=np.float64)
