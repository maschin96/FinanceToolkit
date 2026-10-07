"""Analytics checked against hand-computed loss vectors and wealth paths."""

import numpy as np
import pytest

from finance_toolkit.analytics import (
    analyze_portfolio,
    drawdown,
    portfolio_returns,
    tail_risk,
)
from finance_toolkit.portfolio import Stock, Trade, value_portfolio
from finance_toolkit.simulation import GBMPaths


def test_risk_quantile_and_fractional_tail_mass() -> None:
    risk = tail_risk([0, 10, 20, 30], confidence=0.625)
    assert risk.value_at_risk == 18.75
    assert risk.expected_shortfall == pytest.approx((30 + 0.5 * 20) / 1.5)
    assert tail_risk([0, 10, 20, 30], confidence=0.75).expected_shortfall == 30
    assert tail_risk([5], confidence=0.95).expected_shortfall == 5
    assert tail_risk([-5, -4, -3], confidence=0.9).value_at_risk < 0


def test_return_and_drawdown_reference() -> None:
    wealth = np.array([[100, 120, 90, 110], [100, 80, 120, 60]], dtype=float)
    np.testing.assert_allclose(
        portfolio_returns(wealth, initial_value=100),
        [[0, 0.2, -0.1, 0.1], [0, -0.2, 0.2, -0.4]],
        atol=1e-14,
    )
    np.testing.assert_allclose(
        drawdown(wealth), [[0, 0, 0.25, 1 - 110 / 120], [0, 0.2, 0, 0.5]], atol=1e-14
    )


def test_portfolio_analysis_pnl_fees_losses_and_totals() -> None:
    market = GBMPaths(
        np.array([0.0, 1.0, 2.0]),
        np.array([[[100.0], [120.0], [90.0]], [[100.0], [80.0], [110.0]]]),
    )
    portfolio = value_portfolio(market, [Trade(0, Stock(), 1, fee=1)], initial_cash=100)
    analysis = analyze_portfolio(portfolio, confidence=0.75)
    np.testing.assert_array_equal(analysis.pnl, [[-1, 19, -11], [-1, -21, 9]])
    np.testing.assert_array_equal(analysis.terminal_losses, [11, -9])
    assert analysis.risk.value_at_risk == 6
    assert analysis.risk.expected_shortfall == 11
    assert analysis.returns is not None
    np.testing.assert_allclose(analysis.returns, analysis.pnl / 100, atol=1e-14)
    assert analysis.drawdowns is not None
    assert analysis.maximum_drawdown is not None
    np.testing.assert_allclose(
        analysis.maximum_drawdown, [30 / 119, 20 / 99], atol=1e-14
    )
    # Initial fee appears in P&L, not an external withdrawal.


def test_portfolio_risk_aggregates_before_quantile() -> None:
    paths = GBMPaths(
        np.array([0.0, 1.0]),
        np.array([[[100.0, 100.0], [80.0, 120.0]], [[100.0, 100.0], [120.0, 80.0]]]),
    )
    result = value_portfolio(
        paths, [Trade(0, Stock(0), 1), Trade(0, Stock(1), 1)], initial_cash=200
    )
    analysis = analyze_portfolio(result)
    assert analysis.risk.value_at_risk == analysis.risk.expected_shortfall == 0


@pytest.mark.parametrize("capital", [0, -100])
def test_absolute_analysis_remains_available_for_nonpositive_capital(
    capital: float,
) -> None:
    paths = GBMPaths(np.array([0.0, 1.0]), np.array([[[100.0], [120.0]]]))
    result = analyze_portfolio(
        value_portfolio(paths, [Trade(0, Stock(), 1)], initial_cash=capital)
    )
    np.testing.assert_array_equal(result.pnl, [[0, 20]])
    assert result.returns is None
    assert result.drawdowns is None
    with pytest.raises(ValueError):
        portfolio_returns(result.wealth, initial_value=capital)


@pytest.mark.parametrize("wealth", [[100, 0], [100, -1], [100, np.nan], []])
def test_undefined_drawdown_rejected(wealth: list) -> None:
    with pytest.raises(ValueError):
        drawdown(wealth)


@pytest.mark.parametrize(
    "losses,confidence",
    [
        ([], 0.95),
        ([1, np.nan], 0.95),
        ([1], 0),
        ([1], 1),
        ([1], np.nan),
        ([[1, 2]], 0.95),
    ],
)
def test_invalid_risk_parameters(losses: list, confidence: float) -> None:
    with pytest.raises(ValueError):
        tail_risk(losses, confidence=confidence)
