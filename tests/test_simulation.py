"""GBM expectations derived from its analytic solution, not implementation output."""

from decimal import Decimal

import numpy as np
import pytest

from finance_toolkit.simulation import simulate_gbm


def test_zero_volatility_matches_deterministic_growth() -> None:
    result = simulate_gbm(
        [100.0, 80.0],
        drift=[0.05, -0.02],
        volatility=0.0,
        horizon=2.0,
        steps=4,
        paths=3,
        seed=7,
    )
    np.testing.assert_array_equal(result.times, [0.0, 0.5, 1.0, 1.5, 2.0])
    assert result.prices.shape == (3, 5, 2)
    expected = np.array([100.0, 80.0]) * np.exp(
        result.times[:, None] * np.array([0.05, -0.02])
    )
    np.testing.assert_allclose(
        result.prices, np.broadcast_to(expected, (3, 5, 2)), rtol=1e-13, atol=1e-12
    )


def test_seeded_single_asset_paths_are_positive_and_random() -> None:
    args = dict(drift=0.07, volatility=0.3, horizon=1.0, steps=12, paths=20)
    first = simulate_gbm(100.0, seed=42, **args)
    second = simulate_gbm(100.0, seed=42, **args)
    other = simulate_gbm(100.0, seed=43, **args)
    assert first.prices.shape == (20, 13, 1)
    np.testing.assert_array_equal(first.prices, second.prices)
    np.testing.assert_array_equal(first.prices[:, 0, 0], 100.0)
    assert np.all(first.prices > 0.0)
    assert not np.array_equal(first.prices, other.prices)
    assert np.std(first.prices[:, -1, 0]) > 0.0


@pytest.mark.parametrize("paths", [4_000, 40_000])
def test_terminal_logreturn_moments(paths: int) -> None:
    mu, sigma, horizon = 0.08, 0.25, 2.0
    result = simulate_gbm(
        100.0,
        drift=mu,
        volatility=sigma,
        horizon=horizon,
        steps=8,
        paths=paths,
        seed=51,
    )
    returns = np.log(result.prices[:, -1, 0] / 100.0)
    expected_mean = (mu - sigma**2 / 2.0) * horizon
    expected_var = sigma**2 * horizon
    # Six analytic standard errors; fixed before running the simulator.
    assert abs(returns.mean() - expected_mean) < 6 * np.sqrt(expected_var / paths)
    assert abs(returns.var(ddof=1) - expected_var) < (
        6 * expected_var * np.sqrt(2 / (paths - 1))
    )


@pytest.mark.parametrize("rho", [0.0, 0.65])
def test_correlated_logreturns_have_analytic_covariance(rho: float) -> None:
    paths, horizon = 60_000, 1.5
    sigma = np.array([0.2, 0.4])
    result = simulate_gbm(
        [100.0, 50.0],
        drift=[0.05, -0.01],
        volatility=sigma,
        horizon=horizon,
        steps=6,
        paths=paths,
        seed=9,
        correlation=None if rho == 0.0 else [[1.0, rho], [rho, 1.0]],
    )
    returns = np.log(result.prices[:, -1, :] / [100.0, 50.0])
    expected = sigma[:, None] * sigma[None, :] * horizon * [[1.0, rho], [rho, 1.0]]
    # Normal sample covariance standard errors (Wishart distribution).
    errors = np.sqrt(
        (expected**2 + np.diag(expected)[:, None] * np.diag(expected)[None, :])
        / (paths - 1)
    )
    assert np.all(np.abs(np.cov(returns.T) - expected) < 6 * errors)


@pytest.mark.parametrize("rho", [-1.0, 1.0])
def test_singular_correlation_is_supported(rho: float) -> None:
    result = simulate_gbm(
        [1.0, 1.0],
        drift=0.02,
        volatility=0.2,
        horizon=1.0,
        steps=5,
        paths=10,
        seed=3,
        correlation=[[1.0, rho], [rho, 1.0]],
    )
    # mu=sigma²/2 makes log drift zero.
    logs = np.log(result.prices)
    np.testing.assert_allclose(logs[:, :, 0], rho * logs[:, :, 1], atol=1e-14)


def test_zero_horizon_and_generator_ownership() -> None:
    rng = np.random.default_rng(22)
    control = np.random.default_rng(22)
    result = simulate_gbm(
        [2.0, 3.0],
        drift=0.1,
        volatility=0.4,
        horizon=0.0,
        steps=4,
        paths=2,
        rng=rng,
    )
    np.testing.assert_array_equal(result.prices, np.broadcast_to([2.0, 3.0], (2, 5, 2)))
    assert rng.random() == control.random()
    args = dict(drift=0.05, volatility=0.2, horizon=1.0, steps=4, paths=5)
    first = simulate_gbm(1.0, rng=rng, **args)
    second = simulate_gbm(1.0, rng=rng, **args)
    assert not np.array_equal(first.prices, second.prices)


@pytest.mark.parametrize(
    "overrides",
    [
        {"spot": 0.0},
        {"spot": -1.0},
        {"spot": np.nan},
        {"spot": []},
        {"spot": [[1.0]]},
        {"volatility": -0.1},
        {"volatility": np.inf},
        {"drift": np.nan},
        {"drift": [0.1, 0.2]},
        {"horizon": -1.0},
        {"horizon": np.inf},
        {"horizon": "one"},
        {"horizon": True},
        {"steps": 0},
        {"steps": 1.5},
        {"steps": True},
        {"paths": -1},
        {"paths": False},
        {"seed": -1},
        {"seed": 1.5},
        {"seed": 1, "rng": np.random.default_rng(1)},
        {"rng": 1},
        {"correlation": [[0.9]]},
        {"correlation": [[np.nan]]},
        {"correlation": [[1.0, 0.0], [0.0, 1.0]]},
        {"drift": 1e308},
        {"volatility": 1e308},
        {"drift": -1e308},
    ],
)
def test_invalid_parameters_are_rejected(overrides: dict) -> None:
    args = dict(spot=100.0, drift=0.05, volatility=0.2, horizon=1.0, steps=2, paths=3)
    args.update(overrides)
    with pytest.raises(ValueError):
        simulate_gbm(**args)


@pytest.mark.parametrize(
    "correlation",
    [
        [[1.0, 0.5], [0.0, 1.0]],
        [[1.0, 1.1], [1.1, 1.0]],
        [[1.0, np.inf], [np.inf, 1.0]],
    ],
)
def test_invalid_multiasset_correlation_is_rejected(correlation: list) -> None:
    with pytest.raises(ValueError):
        simulate_gbm(
            [1.0, 2.0],
            drift=0.05,
            volatility=0.2,
            horizon=1.0,
            steps=2,
            paths=3,
            correlation=correlation,
        )


def test_price_mean_and_independent_time_increments() -> None:
    paths, sigma, mu, horizon = 40_000, 0.3, 0.04, 2.0
    result = simulate_gbm(
        100.0,
        drift=mu,
        volatility=sigma,
        horizon=horizon,
        steps=2,
        paths=paths,
        seed=191,
    )
    expected_mean = 100.0 * np.exp(mu * horizon)
    expected_variance = expected_mean**2 * np.expm1(sigma**2 * horizon)
    assert abs(result.prices[:, -1, 0].mean() - expected_mean) < (
        6 * np.sqrt(expected_variance / paths)
    )
    increments = np.diff(np.log(result.prices[:, :, 0]), axis=1)
    assert abs(np.corrcoef(increments.T)[0, 1]) < 6 / np.sqrt(paths)


def test_deterministic_simulation_does_not_advance_random_state() -> None:
    rng = np.random.default_rng(91)
    control = np.random.default_rng(91)
    global_before = np.random.get_state()
    simulate_gbm(
        100.0,
        drift=0.05,
        volatility=0.0,
        horizon=1.0,
        steps=4,
        paths=3,
        rng=rng,
    )
    assert rng.random() == control.random()
    simulate_gbm(
        100.0,
        drift=0.05,
        volatility=0.2,
        horizon=1.0,
        steps=4,
        paths=3,
        seed=123,
    )
    global_after = np.random.get_state()
    np.testing.assert_array_equal(global_before[1], global_after[1])
    assert global_before[0] == global_after[0]
    assert global_before[2:] == global_after[2:]


def test_indefinite_three_asset_correlation_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive semidefinite"):
        simulate_gbm(
            [1.0, 2.0, 3.0],
            drift=0.0,
            volatility=0.2,
            horizon=1.0,
            steps=3,
            paths=2,
            correlation=[[1.0, 0.9, 0.9], [0.9, 1.0, -0.9], [0.9, -0.9, 1.0]],
        )


def test_representable_prices_survive_extreme_initial_scale() -> None:
    # exp(-750) underflows by itself; multiplying by 1e300 has finite true result.
    result = simulate_gbm(
        1e300,
        drift=-750.0,
        volatility=0.0,
        horizon=1.0,
        steps=1,
        paths=1,
    )
    np.testing.assert_array_equal(result.prices[:, 0, 0], 1e300)
    np.testing.assert_allclose(
        result.prices[0, -1, 0],
        float(Decimal("1e300") * Decimal(-750).exp()),
        rtol=1e-13,
    )
