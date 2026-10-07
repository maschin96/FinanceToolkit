"""Portfolio P&L and explicitly defined empirical risk measures."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_array, finite_float
from finance_toolkit.portfolio import PortfolioPaths


@dataclass(frozen=True)
class TailRisk:
    """Loss quantile and mean of the worst (1-confidence) empirical mass."""

    confidence: float
    value_at_risk: float
    expected_shortfall: float


def tail_risk(losses: ArrayLike, *, confidence: float = 0.95) -> TailRisk:
    """Empirical linear VaR and fractional-tail ES in currency, not percentages.

    Positive loss means losing money; profitable samples may yield negative VaR.
    Losses must be a nonempty finite 1D vector and 0 < confidence < 1. VaR uses
    NumPy's 'linear' quantile. ES averages exactly (1-confidence)*n worst
    observations, fractionally weighting the boundary observation. Single
    observations and tied losses are supported. Invalid inputs raise ValueError.
    """
    array = finite_array(losses, "losses")
    confidence = finite_float(confidence, "confidence")
    if array.ndim != 1 or not 0 < confidence < 1:
        raise ValueError(
            "losses must be 1D and confidence strictly between zero and one"
        )
    ordered = np.sort(array)[::-1]
    mass = (1 - confidence) * array.size
    whole = int(np.floor(mass))
    fraction = mass - whole
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            var = float(np.quantile(array, confidence, method="linear"))
            if whole == 0:
                es = float(ordered[0])
            else:
                es = float(np.sum(ordered[:whole] / mass))
                if fraction:
                    es += float(ordered[whole] * (fraction / mass))
    except FloatingPointError as error:
        raise ValueError(
            "loss scale is not representable for risk calculations"
        ) from error
    if not np.isfinite(var) or not np.isfinite(es):
        raise ValueError("loss scale is not representable for risk calculations")
    return TailRisk(confidence, var, es)


def portfolio_returns(
    wealth: ArrayLike, *, initial_value: float
) -> NDArray[np.float64]:
    """Cumulative simple return relative to positive opening capital, no outside flows.

    Invalid/nonpositive initial capital raises ValueError; wealth may be negative.
    Output has the same shape as the nonempty finite input.
    """
    values = finite_array(wealth, "wealth")
    initial_value = finite_float(initial_value, "initial_value")
    if initial_value <= 0:
        raise ValueError("percentage returns need strictly positive initial capital")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            result = values / initial_value - 1
    except FloatingPointError as error:
        raise ValueError("return scale is unrepresentable") from error
    return np.asarray(result, dtype=np.float64)


def drawdown(wealth: ArrayLike) -> NDArray[np.float64]:
    """Fractional decline from observed running peak along the last (time) axis.

    Wealth must be finite, positive and 1D or 2D (paths,times). First observed
    wealth, after initial trades/fees, initializes the peak. Invalid input
    raises ValueError; no percentage drawdown is defined through insolvency.
    """
    values = finite_array(wealth, "wealth")
    if values.ndim not in (1, 2) or np.any(values <= 0):
        raise ValueError("drawdown needs positive wealth with one time axis")
    peaks = np.maximum.accumulate(values, axis=-1)
    return np.asarray(1 - values / peaks, dtype=np.float64)


@dataclass(frozen=True)
class PortfolioAnalysis:
    """Monetary paths and optional relative metrics; risk is on aggregate wealth.

    Wealth/P&L/returns/drawdowns shape (paths,times); losses/max drawdown shape
    (paths,). Returns are None for nonpositive opening capital. Drawdowns are
    None if any wealth observation is nonpositive; absolute P&L/risk still exist.
    """

    times: NDArray[np.float64]
    wealth: NDArray[np.float64]
    pnl: NDArray[np.float64]
    returns: NDArray[np.float64] | None
    drawdowns: NDArray[np.float64] | None
    maximum_drawdown: NDArray[np.float64] | None
    terminal_losses: NDArray[np.float64]
    risk: TailRisk


def analyze_portfolio(
    portfolio: PortfolioPaths, *, confidence: float = 0.95
) -> PortfolioAnalysis:
    """Analyze wealth including cash, fees, financing and all instrument cashflows.

    P&L = wealth - initial_cash, so initial fees/execution differences are retained.
    Loss = initial_cash - terminal wealth. Quantiles apply after aggregating
    instruments, never by summing standalone VaRs. No external capital flows.
    Invalid inputs or numeric scale raise ValueError.
    """
    wealth = finite_array(portfolio.wealth, "wealth").copy()
    initial = finite_float(portfolio.initial_cash, "initial_cash")
    try:
        with np.errstate(over="raise", invalid="raise"):
            pnl = wealth - initial
            losses = -pnl[:, -1]
    except FloatingPointError as error:
        raise ValueError("P&L scale is unrepresentable") from error
    returns = portfolio_returns(wealth, initial_value=initial) if initial > 0 else None
    drawdowns = drawdown(wealth) if np.all(wealth > 0) else None
    maximum = np.max(drawdowns, axis=1) if drawdowns is not None else None
    return PortfolioAnalysis(
        portfolio.times.copy(),
        wealth,
        pnl,
        returns,
        drawdowns,
        maximum,
        losses,
        tail_risk(losses, confidence=confidence),
    )
