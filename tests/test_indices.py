import numpy as np
import pytest

from finance_toolkit.indices import calculate_index


def test_hand_weight_drift_contributions_and_delayed_rebalance():
    prices = np.array([[100, 100], [120, 80], [150, 100], [150, 120]], dtype=float)
    dates = ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"]
    hold = calculate_index(
        dates, prices, tickers=["A", "B"], weights=[0.5, 0.5], base_date=dates[0]
    )
    np.testing.assert_equal(hold.levels, [100, 100, 125, 135])
    np.testing.assert_allclose(hold.weights[1], [0.6, 0.4])
    np.testing.assert_allclose(hold.contributions.sum(axis=1), hold.returns, atol=1e-14)
    rebalance = calculate_index(
        dates,
        prices,
        tickers=["A", "B"],
        weights=[0.5, 0.5],
        base_date=dates[0],
        rebalance_dates=[dates[1]],
    )
    np.testing.assert_equal(rebalance.levels, [100, 100, 125, 137.5])
    np.testing.assert_allclose(rebalance.holdings[1], [0.5, 0.5])
    np.testing.assert_allclose(rebalance.weights[2], [0.5, 0.5])
    prefix = calculate_index(
        dates[:3],
        prices[:3],
        tickers=["A", "B"],
        weights=[0.5, 0.5],
        base_date=dates[0],
        rebalance_dates=[dates[1]],
    )
    np.testing.assert_equal(prefix.levels, rebalance.levels[:3])


def test_single_asset_base_and_positive_scaled_invariance():
    dates = ["2026-01-01", "2026-01-02", "2026-01-05"]
    index = calculate_index(
        dates, [[10], [12], [15]], tickers=["A"], base_date=dates[1], base_value=200
    )
    np.testing.assert_allclose(index.levels, [200, 250], rtol=1e-14, atol=1e-12)
    assert index.levels[0] == 200


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(weights=[0.5, 0.4]),
        dict(weights=[1.1, -0.1]),
        dict(tickers=["A", "A"]),
        dict(base_date="2026-01-03"),
        dict(rebalance_dates=["2026-01-03"]),
        dict(base_value=0),
    ],
)
def test_invalid_index(kwargs):
    args = dict(tickers=["A", "B"], base_date="2026-01-01")
    args.update(kwargs)
    with pytest.raises(ValueError):
        calculate_index(["2026-01-01", "2026-01-05"], [[100, 100], [110, 90]], **args)


def test_three_assets_constant_path_and_independent_contributions():
    index = calculate_index(
        ["2026-01-01", "2026-01-02"],
        [[100, 100, 100], [110, 90, 120]],
        tickers=["A", "B", "C"],
        weights=[0.2, 0.3, 0.5],
        base_date="2026-01-01",
    )
    np.testing.assert_allclose(index.contributions[1], [0.02, -0.03, 0.10], atol=1e-14)
    assert index.levels[1] == pytest.approx(109, abs=1e-12)
    constant = calculate_index(
        ["2026-01-01", "2026-01-02"],
        [[100, 100, 100], [100, 100, 100]],
        tickers=["A", "B", "C"],
        base_date="2026-01-01",
    )
    np.testing.assert_allclose(constant.levels, [100, 100], atol=1e-12)


def test_future_rebalance_schedule_does_not_affect_prefix():
    result = calculate_index(
        ["2026-01-01", "2026-01-02"],
        [[100], [110]],
        tickers=["A"],
        base_date="2026-01-01",
        rebalance_dates=["2026-02-02"],
    )
    assert result.rebalance_executions == ()
