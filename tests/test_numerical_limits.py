"""Public results must be finite or fail explicitly, without runtime warnings."""

import warnings
from dataclasses import replace

import numpy as np
import pytest

from finance_toolkit.analytics import analyze_portfolio, portfolio_returns, tail_risk
from finance_toolkit.attribution import attribute_book, explain_option_move
from finance_toolkit.hedge_lab import ComparisonCase, compare_hedges
from finance_toolkit.option_strategies import OptionStrategy, build_strategy
from finance_toolkit.options_book import Order, simulate_book
from finance_toolkit.portfolio import EuropeanOption, Stock, Trade, value_portfolio
from finance_toolkit.simulation import GBMPaths


@pytest.fixture(autouse=True)
def no_runtime_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        yield


def _small_book():
    return simulate_book(
        GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 2), 100.0)),
        (Stock(0), Stock(1)),
        initial_cash=1000,
    )


@pytest.mark.parametrize("quantity,end_time,end_spot", [(10, 1, 110), (1, 0.1, 120)])
def test_option_move_rejects_unrepresentable_currency_components(
    quantity, end_time, end_spot
):
    with pytest.raises(ValueError, match="unrepresentable.*attribution"):
        explain_option_move(
            EuropeanOption(0, 100, 1, 0.2, multiplier=1e308),
            quantity=quantity,
            spot_start=100,
            spot_end=end_spot,
            time_start=0,
            time_end=end_time,
            volatility_start=0.2,
            volatility_end=0.2,
            rate_start=0,
            rate_end=0,
        )


def test_option_move_rejects_overflow_in_squared_spot_shock():
    with pytest.raises(ValueError, match="unrepresentable.*attribution"):
        explain_option_move(
            EuropeanOption(0, 100, 1, 0.2, multiplier=1),
            quantity=1,
            spot_start=100,
            spot_end=1e200,
            time_start=0,
            time_end=0.1,
            volatility_start=0.2,
            volatility_end=0.2,
            rate_start=0,
            rate_end=0,
        )


def test_zero_contracts_do_not_require_extreme_taylor_components():
    result = explain_option_move(
        EuropeanOption(0, 100, 1, 0.2, multiplier=1e308),
        quantity=0,
        spot_start=100,
        spot_end=1e200,
        time_start=0,
        time_end=0.1,
        volatility_start=0.2,
        volatility_end=0.2,
        rate_start=0,
        rate_end=0,
    )
    assert all(value == 0 for name, value in result.items() if name != "event")


@pytest.mark.parametrize("name", ["protective_put", "covered_call", "collar"])
def test_builder_rejects_unrepresentable_stock_quantity(name):
    with pytest.raises(ValueError, match="strategy.*quantit"):
        build_strategy(
            name,
            lower_strike=90,
            upper_strike=110,
            maturity=1,
            volatility=0.2,
            contracts=1e308,
            multiplier=100,
        )


@pytest.mark.parametrize("name", ["bull_call", "bear_put"])
def test_spread_large_quantity_is_allowed_but_currency_overflow_rejected(name):
    # Contract quantities themselves are finite; the currency payoff is not.
    strategy = build_strategy(
        name,
        lower_strike=90,
        upper_strike=110,
        maturity=1,
        volatility=0.2,
        contracts=1e308,
        multiplier=100,
    )
    with pytest.raises(ValueError, match="unrepresentable.*payoff"):
        strategy.payoff(100)


def test_signed_custom_strategy_and_zero_quantity_payoff():
    strategy = OptionStrategy("covered_call", (Stock(), Stock(1)), (-2, 0))
    np.testing.assert_array_equal(strategy.payoff([0, 100]), [0, -200])
    with pytest.raises(ValueError, match="strategy.*quantit"):
        OptionStrategy("covered_call", (Stock(),), (np.inf,))


def test_book_wealth_nets_cash_before_rejecting_large_positions():
    # +1e308 +1e308 -1e308 = 1e308 currency, independently derived.
    book = simulate_book(
        GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 2), 1e308)),
        (Stock(0), Stock(1)),
        initial_cash=1e308,
        initial_orders=(Order(0, 1), Order(1, 1)),
        allow_borrowing=True,
    )
    np.testing.assert_allclose(book.wealth, 1e308, rtol=2e-15, atol=0)
    np.testing.assert_allclose(book.weights, 1, rtol=2e-15, atol=0)


def test_portfolio_wealth_nets_large_positive_and_negative_currency_terms():
    small = value_portfolio(
        GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 2), 100.0)),
        (Trade(0, Stock(0), 1), Trade(0, Stock(1), 1)),
        initial_cash=1000,
    )
    for sign in (1, -1):
        paths = replace(
            small,
            cash=np.full((1, 2), -sign * 1e308),
            instrument_values=np.full((1, 2, 2), sign * 1e308),
        )
        np.testing.assert_allclose(paths.wealth, sign * 1e308, rtol=2e-15, atol=0)
    # Empty portfolios remain cash-only; ordinary offsetting shorts retain cash.
    cash_only = value_portfolio(
        GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 1), 100.0)),
        (),
        initial_cash=-5,
    )
    np.testing.assert_array_equal(cash_only.wealth, -5)


@pytest.mark.parametrize("sign", [1, -1])
def test_unrepresentable_net_wealth_is_an_explicit_error(sign):
    book = replace(
        _small_book(),
        values=np.full((1, 2, 2), sign * 1e308),
        cash=np.full((1, 2), sign * 1e308),
    )
    with pytest.raises(ValueError, match="unrepresentable.*wealth"):
        _ = book.wealth


def test_weights_reject_unrepresentable_ratio_without_losing_small_cash():
    book = replace(
        _small_book(),
        values=np.tile([1e308, -1e308], (1, 2, 1)),
        cash=np.full((1, 2), 1e-308),
    )
    np.testing.assert_array_equal(book.wealth, 1e-308)
    with pytest.raises(ValueError, match="unrepresentable.*weights"):
        _ = book.weights


def test_wealth_retry_preserves_unaffected_rows_and_rejects_nonfinite_inputs():
    book = replace(
        _small_book(),
        values=np.array([[[1e308, 1e308], [1e308, -1e308]]]),
        cash=np.array([[-1e308, 1e-308]]),
    )
    # Only the first time has an overflowing gross sum. The second still
    # retains its small cash exactly rather than scaling all rows together.
    np.testing.assert_allclose(book.wealth[0, 0], 1e308, rtol=2e-15, atol=0)
    assert book.wealth[0, 1] == 1e-308
    for invalid in (np.inf, np.nan):
        with pytest.raises(ValueError, match="unrepresentable.*wealth"):
            _ = replace(book, cash=np.full((1, 2), invalid)).wealth


def test_overflowing_gross_sum_preserves_small_net_after_exact_cancellation():
    book = simulate_book(
        GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 5), 100.0)),
        tuple(Stock(j) for j in range(5)),
        initial_cash=0,
    )
    book = replace(
        book,
        values=np.tile([1e308, 1e308, -1e308, -1e308, 1e-308], (1, 2, 1)),
    )
    # Four identical magnitudes cancel exactly; the fifth term must survive.
    np.testing.assert_array_equal(book.wealth, 1e-308)


def test_book_attribution_properties_reject_unrepresentable_sums():
    result = attribute_book(_small_book())
    huge = np.full_like(result.market, 1e308)
    for changed, property_name in [
        (replace(result, delta=huge, gamma=huge), "approximation"),
        (replace(result, market=huge), "reconciled"),
    ]:
        with pytest.raises(ValueError, match="unrepresentable.*attribution"):
            getattr(changed, property_name)


def test_book_attribution_rejects_unrepresentable_interval_pnl():
    book = replace(_small_book(), cash=np.array([[-1e308, 1e308]]))
    with pytest.raises(ValueError, match="unrepresentable.*attribution"):
        attribute_book(book)


def test_comparison_rejects_unrepresentable_metric_aggregation():
    with pytest.raises(ValueError, match="unrepresentable.*metric"):
        compare_hedges(
            GBMPaths(np.array([0.0, 1.0]), np.full((2, 2, 1), 100.0)),
            (ComparisonCase("none"),),
            initial_cash=1e308,
        )


def test_existing_analysis_overflow_signals_remain_explicit():
    with pytest.raises(ValueError):
        portfolio_returns([1e308], initial_value=1e-308)
    with pytest.raises(ValueError):
        tail_risk([-1e308, 1e308])
    portfolio = value_portfolio(
        GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 1), 100.0)),
        (),
        initial_cash=1e308,
    )
    with pytest.raises(ValueError):
        analyze_portfolio(replace(portfolio, cash=np.array([[1e308, -1e308]])))
