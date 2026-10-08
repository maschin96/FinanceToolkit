import numpy as np
import pytest

from finance_toolkit.options_book import Order, simulate_book
from finance_toolkit.portfolio import Stock
from finance_toolkit.simulation import GBMPaths


def market():
    return GBMPaths(
        np.array([0.0, 0.5, 1.0]), np.array([100.0, 110.0, 120.0])[None, :, None]
    )


def test_positive_and_negative_cash_continuous_finance():
    positive = simulate_book(market(), (Stock(),), initial_cash=100, lending_rate=0.1)
    np.testing.assert_allclose(
        positive.cash[0], 100 * np.exp(0.1 * market().times), rtol=1e-14
    )
    negative = simulate_book(
        market(),
        (Stock(),),
        initial_cash=0,
        initial_orders=(Order(0, 1),),
        allow_borrowing=True,
        borrowing_rate=0.2,
    )
    np.testing.assert_allclose(
        negative.cash[0], -100 * np.exp(0.2 * market().times), rtol=1e-14
    )
    np.testing.assert_allclose(
        negative.financing[0, 1:], np.diff(negative.cash[0]), rtol=1e-14
    )


def test_short_stock_borrow_cost_left_endpoint_notional():
    book = simulate_book(
        market(),
        (Stock(),),
        initial_cash=100,
        initial_orders=(Order(0, -2, fee=1),),
        allow_short_stocks=True,
        stock_borrow_rate=0.1,
        signal=lambda s: (Order(0, 1, fee=2),) if s.time == 0 else None,
    )
    # Borrow: 2*100*.1*.5=10, then 1*110*.1*.5=5.5.
    np.testing.assert_allclose(book.stock_borrow_costs[0, :, 0], [0, 10, 5.5])
    np.testing.assert_allclose(book.cash[0], [299, 177, 171.5])
    np.testing.assert_allclose(book.quantities[0, :, 0], [-2, -1, -1])
    assert book.wealth[0, -1] == 51.5


def test_nonpositive_wealth_preserves_absolute_values_rejects_weights():
    book = simulate_book(
        market(),
        (Stock(),),
        initial_cash=0,
        initial_orders=(Order(0, -1),),
        allow_short_stocks=True,
    )
    np.testing.assert_equal(book.wealth[0], [0, -10, -20])
    with pytest.raises(ValueError, match="positive"):
        _ = book.weights


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(stock_borrow_rate=-1),
        dict(allow_borrowing=1),
        dict(lending_rate=float("nan")),
    ],
)
def test_invalid_finance(kwargs):
    with pytest.raises(ValueError):
        simulate_book(market(), (Stock(),), initial_cash=100, **kwargs)
