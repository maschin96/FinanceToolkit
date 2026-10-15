"""Built-in strategy adapters sharing one immutable market realization."""

import re
from dataclasses import dataclass
from typing import TypedDict

import numpy as np
from numpy.typing import NDArray

from finance_toolkit.attribution import Attribution, attribute_book
from finance_toolkit.hedge_lab import Comparison, ComparisonCase, compare_hedges
from finance_toolkit.hedging import HedgePaths
from finance_toolkit.instruments.bonds import TIME_TOLERANCE
from finance_toolkit.option_strategies import build_strategy
from finance_toolkit.options_book import BookPaths, BookState, Order, simulate_book
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.simulation import GBMPaths
from finance_toolkit.strategies import StrategyPaths, simulate_rebalancing
from finance_toolkit.tui.config import (
    HedgeConfig,
    Workspace,
    decode_workspace,
    encode_workspace,
)
from finance_toolkit.tui.services import simulate_market


@dataclass(frozen=True)
class StrategyResult:
    """Full ledgers on one base market; book IDs include category/name."""

    config: Workspace
    market: GBMPaths
    rebalancing: dict[str, StrategyPaths]
    books: dict[str, BookPaths]
    hedges: dict[str, HedgePaths]
    attributions: dict[str, Attribution]
    comparison: Comparison | None


class _BookParameters(TypedDict):
    initial_cash: float
    fixed_fee: float
    proportional_fee: float
    lending_rate: float
    rate: float
    borrowing_rate: float
    stock_borrow_rate: float
    allow_borrowing: bool
    allow_short_stocks: bool


def validate_strategies(config: Workspace) -> None:
    """Check deterministic input/permission/grid preconditions before a worker."""
    simulation, strategy, hedge = config.simulation, config.strategy, config.hedge
    assets = len(simulation.spots)
    times = np.linspace(0, simulation.horizon, simulation.steps + 1)
    if np.any(np.diff(times) <= 2 * TIME_TOLERANCE):
        raise ValueError("time grid must have separation >2e-10 years")
    weights = np.asarray(strategy.weights)
    if weights.shape != (assets,) or np.any(weights < 0) or weights.sum() > 1:
        raise ValueError("one nonnegative target weight per asset, sum <=1 required")
    if strategy.calendar is not None and strategy.threshold is not None:
        raise ValueError("choose calendar or threshold")
    if strategy.threshold is not None and not 0 < strategy.threshold <= 1:
        raise ValueError("rebalancing threshold must be in (0,1]")
    if strategy.calendar is not None and len(set(strategy.calendar)) != len(
        strategy.calendar
    ):
        raise ValueError("calendar must have distinct times")
    for time in strategy.calendar or ():
        _grid_index(time, times)
    if (
        min(strategy.fixed_fee, strategy.proportional_fee, strategy.stock_borrow_rate)
        < 0
    ):
        raise ValueError("fees/stock borrow rate must be nonnegative")
    if not 0 <= strategy.asset < assets:
        raise ValueError("strategy asset outside simulation")
    built = build_strategy(
        strategy.option_strategy,
        lower_strike=strategy.strike,
        upper_strike=strategy.upper_strike,
        maturity=strategy.maturity,
        volatility=strategy.volatility,
        asset=strategy.asset,
        contracts=strategy.quantity,
        multiplier=strategy.multiplier,
        dividend_yield=strategy.dividend_yield,
    )
    for instrument in built.instruments:
        if (
            isinstance(instrument, EuropeanOption)
            and instrument.maturity <= simulation.horizon
        ):
            _grid_index(instrument.maturity, times)
    for trade in strategy.orders:
        scheduled_instrument = trade.instrument.build()
        if (
            not isinstance(scheduled_instrument, Stock | EuropeanOption)
            or scheduled_instrument.asset >= assets
        ):
            raise ValueError("dynamic orders require existing stock/option assets")
        _grid_index(trade.time, times)
        if isinstance(scheduled_instrument, EuropeanOption):
            if trade.time >= scheduled_instrument.maturity - TIME_TOLERANCE:
                raise ValueError("cannot execute an expired option")
            if scheduled_instrument.maturity <= simulation.horizon:
                _grid_index(scheduled_instrument.maturity, times)
    if hedge.enabled:
        if not hedge.allow_short or not hedge.allow_borrowing:
            raise ValueError(
                "hedging requires explicit short-stock and credit permissions"
            )
        option = hedge.option.build()
        if not isinstance(option, EuropeanOption) or option.asset >= assets:
            raise ValueError("hedge requires an option on an existing asset")
        if option.maturity != simulation.horizon:
            raise ValueError("hedge option maturity must equal simulation horizon")
        if hedge.option_quantity == 0:
            raise ValueError("hedge opening option quantity must be nonzero")
        cases = _comparison_cases(hedge)
        if len(cases) > 20:
            raise ValueError("TUI limit: 20 hedge cases")
        if len({case.name for case in cases}) != len(cases) or any(
            not re.fullmatch(r"[A-Za-z0-9_-]+", case.name) for case in cases
        ):
            raise ValueError("distinct safe hedge case names required")
        for case in cases:
            if case.stride <= 0 or simulation.steps % case.stride:
                raise ValueError("positive hedge strides dividing base steps required")
            if case.calendar_every is not None and (
                case.calendar_every <= 0 or case.threshold is not None
            ):
                raise ValueError("positive calendar_every or threshold, not both")
            if case.threshold is not None and case.threshold <= 0:
                raise ValueError("positive share-equivalent delta threshold required")
            if min(case.fixed_fee, case.proportional_fee, hedge.stock_borrow_rate) < 0:
                raise ValueError("hedge fees/borrow rate must be nonnegative")


def _comparison_cases(hedge: HedgeConfig) -> tuple[ComparisonCase, ...]:
    if hedge.cases:
        return tuple(
            ComparisonCase(
                case.name,
                case.stride,
                case.calendar_every,
                case.threshold,
                case.fixed_fee,
                case.proportional_fee,
            )
            for case in hedge.cases
        )
    if len(hedge.case_names) != len(hedge.strides) or not hedge.strides:
        raise ValueError("one case name per stride required")
    return tuple(
        ComparisonCase(
            name,
            stride,
            hedge.calendar_every,
            hedge.threshold,
            hedge.fixed_fee,
            hedge.proportional_fee,
        )
        for name, stride in zip(hedge.case_names, hedge.strides, strict=True)
    )


def _grid_index(time: float, times: NDArray[np.float64]) -> int:
    matches = np.flatnonzero(np.abs(times - time) <= TIME_TOLERANCE)
    if matches.size != 1:
        raise ValueError(f"time {time} must match exactly one simulation time")
    return int(matches[0])


def run_strategies(workspace: Workspace) -> StrategyResult:
    """One market/capital, separate opening assumptions, exact book attribution."""
    snapshot = decode_workspace(encode_workspace(workspace))
    validate_strategies(snapshot)
    snapshot, market = simulate_market(snapshot)
    config, funding = snapshot.strategy, snapshot.portfolio
    common = dict(
        initial_cash=funding.initial_cash,
        fixed_fee=config.fixed_fee,
        proportional_fee=config.proportional_fee,
        lending_rate=funding.lending_rate,
    )
    rebalancing = {
        "buy_and_hold": simulate_rebalancing(market, config.weights, **common),
        "configured": simulate_rebalancing(
            market,
            config.weights,
            calendar=config.calendar,
            threshold=config.threshold,
            **common,
        ),
    }
    built = build_strategy(
        config.option_strategy,
        lower_strike=config.strike,
        upper_strike=config.upper_strike,
        maturity=config.maturity,
        volatility=config.volatility,
        asset=config.asset,
        contracts=config.quantity,
        multiplier=config.multiplier,
        dividend_yield=config.dividend_yield,
    )
    book_common: _BookParameters = dict(
        initial_cash=funding.initial_cash,
        fixed_fee=config.fixed_fee,
        proportional_fee=config.proportional_fee,
        lending_rate=funding.lending_rate,
        rate=funding.rate,
        borrowing_rate=funding.borrowing_rate,
        stock_borrow_rate=config.stock_borrow_rate,
        allow_borrowing=config.allow_borrowing,
        allow_short_stocks=config.allow_short,
    )
    books = {
        f"strategy/configured_{config.option_strategy}": simulate_book(
            market, built.instruments, initial_orders=built.orders(), **book_common
        )
    }
    instruments = tuple(
        dict.fromkeys(trade.instrument.build() for trade in config.orders)
    ) or (Stock(),)
    # Validation above narrowed instruments to the public BookInstrument union.
    book_instruments = tuple(
        x for x in instruments if isinstance(x, Stock | EuropeanOption)
    )
    initial: list[Order] = []
    signals: dict[float, list[Order]] = {}
    for trade in config.orders:
        order = Order(
            book_instruments.index(trade.instrument.build()),
            trade.quantity,
            trade.price,
            trade.fee,
        )
        index = _grid_index(trade.time, market.times)
        if index == 0:
            initial.append(order)
        else:
            signals.setdefault(float(market.times[index - 1]), []).append(order)

    def signal(state: BookState) -> tuple[Order, ...]:
        return tuple(signals.get(state.time, ()))

    books["dynamic/scheduled"] = simulate_book(
        market, book_instruments, initial_orders=initial, signal=signal, **book_common
    )
    hedges: dict[str, HedgePaths] = {}
    comparison = None
    if snapshot.hedge.enabled:
        hedge = snapshot.hedge
        option = hedge.option.build()
        assert isinstance(option, EuropeanOption)  # validated before simulation
        cases = _comparison_cases(hedge)
        comparison = compare_hedges(
            market,
            cases,
            initial_cash=funding.initial_cash,
            option=option,
            option_quantity=hedge.option_quantity,
            rate=funding.rate,
            lending_rate=funding.lending_rate,
            borrowing_rate=funding.borrowing_rate,
            stock_borrow_rate=hedge.stock_borrow_rate,
        )
        books.update({f"hedge/{name}": book for name, book in comparison.books.items()})
        books.update(
            {f"strategy/{name}": book for name, book in comparison.strategies.items()}
        )
        hedges.update(
            {f"hedge/{name}": value for name, value in comparison.hedges.items()}
        )
    return StrategyResult(
        snapshot,
        market,
        rebalancing,
        books,
        hedges,
        {name: attribute_book(book) for name, book in books.items()},
        comparison,
    )
