import numpy as np
import pytest

from finance_toolkit.options_book import Order, simulate_book
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.simulation import GBMPaths


def market(prices=(100, 110, 120)):
    return GBMPaths(
        np.array([0.0, 0.5, 1.0]), np.array(prices, dtype=float)[None, :, None]
    )


def test_pathwise_partial_close_and_settlement():
    option = EuropeanOption(0, 100, 1, 0.2, multiplier=10)
    result = simulate_book(
        market(),
        (option,),
        initial_cash=1000,
        initial_orders=(Order(0, 2, price=5, fee=1),),
        signal=lambda s: (Order(0, -1, price=8, fee=2),) if s.time == 0 else None,
    )
    np.testing.assert_allclose(result.quantities[0, :, 0], [2, 1, 0])
    np.testing.assert_allclose(result.cash[0], [899, 977, 1177])
    np.testing.assert_allclose(result.settlements[0, :, 0], [0, 0, 200])
    assert result.values[0, -1, 0] == 0


def test_short_put_pays_once():
    option = EuropeanOption(0, 100, 1, 0.2, kind="put", multiplier=2)
    result = simulate_book(
        market((100, 90, 80)),
        (option,),
        initial_cash=100,
        initial_orders=(Order(0, -1, price=4),),
    )
    np.testing.assert_allclose(result.cash[0], [108, 108, 68])
    assert result.settlements[0, -1, 0] == -40


def test_readonly_delayed_pathwise_state_and_prefix():
    observed = []

    def signal(state):
        assert not state.spots.flags.writeable
        assert not state.quantities.flags.writeable
        observed.append(state.time)
        return (Order(0, 1),) if state.spots[0] == 100 else None

    full = simulate_book(market(), (Stock(),), initial_cash=1000, signal=signal)
    prefix = GBMPaths(market().times[:2], market().prices[:, :2])
    short = simulate_book(prefix, (Stock(),), initial_cash=1000, signal=signal)
    np.testing.assert_equal(full.trades[:, :2], short.trades)
    np.testing.assert_equal(full.cash[:, :2], short.cash)
    assert full.trades[0, 0, 0] == 0
    assert full.trades[0, 1, 0] == 1


def test_expiry_trade_and_missing_date_rejected():
    option = EuropeanOption(0, 100, 0.5, 0.2)
    with pytest.raises(ValueError, match="expiry"):
        simulate_book(
            market(), (option,), initial_cash=1000, signal=lambda s: (Order(0, 1),)
        )
    with pytest.raises(ValueError, match="grid"):
        simulate_book(market(), (EuropeanOption(0, 100, 0.4, 0.2),), initial_cash=1000)


def test_multiple_expiries_and_execution_costs_reconcile():
    instruments = (
        EuropeanOption(0, 100, 0.5, 0.2, multiplier=2),
        EuropeanOption(0, 100, 1, 0.2, kind="put", multiplier=3),
    )
    book = simulate_book(
        market(),
        instruments,
        initial_cash=1000,
        initial_orders=(Order(0, 2, price=5), Order(1, -1, price=4)),
        fixed_fee=1,
        proportional_fee=0.01,
    )
    np.testing.assert_allclose(book.settlements[0], [[0, 0], [40, 0], [0, 0]])
    expected = 1000 + np.cumsum(
        (book.trade_cashflows - book.fees + book.settlements).sum(axis=-1), axis=1
    )
    np.testing.assert_allclose(book.cash, expected, rtol=1e-14, atol=1e-10)
    np.testing.assert_equal(book.quantities[0], [[2, -1], [0, -1], [0, 0]])


@pytest.mark.parametrize(
    "kwargs", [dict(initial_cash=-1), dict(fixed_fee=-1), dict(proportional_fee=-1)]
)
def test_invalid_capital_and_fees(kwargs):
    args = dict(initial_cash=1000)
    args.update(kwargs)
    with pytest.raises(ValueError):
        simulate_book(market(), (Stock(),), **args)


def test_complete_close_and_distinct_paths():
    prices = np.array([[[100], [110], [120]], [[90], [95], [100]]], dtype=float)
    paths = GBMPaths(np.array([0.0, 0.5, 1.0]), prices)
    option = EuropeanOption(0, 100, 1, 0.2, multiplier=1)

    def signal(state):
        return (
            (Order(0, -1, price=3),)
            if state.time == 0 and state.spots[0] == 100
            else None
        )

    book = simulate_book(
        paths,
        (option,),
        initial_cash=100,
        initial_orders=(Order(0, 1, price=2),),
        signal=signal,
    )
    np.testing.assert_equal(book.quantities[:, 1, 0], [0, 1])
    np.testing.assert_equal(book.cash[:, -1], [101, 98])


@pytest.mark.parametrize("order", [Order(1, 1), Order(0, -1), Order(0, 100)])
def test_bad_orders_rejected(order):
    with pytest.raises(ValueError):
        simulate_book(market(), (Stock(),), initial_cash=100, initial_orders=(order,))
