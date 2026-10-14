"""Typed UI adapter boundaries; numerical formulas remain in public core APIs."""

from dataclasses import dataclass

from finance_toolkit.analytics import PortfolioAnalysis, analyze_portfolio
from finance_toolkit.portfolio import PortfolioPaths, value_portfolio
from finance_toolkit.simulation import GBMPaths, simulate_gbm
from finance_toolkit.tui.config import Workspace, decode_workspace, encode_workspace


@dataclass(frozen=True)
class PortfolioResult:
    """Owned run outputs with full precision; monetary arrays (paths, times)."""

    config: Workspace
    market: GBMPaths
    portfolio: PortfolioPaths
    analysis: PortfolioAnalysis


def run_portfolio(workspace: Workspace) -> PortfolioResult:
    """Copy/validate inputs, simulate and value once; propagate concrete errors.

    ValueError is an expected input/model-domain error. Other exceptions remain
    diagnostic programming/infrastructure failures. No filesystem/network I/O.
    Core enforces event-grid matching; the adapter never shifts a payment.
    """
    snapshot = decode_workspace(encode_workspace(workspace))
    simulation = snapshot.simulation
    portfolio = snapshot.portfolio
    market = simulate_gbm(
        simulation.spots,
        drift=simulation.drifts,
        volatility=simulation.volatilities,
        horizon=simulation.horizon,
        steps=simulation.steps,
        paths=simulation.paths,
        correlation=simulation.correlation,
        seed=simulation.seed,
    )
    book = value_portfolio(
        market,
        tuple(trade.build() for trade in portfolio.trades),
        initial_cash=portfolio.initial_cash,
        rate=portfolio.rate,
        lending_rate=portfolio.lending_rate,
        borrowing_rate=portfolio.borrowing_rate,
    )
    return PortfolioResult(
        snapshot,
        market,
        book,
        analyze_portfolio(book, confidence=snapshot.risk.confidence),
    )
