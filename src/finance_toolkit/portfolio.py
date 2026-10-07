"""Pathwise trading and cash accounting for stock, option and bond portfolios."""

from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Integral
from typing import TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_array, finite_float
from finance_toolkit.instruments.bonds import TIME_TOLERANCE, Bond
from finance_toolkit.instruments.options import OptionKind, black_scholes, option_payoff
from finance_toolkit.simulation import GBMPaths


def _asset_index(asset: int) -> None:
    if isinstance(asset, bool) or not isinstance(asset, Integral) or asset < 0:
        raise ValueError("asset must be a nonnegative integer")


@dataclass(frozen=True)
class Stock:
    """One share of a simulated asset; price-only returns, no dividend payments."""

    asset: int = 0

    def __post_init__(self) -> None:
        _asset_index(self.asset)


@dataclass(frozen=True)
class EuropeanOption:
    """Cash-settled contract, expiry in absolute years from simulation t=0.

    Quote is per underlying unit; multiplier converts to currency per contract.
    Model volatility is explicit and independent of GBM scenario volatility.
    Dividend yield is a pricing parameter, not a stock dividend cash schedule.
    """

    asset: int
    strike: float
    maturity: float
    volatility: float
    kind: OptionKind = "call"
    multiplier: float = 100.0
    dividend_yield: float = 0.0

    def __post_init__(self) -> None:
        _asset_index(self.asset)
        for name in (
            "strike",
            "maturity",
            "volatility",
            "multiplier",
            "dividend_yield",
        ):
            object.__setattr__(self, name, finite_float(getattr(self, name), name))
        if (
            self.strike <= 0
            or self.maturity <= 0
            or self.volatility < 0
            or self.multiplier <= 0
        ):
            raise ValueError(
                "strike/maturity/multiplier positive; volatility nonnegative"
            )
        if self.kind not in ("call", "put"):
            raise ValueError("kind must be 'call' or 'put'")


Instrument: TypeAlias = Stock | EuropeanOption | Bond


@dataclass(frozen=True)
class Trade:
    """Signed units/contracts: buy positive, sell/short negative.

    Time in years on the simulation grid. Optional execution price is a quote
    per share/bond/underlying option unit; options apply their multiplier.
    Fee is an absolute currency charge per trade, never multiplied by quantity.
    Missing price executes at the model quote. Trades at/after expiry rejected.
    """

    time: float
    instrument: Instrument
    quantity: float
    price: float | None = None
    fee: float = 0.0

    def __post_init__(self) -> None:
        for name in ("time", "quantity", "fee"):
            object.__setattr__(self, name, finite_float(getattr(self, name), name))
        if not isinstance(self.instrument, Stock | EuropeanOption | Bond):
            raise ValueError("instrument must be Stock, EuropeanOption or Bond")
        if self.time < 0 or self.quantity == 0 or self.fee < 0:
            raise ValueError("time/fee nonnegative; quantity nonzero")
        if self.price is not None:
            object.__setattr__(self, "price", finite_float(self.price, "price"))
            if self.price < 0:
                raise ValueError("execution price must be nonnegative")


@dataclass(frozen=True)
class PortfolioPaths:
    """Account paths in one currency; monetary arrays shaped (paths, times).

    instrument_values shape (paths, times, instruments), quantities shape
    (times, instruments). Event cashflows are signed (income positive) and
    exclude opening cash. Instrument order follows first occurrence in trades.
    """

    times: NDArray[np.float64]
    initial_cash: float
    instruments: tuple[Instrument, ...]
    quantities: NDArray[np.float64]
    instrument_values: NDArray[np.float64]
    cash: NDArray[np.float64]
    trade_cashflows: NDArray[np.float64]
    fee_cashflows: NDArray[np.float64]
    coupon_cashflows: NDArray[np.float64]
    principal_cashflows: NDArray[np.float64]
    option_cashflows: NDArray[np.float64]
    financing_cashflows: NDArray[np.float64]

    @property
    def wealth(self) -> NDArray[np.float64]:
        """Cash plus current instrument market values, including short liabilities."""
        return np.asarray(
            self.cash + self.instrument_values.sum(axis=-1), dtype=np.float64
        )


def _grid_index(times: NDArray[np.float64], time: float) -> int:
    matches = np.flatnonzero(np.abs(times - time) <= TIME_TOLERANCE)
    if matches.size != 1:
        raise ValueError(f"time {time} must match exactly one simulation time")
    return int(matches[0])


def _quote(
    instrument: Instrument,
    time: float,
    spots: NDArray[np.float64],
    rates: NDArray[np.float64],
) -> NDArray[np.float64]:
    if isinstance(instrument, Stock):
        return np.asarray(spots[:, instrument.asset], dtype=np.float64)
    if isinstance(instrument, Bond):
        return instrument.price(time, rate=rates)
    if time >= instrument.maturity - TIME_TOLERANCE:
        return np.zeros(spots.shape[0], dtype=np.float64)
    return black_scholes(
        spots[:, instrument.asset],
        instrument.strike,
        instrument.maturity - time,
        instrument.volatility,
        rates,
        dividend_yield=instrument.dividend_yield,
        kind=instrument.kind,
    )


def value_portfolio(
    market: GBMPaths,
    trades: Sequence[Trade],
    *,
    initial_cash: float,
    rate: ArrayLike = 0.0,
    lending_rate: float = 0.0,
    borrowing_rate: float = 0.0,
) -> PortfolioPaths:
    """Execute deterministic trades across all simulated paths and mark to market.

    Market times start at zero, strictly increase, and include every trade and
    instrument payment/expiry within the horizon (tolerance 1e-10 years). Prices
    are positive finite (paths, times, assets). `rate` is a scalar, time vector,
    or (paths,times) array of continuous annual flat valuation curves. It does
    not use scenario drift. Cash earns lending_rate or pays borrowing_rate,
    each an explicit constant continuous annual rate, default zero.

    Event order: accrue cash, pay existing holders, extinguish matured holdings,
    execute trades in supplied order, then ex-payment valuation. No deposits,
    withdrawals, dividend cashflows, margin constraints, taxes or FX. Invalid
    grids, inputs or unrepresentable results raise ValueError.
    """
    times = finite_array(market.times, "times")
    prices = finite_array(market.prices, "prices")
    initial_cash = finite_float(initial_cash, "initial_cash")
    lending_rate = finite_float(lending_rate, "lending_rate")
    borrowing_rate = finite_float(borrowing_rate, "borrowing_rate")
    if times.ndim != 1 or times[0] != 0 or np.any(np.diff(times) <= 2 * TIME_TOLERANCE):
        raise ValueError(
            "times must start at zero and be strictly separated by >2e-10 years"
        )
    if prices.ndim != 3 or prices.shape[1] != times.size or np.any(prices <= 0):
        raise ValueError("prices must be positive (paths, times, assets)")
    path_count, time_count, assets = prices.shape
    rates = np.broadcast_to(finite_array(rate, "rate"), (path_count, time_count))
    instruments = tuple(dict.fromkeys(trade.instrument for trade in trades))
    by_time: dict[int, list[Trade]] = {}
    for trade in trades:
        index = _grid_index(times, trade.time)
        if (
            isinstance(trade.instrument, Stock | EuropeanOption)
            and trade.instrument.asset >= assets
        ):
            raise ValueError("instrument asset is outside market asset axis")
        if isinstance(trade.instrument, Bond | EuropeanOption):
            if times[index] >= trade.instrument.maturity - TIME_TOLERANCE:
                raise ValueError("cannot trade an instrument at or after its maturity")
        by_time.setdefault(index, []).append(trade)
    payments: dict[tuple[int, int], tuple[float, float]] = {}
    for j, instrument in enumerate(instruments):
        if isinstance(instrument, Bond):
            flows = instrument.cashflows()
            for time, coupon, principal in zip(
                flows.times, flows.coupons, flows.principal, strict=True
            ):
                if time <= times[-1] + TIME_TOLERANCE:
                    payments[(_grid_index(times, float(time)), j)] = (
                        float(coupon),
                        float(principal),
                    )
        elif (
            isinstance(instrument, EuropeanOption)
            and instrument.maturity <= times[-1] + TIME_TOLERANCE
        ):
            _grid_index(times, instrument.maturity)
    shape = (path_count, time_count)
    cash, trade_flows, fees, coupons, principal, options, financing = (
        np.zeros(shape, dtype=np.float64) for _ in range(7)
    )
    values = np.zeros((*shape, len(instruments)), dtype=np.float64)
    quantities = np.zeros((time_count, len(instruments)), dtype=np.float64)
    holdings = np.zeros(len(instruments), dtype=np.float64)
    balance = np.full(path_count, initial_cash, dtype=np.float64)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            for i, time in enumerate(times):
                if i:
                    grown = balance * np.exp(
                        np.where(balance >= 0, lending_rate, borrowing_rate)
                        * (time - times[i - 1])
                    )
                    financing[:, i] = grown - balance
                    balance = grown
                for j, instrument in enumerate(instruments):
                    if isinstance(instrument, Bond):
                        coupon, redemption = payments.get((i, j), (0.0, 0.0))
                        coupons[:, i] += holdings[j] * coupon
                        principal[:, i] += holdings[j] * redemption
                    elif (
                        isinstance(instrument, EuropeanOption)
                        and abs(time - instrument.maturity) <= TIME_TOLERANCE
                    ):
                        options[:, i] += (
                            holdings[j]
                            * instrument.multiplier
                            * option_payoff(
                                prices[:, i, instrument.asset],
                                instrument.strike,
                                kind=instrument.kind,
                            )
                        )
                    if (
                        isinstance(instrument, Bond | EuropeanOption)
                        and time >= instrument.maturity - TIME_TOLERANCE
                    ):
                        holdings[j] = 0.0
                balance = balance + coupons[:, i] + principal[:, i] + options[:, i]
                for trade in by_time.get(i, []):
                    j = instruments.index(trade.instrument)
                    quote = (
                        _quote(trade.instrument, float(time), prices[:, i], rates[:, i])
                        if trade.price is None
                        else trade.price
                    )
                    multiplier = (
                        trade.instrument.multiplier
                        if isinstance(trade.instrument, EuropeanOption)
                        else 1.0
                    )
                    flow = -trade.quantity * multiplier * quote
                    trade_flows[:, i] += flow
                    fees[:, i] -= trade.fee
                    balance = balance + flow - trade.fee
                    holdings[j] += trade.quantity
                for j, instrument in enumerate(instruments):
                    multiplier = (
                        instrument.multiplier
                        if isinstance(instrument, EuropeanOption)
                        else 1.0
                    )
                    values[:, i, j] = (
                        holdings[j]
                        * multiplier
                        * _quote(instrument, float(time), prices[:, i], rates[:, i])
                    )
                quantities[i] = holdings
                cash[:, i] = balance
    except FloatingPointError as error:
        raise ValueError("portfolio inputs produce unrepresentable values") from error
    result = PortfolioPaths(
        times.copy(),
        initial_cash,
        instruments,
        quantities,
        values,
        cash,
        trade_flows,
        fees,
        coupons,
        principal,
        options,
        financing,
    )
    if not np.all(np.isfinite(result.wealth)) or not np.all(np.isfinite(cash)):
        raise ValueError("portfolio inputs produce unrepresentable values")
    return result
