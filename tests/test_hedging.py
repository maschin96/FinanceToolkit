import numpy as np
import pytest
from scipy.special import ndtr

from finance_toolkit.hedging import simulate_hedge
from finance_toolkit.options_book import Order
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.simulation import GBMPaths, simulate_gbm


@pytest.mark.parametrize(
    "kind,quantity", [("call", 1), ("put", 1), ("call", -1), ("put", -1)]
)
def test_signed_delayed_hedge_and_expiry_close(kind, quantity):
    option = EuropeanOption(0, 100, 1, 0.2, kind=kind, multiplier=10)
    market = GBMPaths(
        np.array([0.0, 0.5, 1.0]), np.array([100.0, 110.0, 120.0])[None, :, None]
    )
    result = simulate_hedge(
        market,
        (Stock(), option),
        initial_cash=1000,
        initial_orders=(Order(1, quantity),),
        calendar=[0, 0.5],
    )
    delta = (ndtr(0.1) - (kind == "put")) * quantity * 10
    assert result.book.trades[0, 0, 0] == 0
    assert result.book.trades[0, 1, 0] == pytest.approx(-delta, abs=1e-12)
    assert result.book.quantities[0, -1, 0] == 0
    assert result.residual_delta[0, -1, 0] == 0
    assert result.residual_delta[0, 1, 0] != 0
    np.testing.assert_allclose(
        result.book.cash,
        1000
        + np.cumsum(
            (
                result.book.trade_cashflows
                - result.book.fees
                + result.book.settlements
                - result.book.stock_borrow_costs
            ).sum(axis=-1)
            + result.book.financing,
            axis=1,
        ),
        atol=1e-10,
    )


def test_threshold_strict_and_unhedged_same_opening():
    market = GBMPaths(np.array([0.0, 0.5, 1.0]), np.full((1, 3, 1), 100.0))
    instruments = (Stock(), EuropeanOption(0, 100, 1, 0.2, multiplier=1))
    delta = float(ndtr(0.1))
    none = simulate_hedge(
        market, instruments, initial_cash=100, initial_orders=(Order(1, 1),)
    )
    equal = simulate_hedge(
        market,
        instruments,
        initial_cash=100,
        initial_orders=(Order(1, 1),),
        threshold=delta,
    )
    np.testing.assert_equal(equal.book.trades, none.book.trades)
    below = simulate_hedge(
        market,
        instruments,
        initial_cash=100,
        initial_orders=(Order(1, 1),),
        threshold=delta - 1e-6,
    )
    assert below.book.trades[0, 1, 0] < 0
    assert below.book.wealth[0, 0] == none.book.wealth[0, 0]


def test_coupled_risk_neutral_hedge_error_converges():
    fine = simulate_gbm(
        100, drift=0, volatility=0.2, horizon=1, steps=128, paths=1000, seed=314
    )
    instruments = (Stock(), EuropeanOption(0, 100, 1, 0.2, multiplier=1))
    errors = []
    for stride in (8, 1):
        market = GBMPaths(fine.times[::stride], fine.prices[:, ::stride])
        result = simulate_hedge(
            market,
            instruments,
            initial_cash=0,
            initial_orders=(Order(1, -1),),
            calendar=market.times[:-1],
        )
        errors.append(np.sqrt(np.mean(result.book.wealth[:, -1] ** 2)))
    assert errors[1] < 0.7 * errors[0]


def test_multiasset_aggregation_and_prefix_invariance():
    times = np.array([0.0, 0.25, 0.5, 1.0])
    prices = np.array([[[100.0, 80.0], [102.0, 79.0], [104.0, 82.0], [108.0, 85.0]]])
    instruments = (
        Stock(0),
        Stock(1),
        EuropeanOption(0, 100, 1, 0.2, multiplier=2),
        EuropeanOption(1, 80, 1, 0.3, kind="put", multiplier=3),
    )
    initial = (Order(2, 2), Order(3, -1))
    full = simulate_hedge(
        GBMPaths(times, prices),
        instruments,
        initial_cash=100,
        initial_orders=initial,
        calendar=times,
    )
    short = simulate_hedge(
        GBMPaths(times[:3], prices[:, :3]),
        instruments,
        initial_cash=100,
        initial_orders=initial,
        calendar=times[:3],
    )
    np.testing.assert_equal(full.book.cash[:, :3], short.book.cash)
    np.testing.assert_equal(full.book.trades[:, :3], short.book.trades)
    assert full.target_shares[0, 0, 0] < 0
    assert full.target_shares[0, 0, 1] < 0


def test_active_zero_volatility_rejected_expired_greeks_not_evaluated():
    paths = GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 1), 100.0))
    with pytest.raises(ValueError, match="positive"):
        simulate_hedge(
            paths,
            (Stock(), EuropeanOption(0, 100, 1, 0)),
            initial_cash=100,
            initial_orders=(Order(1, 1),),
            calendar=[0],
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(threshold=0),
        dict(calendar=[0.3]),
        dict(calendar=[0, 0]),
        dict(calendar=[0], threshold=1),
    ],
)
def test_invalid_hedge_rules(kwargs):
    with pytest.raises(ValueError):
        simulate_hedge(
            GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 1), 100.0)),
            (Stock(), EuropeanOption(0, 100, 1, 0.2)),
            initial_cash=100,
            **kwargs,
        )
