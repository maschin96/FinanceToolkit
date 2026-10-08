"""Independent one-path ledger, prefix and cash constraint references."""

import numpy as np
import pytest

from finance_toolkit.simulation import GBMPaths
from finance_toolkit.strategies import simulate_strategy


def market(prices, times=None):
    prices = np.asarray(prices, dtype=float)
    return GBMPaths(
        np.arange(prices.shape[1], dtype=float)
        if times is None
        else np.array(times, dtype=float),
        prices,
    )


def test_delayed_execution_hand_ledger():
    m = market([[[10], [20], [20]]])

    def signal(state):
        return [float(state.wealth) * 0.5 / state.spots[0]]

    r = simulate_strategy(m, signal, initial_cash=100, initial_weights=[0.5])
    np.testing.assert_allclose(
        r.quantities[0, :, 0], [5, 5, 3.75], rtol=1e-12, atol=1e-10
    )
    np.testing.assert_allclose(r.cash[0], [50, 50, 75], rtol=1e-12, atol=1e-10)
    np.testing.assert_allclose(r.wealth[0], [100, 150, 150], rtol=1e-12, atol=1e-10)
    np.testing.assert_allclose(r.trades[0, :, 0], [5, 0, -1.25], rtol=1e-12, atol=1e-10)


def test_fees_and_no_null_orders():
    m = market([[[10], [10], [10]]])
    r = simulate_strategy(
        m,
        lambda s: s.quantities,
        initial_cash=100,
        initial_weights=[0.5],
        fixed_fee=1,
        proportional_fee=0.01,
    )
    np.testing.assert_allclose(r.cash[0], [48.5] * 3, rtol=1e-12, atol=1e-10)
    np.testing.assert_allclose(r.wealth[0], [98.5] * 3, rtol=1e-12, atol=1e-10)
    np.testing.assert_allclose(r.fees[0, :, 0], [1.5, 0, 0], rtol=1e-12, atol=1e-10)
    assert r.turnover.sum() == 50


def test_cash_limited_purchase_and_sell_first():
    m = market([[[10, 10], [20, 10], [20, 10]]])

    def signal(state):
        return [0, 100]

    r = simulate_strategy(
        m, signal, initial_cash=100, initial_weights=[1, 0], fixed_fee=1
    )
    assert np.all(r.cash >= 0)
    assert np.all(r.quantities >= 0)
    assert r.trades[0, 1, 0] < 0
    assert r.trades[0, 1, 1] > 0
    assert r.quantities[0, 1, 1] < 100
    np.testing.assert_allclose(
        r.wealth[0, 1],
        r.wealth[0, 0] + r.quantities[0, 0, 0] * 10 - r.fees[0, 1].sum(),
        rtol=1e-12,
        atol=1e-10,
    )


def test_insufficient_cash_and_unaffordable_sale():
    m = market([[[1], [0.1]]])
    r = simulate_strategy(
        m, lambda s: [0], initial_cash=1, initial_weights=[1], fixed_fee=0.5
    )
    # opening buys 0.5; sale proceeds 0.05 cannot fund a 0.5 fee
    assert r.quantities[0, 1, 0] == 0.5
    assert r.fees[0, 1, 0] == 0
    r = simulate_strategy(m, None, initial_cash=1, initial_weights=[1], fixed_fee=2)
    assert r.trades.sum() == 0
    assert r.cash[0, 0] == 1


def test_pathwise_prefix_invariance_and_state_isolation():
    m = market([[[10], [20], [30]], [[10], [20], [5]]])
    seen = []

    def signal(state):
        seen.append(state.time)
        assert not state.spots.flags.writeable
        assert not state.quantities.flags.writeable
        assert not hasattr(state, "market")
        return [0.5 * state.wealth / state.spots[0]]

    r = simulate_strategy(m, signal, initial_cash=100, initial_weights=[0.5])
    np.testing.assert_array_equal(r.quantities[0, :2], r.quantities[1, :2])
    prefix = simulate_strategy(
        GBMPaths(m.times[:2], m.prices[:, :2]),
        signal,
        initial_cash=100,
        initial_weights=[0.5],
    )
    np.testing.assert_array_equal(prefix.quantities, r.quantities[:, :2])
    assert r.quantities.shape == (2, 3, 1)
    assert seen == [0, 1, 0, 1, 0, 0]


def test_cash_financing_and_last_signal():
    m = market([[[10], [10]]], times=[0, 2])
    r = simulate_strategy(
        m, None, initial_cash=100, initial_weights=[0], lending_rate=0.03
    )
    assert r.cash[0, 1] == pytest.approx(100 * np.exp(0.06))
    r = simulate_strategy(m, lambda s: [1000], initial_cash=100, initial_weights=[0])
    assert r.trades[0, 1, 0] == 10


@pytest.mark.parametrize(
    "kwargs",
    [
        {"initial_cash": 0},
        {"initial_weights": [-0.1]},
        {"initial_weights": [1.1]},
        {"initial_weights": [0.2, 0.3]},
        {"fixed_fee": -1},
        {"proportional_fee": np.inf},
        {"lending_rate": np.nan},
    ],
)
def test_invalid_inputs(kwargs):
    args = dict(initial_cash=100, initial_weights=[0.5])
    args.update(kwargs)
    with pytest.raises(ValueError):
        simulate_strategy(market([[[10], [20]]]), None, **args)


@pytest.mark.parametrize("target", [[-1], [np.nan], [1, 2]])
def test_invalid_signal(target):
    with pytest.raises(ValueError):
        simulate_strategy(
            market([[[10], [20]]]),
            lambda s: target,
            initial_cash=100,
            initial_weights=[0.5],
        )


@pytest.mark.parametrize(
    "m",
    [
        market([[[0], [1]]]),
        market([[[1], [1]]], times=[0, 0]),
        market([[[1], [1]]], times=[1, 2]),
    ],
)
def test_invalid_market(m):
    with pytest.raises(ValueError):
        simulate_strategy(m, None, initial_cash=100, initial_weights=[0.5])


def test_numeric_overflow():
    with pytest.raises(ValueError):
        simulate_strategy(
            market([[[10], [10]]]),
            None,
            initial_cash=1e308,
            initial_weights=[0],
            lending_rate=1e308,
        )


def test_multi_asset_cashflow_conservation():
    m = market([[[10, 15], [20, 10], [12, 18], [9, 21]]])

    def signal(state):
        return np.array([0.4, 0.4]) * state.wealth / state.spots

    r = simulate_strategy(
        m,
        signal,
        initial_cash=100,
        initial_weights=[0.4, 0.4],
        fixed_fee=0.1,
        proportional_fee=0.005,
        lending_rate=0.03,
    )
    trade_cash = -(r.trades * m.prices).sum(axis=-1)
    expected = 100 + np.cumsum(trade_cash - r.fees.sum(axis=-1) + r.financing, axis=1)
    np.testing.assert_allclose(r.cash, expected, rtol=1e-12, atol=1e-10)
    np.testing.assert_allclose(
        r.quantities, np.cumsum(r.trades, axis=1), rtol=1e-12, atol=1e-10
    )
