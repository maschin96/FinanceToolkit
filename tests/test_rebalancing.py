"""Target weights, strict thresholds and grid-frequency sensitivity."""

import numpy as np
import pytest

from finance_toolkit.simulation import GBMPaths
from finance_toolkit.strategies import simulate_rebalancing


def mk(values, times=None):
    prices = np.asarray(values, dtype=float)
    return GBMPaths(
        np.arange(prices.shape[1], dtype=float)
        if times is None
        else np.asarray(times, dtype=float),
        prices,
    )


def test_calendar_delayed_rebalance_and_buy_hold():
    m = mk([[[10], [20], [20]]])
    r = simulate_rebalancing(m, [0.5], initial_cash=100, calendar=[1])
    np.testing.assert_allclose(
        r.quantities[0, :, 0], [5, 5, 3.75], rtol=1e-12, atol=1e-10
    )
    assert r.weights[0, -1, 0] == pytest.approx(0.5)
    hold = simulate_rebalancing(m, [0.5], initial_cash=100)
    np.testing.assert_array_equal(hold.quantities[0, :, 0], [5, 5, 5])
    final = simulate_rebalancing(m, [0.5], initial_cash=100, calendar=[2])
    np.testing.assert_array_equal(final.trades, hold.trades)


def test_strict_threshold_boundary():
    m = mk([[[10], [30], [30]]])
    boundary = simulate_rebalancing(m, [0.5], initial_cash=100, threshold=0.25)
    np.testing.assert_array_equal(boundary.quantities[0, :, 0], [5, 5, 5])
    crossed = simulate_rebalancing(m, [0.5], initial_cash=100, threshold=0.249)
    assert crossed.weights[0, -1, 0] == pytest.approx(0.5)
    assert crossed.trades[0, -1, 0] < 0


def test_constant_prices_and_cost_comparison():
    m = mk([[[10, 20], [10, 20], [10, 20]]])
    r = simulate_rebalancing(m, [0.25, 0.5], initial_cash=100, calendar=[0, 1, 2])
    np.testing.assert_allclose(
        r.weights, np.broadcast_to([0.25, 0.5], (1, 3, 2)), rtol=1e-12, atol=1e-12
    )
    assert r.fees.sum() == 0
    hold = simulate_rebalancing(m, [0.25, 0.5], initial_cash=100, fixed_fee=1)
    periodic = simulate_rebalancing(
        m, [0.25, 0.5], initial_cash=100, calendar=[2], fixed_fee=1
    )
    np.testing.assert_array_equal(hold.wealth, periodic.wealth)
    np.testing.assert_array_equal(hold.fees, periodic.fees)
    np.testing.assert_allclose(hold.wealth, 98, rtol=0, atol=1e-10)


def test_pathwise_decisions():
    m = mk([[[10], [30], [30]], [[10], [10], [10]]])
    r = simulate_rebalancing(m, [0.5], initial_cash=100, threshold=0.1)
    assert r.quantities[0, -1, 0] < r.quantities[1, -1, 0]


def test_grid_frequency_sensitivity_is_not_invariance():
    coarse = mk([[[10], [20], [30]]], [0, 1, 2])
    fine = mk([[[10], [15], [20], [25], [30]]], [0, 0.5, 1, 1.5, 2])
    c = simulate_rebalancing(coarse, [0.5], initial_cash=100, calendar=[0, 1])
    f = simulate_rebalancing(fine, [0.5], initial_cash=100, calendar=[0, 0.5, 1, 1.5])
    assert np.isfinite(c.wealth).all() and np.isfinite(f.wealth).all()
    assert c.wealth[0, -1] != f.wealth[0, -1]
    assert np.count_nonzero(f.trades) > np.count_nonzero(c.trades)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"calendar": [0.5]},
        {"calendar": [-1]},
        {"calendar": [1, 1]},
        {"calendar": [[1]]},
        {"threshold": 0},
        {"threshold": np.nan},
        {"threshold": 1.1},
        {"calendar": [1], "threshold": 0.1},
    ],
)
def test_invalid_rule(kwargs):
    with pytest.raises(ValueError):
        simulate_rebalancing(
            mk([[[10], [20], [20]]]), [0.5], initial_cash=100, **kwargs
        )


def test_threshold_includes_cash_remainder():
    m = mk([[[10, 10], [20, 20], [20, 20]]])
    result = simulate_rebalancing(m, [0.4, 0.4], initial_cash=100, threshold=0.05)
    # Each stock changes by only 4.44pp, cash changes by 8.89pp.
    np.testing.assert_allclose(
        result.weights[0, -1], [0.4, 0.4], rtol=1e-12, atol=1e-12
    )
