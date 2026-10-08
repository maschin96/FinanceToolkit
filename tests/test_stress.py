"""Full repricing and local approximation checks, no probabilistic interpretation."""

import numpy as np
import pytest

from finance_toolkit.instruments.bonds import Bond
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.risk import (
    PortfolioSnapshot,
    StressScenario,
    portfolio_exposures,
    stress_grid,
    stress_portfolio,
)


def test_stock_and_cash_hand_calculation_and_zero_shock():
    snap = PortfolioSnapshot(0, (Stock(),), [10], [100], 0.03, 200)
    zero = stress_portfolio(snap, StressScenario("base"))
    assert zero.total_pnl == 0
    assert zero.base_value == 1200
    result = stress_portfolio(snap, StressScenario("crash", spot_shocks=-0.2))
    np.testing.assert_allclose(result.position_pnl, [-200], rtol=0, atol=1e-12)
    assert result.stressed_value == 1000
    assert result.cash == 200


def test_combined_bond_and_option_reference():
    # ATM with r=q=0 has price 100*(2*Phi(sigma/2)-1).
    from scipy.special import ndtr

    snap = PortfolioSnapshot(
        0,
        (EuropeanOption(0, 100, 1, 0.2, multiplier=10), Bond(100, 0, 2)),
        [2, 3],
        [100],
        0,
        50,
    )
    result = stress_portfolio(snap, StressScenario("vol", volatility_shocks=[0.1, 0]))
    expected = 2000 * (2 * ndtr(0.15) - 2 * ndtr(0.1))
    assert result.total_pnl == pytest.approx(expected, rel=1e-12, abs=1e-12)
    result = stress_portfolio(snap, StressScenario("rates", rate_shock=0.01))
    assert result.position_pnl[1] == pytest.approx(
        300 * (np.exp(-0.02) - 1), rel=1e-12, abs=1e-12
    )


def test_local_greek_approximation_converges():
    snap = PortfolioSnapshot(
        0, (EuropeanOption(0, 100, 1, 0.2, multiplier=1),), [1], [100], 0.03, 0
    )
    g = portfolio_exposures(snap)
    errors = []
    for shock in [0.02, 0.01, 0.005]:
        exact = stress_portfolio(
            snap, StressScenario("spot", spot_shocks=shock)
        ).total_pnl
        ds = 100 * shock
        approx = g.asset_delta[0] * ds + 0.5 * g.asset_gamma[0] * ds**2
        errors.append(abs(exact - approx))
    assert errors[2] < errors[1] < errors[0]
    assert errors[2] < errors[0] / 20


def test_grid_and_maturities():
    snap = PortfolioSnapshot(
        2, (EuropeanOption(0, 100, 1, 0), Bond(100, 0.02, 2)), [1, 1], [100], 0.03, 200
    )
    assert (
        stress_portfolio(snap, StressScenario("expired", spot_shocks=-1)).total_pnl == 0
    )
    active = PortfolioSnapshot(
        0, (EuropeanOption(0, 100, 1, 0.2),), [1], [100], 0.03, 0
    )
    grid = stress_grid(active, [-0.1, 0, 0.1], [0, 0.1])
    assert grid.shape == (2, 3)
    for j, v in enumerate([0, 0.1]):
        for i, s in enumerate([-0.1, 0, 0.1]):
            assert (
                grid[j, i]
                == stress_portfolio(
                    active, StressScenario("x", spot_shocks=s, volatility_shocks=v)
                ).total_pnl
            )


@pytest.mark.parametrize(
    "scenario",
    [
        StressScenario("bad", spot_shocks=-1.1),
        StressScenario("bad", volatility_shocks=-0.3),
        StressScenario("bad", spot_shocks=[0, 0]),
        StressScenario("bad", volatility_shocks=[0, 0]),
        StressScenario("bad", rate_shock=float("nan")),
    ],
)
def test_invalid_stress(scenario):
    snap = PortfolioSnapshot(0, (EuropeanOption(0, 100, 1, 0.2),), [1], [100], 0.03, 0)
    with pytest.raises(ValueError):
        stress_portfolio(snap, scenario)


def test_empty_snapshot_and_overflow():
    snap = PortfolioSnapshot(0, (), [], [100], 0.03, 25)
    assert stress_portfolio(snap, StressScenario("empty")).base_value == 25
    with pytest.raises(ValueError):
        stress_portfolio(
            PortfolioSnapshot(0, (Stock(),), [1e308], [100], 0, 0),
            StressScenario("overflow"),
        )


def test_overflowing_rate_rejected_even_for_cash_only():
    snap = PortfolioSnapshot(0, (), [], [100], 1e308, 25)
    with pytest.raises(ValueError):
        stress_portfolio(snap, StressScenario("overflow", rate_shock=1e308))
