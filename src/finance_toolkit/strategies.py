"""Long-only stock/cash strategies with delayed, pathwise execution."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_array, finite_float
from finance_toolkit.instruments.bonds import TIME_TOLERANCE
from finance_toolkit.simulation import GBMPaths


@dataclass(frozen=True)
class StrategyState:
    """Current path state only; owned readonly copies, no future market access."""

    time: float
    spots: NDArray[np.float64]
    quantities: NDArray[np.float64]
    cash: float

    @property
    def wealth(self) -> float:
        return float(self.cash + np.dot(self.spots, self.quantities))


Signal = Callable[[StrategyState], ArrayLike | None]


@dataclass(frozen=True)
class StrategyPaths:
    """Ledger in one currency; quantities/trades/fees/turnover (paths,times,assets).

    Trade quantities signed; fees and turnover positive charges/notional, zero
    without executions. cash/financing (paths,times), monetary values include
    mark-to-market stocks. Initial execution uses the same costs as later trades.
    """

    times: NDArray[np.float64]
    prices: NDArray[np.float64]
    initial_cash: float
    quantities: NDArray[np.float64]
    cash: NDArray[np.float64]
    trades: NDArray[np.float64]
    fees: NDArray[np.float64]
    turnover: NDArray[np.float64]
    financing: NDArray[np.float64]

    @property
    def wealth(self) -> NDArray[np.float64]:
        return np.asarray(
            self.cash + np.sum(self.quantities * self.prices, axis=-1), dtype=np.float64
        )

    @property
    def weights(self) -> NDArray[np.float64]:
        wealth = self.wealth
        if np.any(wealth <= 0):
            raise ValueError("weights require positive wealth")
        return self.quantities * self.prices / wealth[..., None]


def _weights(weights: ArrayLike, assets: int) -> NDArray[np.float64]:
    result = finite_array(weights, "weights")
    if result.shape != (assets,) or np.any(result < 0) or result.sum() > 1:
        raise ValueError("weights must be nonnegative (assets,) with sum <= 1")
    return result.copy()


def _execute(
    current: NDArray[np.float64],
    target: NDArray[np.float64],
    spots: NDArray[np.float64],
    cash: float,
    fixed: float,
    proportional: float,
) -> tuple[float, NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Sell first, then cash-limited buys in explicit asset order."""
    changes = np.zeros(current.shape)
    fees = np.zeros(current.shape)
    turnover = np.zeros(current.shape)
    for selling in (True, False):
        for asset, price in enumerate(spots):
            difference = target[asset] - current[asset]
            if difference == 0 or (difference < 0) != selling:
                continue
            quantity = abs(difference)
            if selling:
                notional = quantity * price
                charge = fixed + proportional * notional
                if cash + notional < charge:
                    continue
                cash += notional - charge
                change = -quantity
            else:
                if cash <= fixed:
                    continue
                quantity = min(quantity, (cash - fixed) / (price * (1 + proportional)))
                if quantity <= 0:
                    continue
                notional = quantity * price
                charge = fixed + proportional * notional
                residual = cash - notional - charge
                # Only bound arithmetic roundoff after the affordability formula.
                if residual < -1e-12 * max(1, cash):
                    raise ValueError("purchase exceeds available cash")
                cash = max(0.0, residual)
                change = quantity
            current[asset] += change
            changes[asset] += change
            fees[asset] += charge
            turnover[asset] += notional
    return cash, changes, fees, turnover


def simulate_strategy(
    market: GBMPaths,
    signal: Signal | None,
    *,
    initial_cash: float,
    initial_weights: ArrayLike,
    fixed_fee: float = 0.0,
    proportional_fee: float = 0.0,
    lending_rate: float = 0.0,
) -> StrategyPaths:
    """Execute long-only quantities signalled at t at the next grid point.

    Initial weights are allocated at t=0 from opening capital, with normal fees.
    signal sees only the current owned state after financing/execution, returns
    nonnegative target shares (assets,) or None. No last-point signal is called.
    Prices positive finite (paths,times,assets); times start at zero and strictly
    increase by >2e-10 years. No borrowing, outside flows or dividends. Positive
    initial capital; finite nonnegative fixed/proportional fees. Cash earns the
    explicit continuous lending_rate (may be negative). Invalid data, signals,
    nonpositive wealth or numerical overflow raise ValueError.
    """
    times = finite_array(market.times, "times").copy()
    prices = finite_array(market.prices, "prices").copy()
    if (
        times.ndim != 1
        or times[0] != 0
        or np.any(np.diff(times) <= 2 * TIME_TOLERANCE)
        or prices.ndim != 3
        or prices.shape[1] != times.size
        or np.any(prices <= 0)
    ):
        raise ValueError("invalid strategy market grid or prices")
    initial_cash = finite_float(initial_cash, "initial_cash")
    fixed_fee = finite_float(fixed_fee, "fixed_fee")
    proportional_fee = finite_float(proportional_fee, "proportional_fee")
    lending_rate = finite_float(lending_rate, "lending_rate")
    if initial_cash <= 0 or fixed_fee < 0 or proportional_fee < 0:
        raise ValueError("positive capital and nonnegative fees required")
    if signal is not None and not callable(signal):
        raise ValueError("signal must be callable or None")
    weights = _weights(initial_weights, prices.shape[2])
    quantities = np.zeros(prices.shape)
    trades = np.zeros(prices.shape)
    fees = np.zeros(prices.shape)
    turnover = np.zeros(prices.shape)
    cash = np.zeros(prices.shape[:2])
    financing = np.zeros(prices.shape[:2])
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            for path in range(prices.shape[0]):
                current = np.zeros(prices.shape[2])
                balance = initial_cash
                pending: NDArray[np.float64] | None = (
                    weights * initial_cash / prices[path, 0]
                )
                for index, time in enumerate(times):
                    if index:
                        earned = balance * np.expm1(
                            lending_rate * (time - times[index - 1])
                        )
                        financing[path, index] = earned
                        balance += earned
                    if pending is not None:
                        balance, delta, charge, notional = _execute(
                            current,
                            pending,
                            prices[path, index],
                            balance,
                            fixed_fee,
                            proportional_fee,
                        )
                        (
                            trades[path, index],
                            fees[path, index],
                            turnover[path, index],
                        ) = delta, charge, notional
                    quantities[path, index] = current
                    cash[path, index] = balance
                    wealth = balance + np.dot(current, prices[path, index])
                    if not np.isfinite(wealth) or wealth <= 0:
                        raise ValueError(
                            "strategy wealth must remain finite and positive"
                        )
                    pending = None
                    if signal is not None and index < times.size - 1:
                        spot_copy, qty_copy = prices[path, index].copy(), current.copy()
                        spot_copy.setflags(write=False)
                        qty_copy.setflags(write=False)
                        result = signal(
                            StrategyState(
                                float(time), spot_copy, qty_copy, float(balance)
                            )
                        )
                        if result is not None:
                            pending = finite_array(result, "signal quantities").copy()
                            if pending.shape != current.shape or np.any(pending < 0):
                                raise ValueError(
                                    "signal needs nonnegative (assets,) quantities"
                                )
    except (FloatingPointError, OverflowError) as error:
        raise ValueError("unrepresentable strategy values") from error
    if not all(
        np.all(np.isfinite(x))
        for x in (quantities, cash, trades, fees, turnover, financing)
    ):
        raise ValueError("unrepresentable strategy values")
    if np.any(cash < 0) or np.any(quantities < 0):
        raise ValueError("strategy cannot borrow or short")
    return StrategyPaths(
        times, prices, initial_cash, quantities, cash, trades, fees, turnover, financing
    )


def simulate_rebalancing(
    market: GBMPaths,
    target_weights: ArrayLike,
    *,
    initial_cash: float,
    calendar: ArrayLike | None = None,
    threshold: float | None = None,
    fixed_fee: float = 0.0,
    proportional_fee: float = 0.0,
    lending_rate: float = 0.0,
) -> StrategyPaths:
    """Compare buy-and-hold, explicit calendar or strict weight-threshold signals.

    At most one of calendar/threshold; neither means buy-and-hold. Weights finite
    nonnegative (assets,) with sum <=1; cash is the remainder. Calendar is a
    finite 1D vector of distinct matching grid times. Empty calendar is allowed.
    Threshold is a fraction, 0<threshold<=1 (0.05 = five percentage points);
    signal when any stock/cash weight deviation is strictly larger. Targets
    computed at signal time and executed at the next point by simulate_strategy.
    Final-point calendar events produce no trade. Invalid rules raise ValueError.
    """
    prices = finite_array(market.prices, "prices")
    if prices.ndim != 3:
        raise ValueError("prices must have shape (paths,times,assets)")
    weights = _weights(target_weights, prices.shape[2])
    if calendar is not None and threshold is not None:
        raise ValueError("choose calendar or threshold, not both")
    scheduled: set[float] = set()
    if calendar is not None:
        dates = np.asarray(calendar, dtype=np.float64)
        times = finite_array(market.times, "times")
        if dates.ndim != 1 or not np.all(np.isfinite(dates)) or times.ndim != 1:
            raise ValueError("calendar must be a finite 1D vector")
        for date in dates:
            matches = np.flatnonzero(np.abs(times - date) <= TIME_TOLERANCE)
            if matches.size != 1 or float(times[matches[0]]) in scheduled:
                raise ValueError("calendar times must match distinct grid points")
            scheduled.add(float(times[matches[0]]))
    if threshold is not None:
        threshold = finite_float(threshold, "threshold")
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be in (0,1]")

    def signal(state: StrategyState) -> ArrayLike | None:
        wealth = state.wealth
        if wealth <= 0:
            raise ValueError("rebalancing needs positive wealth")
        if threshold is not None:
            actual = state.quantities * state.spots / wealth
            cash_deviation = abs(state.cash / wealth - (1 - weights.sum()))
            if not (
                np.any(np.abs(actual - weights) > threshold)
                or cash_deviation > threshold
            ):
                return None
        elif state.time not in scheduled:
            return None
        return weights * wealth / state.spots

    return simulate_strategy(
        market,
        signal if calendar is not None or threshold is not None else None,
        initial_cash=initial_cash,
        initial_weights=weights,
        fixed_fee=fixed_fee,
        proportional_fee=proportional_fee,
        lending_rate=lending_rate,
    )
