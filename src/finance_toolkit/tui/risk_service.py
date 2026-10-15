"""Public risk/stress adapters on an explicitly selected post-event snapshot."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from finance_toolkit.risk import (
    PortfolioExposures,
    PortfolioSnapshot,
    StressResult,
    StressScenario,
    portfolio_exposures,
    stress_grid,
    stress_portfolio,
)
from finance_toolkit.tui.config import Workspace
from finance_toolkit.tui.services import PortfolioResult, run_portfolio


@dataclass(frozen=True)
class RiskResult:
    base: PortfolioResult
    snapshot: PortfolioSnapshot
    exposures: PortfolioExposures | None
    exposure_error: str
    scenarios: tuple[StressResult, ...]
    grid: NDArray[np.float64]


def run_risk(workspace: Workspace) -> RiskResult:
    """Reprice unchanged holdings/cash; preserve base prices if Greeks undefined.

    VaR/ES remains on terminal portfolio losses, independent of hypothetical
    stress. ValueError from Greeks is reported without substituting zero;
    invalid shock inputs propagate rather than being clipped or ignored.
    """
    base = run_portfolio(workspace)
    config = base.config.risk
    snapshot = PortfolioSnapshot(
        float(base.market.times[config.time_index]),
        base.portfolio.instruments,
        base.portfolio.quantities[config.time_index],
        base.market.prices[config.path, config.time_index],
        base.config.portfolio.rate,
        float(base.portfolio.cash[config.path, config.time_index]),
    )
    error = ""
    try:
        exposures = portfolio_exposures(snapshot)
    except ValueError as exception:
        exposures = None
        error = str(exception)
    if config.scenarios:
        if len({x.name for x in config.scenarios}) != len(config.scenarios):
            raise ValueError("distinct scenario names required")
        scenarios = tuple(
            StressScenario(x.name, x.spot_shocks, x.volatility_shocks, x.rate_shock)
            for x in config.scenarios
        )
    else:
        scenarios = tuple(
            StressScenario(
                f"spot={spot:+g},rate={rate:+g}", spot, config.volatility_shock, rate
            )
            for spot in config.spot_shocks
            for rate in config.rate_shocks
        )
    return RiskResult(
        base,
        snapshot,
        exposures,
        error,
        tuple(stress_portfolio(snapshot, scenario) for scenario in scenarios),
        stress_grid(snapshot, config.spot_shocks, config.grid_volatility_shocks),
    )
