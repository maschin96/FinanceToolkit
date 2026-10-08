"""Delayed delta hedges on the mixed book; thresholds in share equivalents."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_float
from finance_toolkit.instruments.bonds import TIME_TOLERANCE
from finance_toolkit.instruments.options import option_greeks
from finance_toolkit.options_book import (
    BookInstrument,
    BookPaths,
    BookState,
    Order,
    simulate_book,
)
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.simulation import GBMPaths


@dataclass(frozen=True)
class HedgePaths:
    """Book plus share-equivalent deltas (paths,times,assets).

    target_shares computed from current options, before_delta before execution,
    residual_delta actual after execution. Delay makes residual generally nonzero.
    """

    book: BookPaths
    target_shares: NDArray[np.float64]
    before_delta: NDArray[np.float64]
    residual_delta: NDArray[np.float64]


def option_delta(state: BookState) -> NDArray[np.float64]:
    """Aggregate signed option delta by asset; expired/zero positions skipped.

    Active S=0, sigma=0 or T=0 follow option_greeks rejection contract.
    """
    delta = np.zeros(state.spots.size)
    for j, instrument in enumerate(state.instruments):
        if (
            isinstance(instrument, EuropeanOption)
            and state.quantities[j] != 0
            and instrument.maturity > state.time + TIME_TOLERANCE
        ):
            greek = option_greeks(
                state.spots[instrument.asset],
                instrument.strike,
                instrument.maturity - state.time,
                instrument.volatility,
                state.rate,
                dividend_yield=instrument.dividend_yield,
                kind=instrument.kind,
            )
            delta[instrument.asset] += (
                state.quantities[j] * instrument.multiplier * float(greek.delta)
            )
    return delta


def simulate_hedge(
    market: GBMPaths,
    instruments: Sequence[BookInstrument],
    *,
    initial_cash: float,
    initial_orders: Sequence[Order] = (),
    calendar: ArrayLike | None = None,
    threshold: float | None = None,
    rate: float = 0.0,
    fixed_fee: float = 0.0,
    proportional_fee: float = 0.0,
    lending_rate: float = 0.0,
    borrowing_rate: float = 0.0,
    stock_borrow_rate: float = 0.0,
) -> HedgePaths:
    """One designated stock hedge per option asset; no other stock positions.

    Neither calendar nor threshold means unhedged control. Initial option orders
    identical across rules; first hedge signal at zero executes at next point.
    Strict absolute threshold >0 in shares. Calendar must match distinct grid
    points; last-point signal ignored. All stock holdings for an asset close at
    its last option expiry after settlement, at actual spot with normal costs.
    Pending obsolete stock orders are cancelled then; no future spot is read.
    Financing/shorts explicitly enabled by this hedge API, using supplied rates.
    """
    instruments = tuple(instruments)
    stock_indices = {
        x.asset: j for j, x in enumerate(instruments) if isinstance(x, Stock)
    }
    if any(
        isinstance(x, EuropeanOption) and x.asset not in stock_indices
        for x in instruments
    ):
        raise ValueError("each option asset requires a designated Stock hedge")
    if any(
        not isinstance(o, Order)
        or o.instrument >= len(instruments)
        or isinstance(instruments[o.instrument], Stock)
        for o in initial_orders
    ):
        raise ValueError(
            "initial orders must be options, stock legs reserved for hedge"
        )
    if calendar is not None and threshold is not None:
        raise ValueError("choose calendar or threshold")
    scheduled: set[float] = set()
    if calendar is not None:
        dates = np.asarray(calendar, dtype=float)
        if dates.ndim != 1 or not np.all(np.isfinite(dates)):
            raise ValueError("calendar must be finite 1D")
        for date in dates:
            match = np.flatnonzero(abs(market.times - date) <= TIME_TOLERANCE)
            if match.size != 1 or float(market.times[match[0]]) in scheduled:
                raise ValueError("calendar must match distinct grid points")
            scheduled.add(float(market.times[match[0]]))
    if threshold is not None:
        threshold = finite_float(threshold, "threshold")
        if threshold <= 0:
            raise ValueError("threshold must be positive shares")

    def signal(state: BookState) -> Sequence[Order] | None:
        delta = option_delta(state)
        residual = delta.copy()
        for asset, j in stock_indices.items():
            residual[asset] += state.quantities[j]
        if threshold is not None:
            if not np.any(abs(residual) > threshold):
                return None
        elif state.time not in scheduled:
            return None
        return tuple(
            Order(j, -residual[asset])
            for asset, j in stock_indices.items()
            if residual[asset] != 0
        )

    book = simulate_book(
        market,
        instruments,
        initial_cash=initial_cash,
        initial_orders=initial_orders,
        signal=signal if calendar is not None or threshold is not None else None,
        rate=rate,
        fixed_fee=fixed_fee,
        proportional_fee=proportional_fee,
        allow_short_stocks=True,
        allow_borrowing=True,
        close_hedges_at_expiry=True,
        lending_rate=lending_rate,
        borrowing_rate=borrowing_rate,
        stock_borrow_rate=stock_borrow_rate,
    )
    target = np.zeros(book.spots.shape)
    before = np.zeros(book.spots.shape)
    residuals = np.zeros(book.spots.shape)
    # Vectorize Greeks over paths for reporting; simulation stays pathwise.
    for t, time in enumerate(book.times):
        delta = np.zeros((book.spots.shape[0], book.spots.shape[2]))
        for j, x in enumerate(instruments):
            if isinstance(x, EuropeanOption) and time < x.maturity - TIME_TOLERANCE:
                active = book.quantities[:, t, j] != 0
                if np.any(active):
                    g = option_greeks(
                        book.spots[active, t, x.asset],
                        x.strike,
                        x.maturity - time,
                        x.volatility,
                        rate,
                        dividend_yield=x.dividend_yield,
                        kind=x.kind,
                    )
                    delta[active, x.asset] += (
                        book.quantities[active, t, j] * x.multiplier * g.delta
                    )
        target[:, t] = -delta
        before[:, t] = delta
        residuals[:, t] = delta
        for asset, j in stock_indices.items():
            before[:, t, asset] += book.quantities[:, t, j] - book.trades[:, t, j]
            residuals[:, t, asset] += book.quantities[:, t, j]
    return HedgePaths(book, target, before, residuals)
