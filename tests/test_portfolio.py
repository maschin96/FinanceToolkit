"""Portfolio cash book: independent hand-calculated balances."""

import numpy as np
import pytest

from finance_toolkit.instruments.bonds import Bond
from finance_toolkit.portfolio import EuropeanOption, Stock, Trade, value_portfolio
from finance_toolkit.simulation import GBMPaths


def market(times: list, spots: list) -> GBMPaths:
    return GBMPaths(
        np.array(times, dtype=float), np.array(spots, dtype=float)[None, :, None]
    )


def test_stock_roundtrip_fees_and_wealth() -> None:
    result = value_portfolio(
        market([0, 1, 2], [100, 110, 120]),
        [Trade(0, Stock(), 2, fee=1), Trade(1, Stock(), -2, fee=2)],
        initial_cash=1000,
    )
    np.testing.assert_allclose(result.cash, [[799, 1017, 1017]], atol=1e-12)
    np.testing.assert_allclose(result.wealth, [[999, 1017, 1017]], atol=1e-12)
    np.testing.assert_allclose(result.trade_cashflows, [[-200, 220, 0]])
    np.testing.assert_allclose(result.fee_cashflows, [[-1, -2, 0]])
    np.testing.assert_array_equal(result.quantities[:, 0], [2, 0, 0])


def test_option_premium_multiplier_and_settlement_once() -> None:
    option = EuropeanOption(
        asset=0, strike=100, maturity=1, volatility=0.2, multiplier=10
    )
    result = value_portfolio(
        market([0, 0.5, 1, 1.5], [100, 110, 120, 130]),
        [Trade(0, option, 2, price=5)],
        initial_cash=1000,
    )
    np.testing.assert_array_equal(result.trade_cashflows, [[-100, 0, 0, 0]])
    np.testing.assert_array_equal(result.option_cashflows, [[0, 0, 400, 0]])
    np.testing.assert_array_equal(result.cash, [[900, 900, 1300, 1300]])
    assert np.all(result.instrument_values[:, 2:, :] == 0)
    assert np.all(result.quantities[2:, :] == 0)


def test_bond_coupon_redemption_and_ex_coupon_sale() -> None:
    bond = Bond(face=100, coupon_rate=0.1, maturity=2)
    result = value_portfolio(
        market([0, 1, 2, 3], [1, 1, 1, 1]),
        [Trade(0, bond, 1, price=120)],
        initial_cash=200,
        rate=0,
    )
    np.testing.assert_array_equal(result.coupon_cashflows, [[0, 10, 10, 0]])
    np.testing.assert_array_equal(result.principal_cashflows, [[0, 0, 100, 0]])
    np.testing.assert_array_equal(result.wealth, [[200, 200, 200, 200]])
    sold = value_portfolio(
        market([0, 1, 2], [1, 1, 1]),
        [Trade(0, bond, 1, price=120), Trade(1, bond, -1)],
        initial_cash=200,
    )
    np.testing.assert_array_equal(sold.cash, [[80, 200, 200]])
    np.testing.assert_array_equal(sold.principal_cashflows, [[0, 0, 0]])


def test_long_short_symmetry_and_explicit_financing() -> None:
    paths = market([0, 1, 2], [100, 110, 90])
    long = value_portfolio(paths, [Trade(0, Stock(), 1)], initial_cash=0)
    short = value_portfolio(paths, [Trade(0, Stock(), -1)], initial_cash=0)
    np.testing.assert_allclose(long.wealth, -short.wealth, atol=1e-12)
    borrowed = value_portfolio(
        paths, [Trade(0, Stock(), 2)], initial_cash=100, borrowing_rate=0.1
    )
    assert borrowed.cash[0, 1] == pytest.approx(-100 * np.exp(0.1))
    lent = value_portfolio(paths, [], initial_cash=100, lending_rate=0.03)
    assert lent.cash[0, 2] == pytest.approx(100 * np.exp(0.06))


def test_multiple_paths_rate_scenarios_and_initial_trade_value() -> None:
    market_paths = GBMPaths(
        np.array([0, 1, 2.0]),
        np.array([[[100.0], [110.0], [120.0]], [[100.0], [90.0], [80.0]]]),
    )
    option = EuropeanOption(
        asset=0, strike=100, maturity=2, volatility=0.2, multiplier=1
    )
    result = value_portfolio(
        market_paths, [Trade(0, option, 1)], initial_cash=100, rate=[0.03, 0.04, 0.05]
    )
    np.testing.assert_allclose(result.wealth[:, 0], 100, atol=1e-12)
    assert result.wealth.shape == (2, 3)
    assert result.wealth[0, -1] > result.wealth[1, -1]
    # No drift appears in the portfolio evaluator: repricing uses risk-free curve.


@pytest.mark.parametrize(
    "trades",
    [
        [Trade(0.2, Stock(), 1)],
        [Trade(0, Stock(asset=1), 1)],
        [Trade(1, EuropeanOption(asset=0, strike=100, maturity=1, volatility=0.2), 1)],
        [Trade(0, Bond(face=100, coupon_rate=0.05, maturity=1, frequency=2), 1)],
    ],
)
def test_missing_times_or_invalid_asset_rejected(trades: list) -> None:
    with pytest.raises(ValueError):
        value_portfolio(market([0, 1, 2], [100, 110, 120]), trades, initial_cash=1000)


@pytest.mark.parametrize(
    "overrides",
    [
        {"quantity": 0},
        {"quantity": np.inf},
        {"time": -1},
        {"fee": -1},
        {"price": -1},
        {"price": np.nan},
    ],
)
def test_invalid_trade_parameters(overrides: dict) -> None:
    args = dict(time=0, instrument=Stock(), quantity=1)
    args.update(overrides)
    with pytest.raises(ValueError):
        Trade(**args)


@pytest.mark.parametrize(
    "overrides",
    [
        {"strike": 0},
        {"maturity": 0},
        {"volatility": -1},
        {"multiplier": 0},
        {"kind": "other"},
        {"asset": -1},
    ],
)
def test_invalid_option_position(overrides: dict) -> None:
    args = dict(asset=0, strike=100, maturity=1, volatility=0.2)
    args.update(overrides)
    with pytest.raises(ValueError):
        EuropeanOption(**args)


def test_invalid_market_paths_or_rates_rejected() -> None:
    for paths in [
        market([0, 0], [100, 110]),
        market([1, 2], [100, 110]),
        market([0, 1], [100, -1]),
    ]:
        with pytest.raises(ValueError):
            value_portfolio(paths, [], initial_cash=100)
    with pytest.raises(ValueError):
        value_portfolio(market([0, 1], [100, 110]), [], initial_cash=100, rate=np.nan)


@pytest.mark.parametrize(
    "instrument",
    [
        Bond(face=100, coupon_rate=0.1, maturity=2),
        EuropeanOption(asset=0, strike=100, maturity=2, volatility=0.2, multiplier=10),
    ],
)
def test_short_instrument_settlement_is_symmetric(instrument: object) -> None:
    paths = market([0, 1, 2, 3], [100, 110, 120, 130])
    long = value_portfolio(paths, [Trade(0, instrument, 1)], initial_cash=0)
    short = value_portfolio(paths, [Trade(0, instrument, -1)], initial_cash=0)
    np.testing.assert_allclose(long.wealth, -short.wealth, atol=1e-10)
    np.testing.assert_allclose(long.cash, -short.cash, atol=1e-10)
    assert long.instrument_values[0, -1, 0] == short.instrument_values[0, -1, 0] == 0


def test_full_cash_book_reconciles_and_new_holder_gets_no_past_coupon() -> None:
    bond = Bond(face=100, coupon_rate=0.1, maturity=2)
    result = value_portfolio(
        market([0, 1, 2, 3], [100, 110, 120, 130]),
        [Trade(0, Stock(), 1, fee=1), Trade(1, bond, 2, fee=2)],
        initial_cash=1000,
        lending_rate=0.02,
    )
    assert result.coupon_cashflows[0, 1] == 0
    assert result.coupon_cashflows[0, 2] == 20
    flows = (
        result.trade_cashflows
        + result.fee_cashflows
        + result.coupon_cashflows
        + result.principal_cashflows
        + result.option_cashflows
        + result.financing_cashflows
    )
    np.testing.assert_allclose(result.cash, 1000 + np.cumsum(flows, axis=1), atol=1e-10)


def test_model_repricing_uses_rate_and_remaining_maturity() -> None:
    option = EuropeanOption(asset=0, strike=90, maturity=2, volatility=0, multiplier=1)
    result = value_portfolio(
        market([0, 1, 2], [100, 100, 100]),
        [Trade(0, option, 1)],
        initial_cash=100,
        rate=0.1,
    )
    expected_cash = 90 * np.exp(-0.2)
    np.testing.assert_allclose(
        result.instrument_values[0, :, 0],
        [100 - 90 * np.exp(-0.2), 100 - 90 * np.exp(-0.1), 0],
        atol=1e-11,
    )
    np.testing.assert_allclose(
        result.cash, [[expected_cash, expected_cash, expected_cash + 10]], atol=1e-11
    )
