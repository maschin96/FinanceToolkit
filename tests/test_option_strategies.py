import numpy as np
import pytest

from finance_toolkit.option_strategies import build_strategy
from finance_toolkit.options_book import simulate_book
from finance_toolkit.portfolio import value_portfolio
from finance_toolkit.simulation import GBMPaths


@pytest.mark.parametrize(
    "name,expected",
    [
        ("protective_put", [90, 90, 100, 110, 120]),
        ("covered_call", [80, 90, 100, 110, 110]),
        ("collar", [90, 90, 100, 110, 110]),
        ("bull_call", [0, 0, 10, 20, 20]),
        ("bear_put", [20, 20, 10, 0, 0]),
    ],
)
def test_algebraic_payoffs(name, expected):
    strategy = build_strategy(
        name,
        lower_strike=90,
        upper_strike=110,
        maturity=1,
        volatility=0.2,
        contracts=2,
        multiplier=10,
    )
    spots = np.array([80, 90, 100, 110, 120], dtype=float)
    np.testing.assert_equal(strategy.payoff(spots), np.array(expected) * 20)
    paths = GBMPaths(
        np.array([0.0, 1.0]), np.stack([np.full(5, 100.0), spots], axis=1)[..., None]
    )
    old = value_portfolio(paths, strategy.trades(), initial_cash=10000)
    new = simulate_book(
        paths,
        strategy.instruments,
        initial_cash=10000,
        initial_orders=strategy.orders(),
    )
    np.testing.assert_allclose(new.wealth, old.wealth, atol=1e-10, rtol=1e-14)
    np.testing.assert_equal(
        new.settlements.sum(axis=-1)[:, -1] + new.values.sum(axis=-1)[:, -1],
        strategy.payoff(spots),
    )
    close = strategy.orders(close=True)
    assert all(
        a.quantity == -b.quantity for a, b in zip(strategy.orders(), close, strict=True)
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(lower_strike=110, upper_strike=90),
        dict(contracts=0),
        dict(asset=-1),
        dict(name="unknown"),
        dict(multiplier=-1),
    ],
)
def test_invalid_builder(kwargs):
    args = dict(
        name="collar", lower_strike=90, upper_strike=110, maturity=1, volatility=0.2
    )
    args.update(kwargs)
    with pytest.raises(ValueError):
        build_strategy(**args)
