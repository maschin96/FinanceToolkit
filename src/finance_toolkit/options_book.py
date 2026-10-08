"""Delayed, pathwise stock/European-option ledger in one currency."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from numbers import Integral

import numpy as np
from numpy.typing import NDArray

from finance_toolkit._validation import finite_array, finite_float
from finance_toolkit.instruments.bonds import TIME_TOLERANCE
from finance_toolkit.instruments.options import black_scholes, option_payoff
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.simulation import GBMPaths

BookInstrument = Stock | EuropeanOption


@dataclass(frozen=True)
class Order:
    """Signed shares/contracts; optional per-unit quote and absolute currency fee."""

    instrument: int
    quantity: float
    price: float | None = None
    fee: float = 0.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.instrument, bool)
            or not isinstance(self.instrument, Integral)
            or self.instrument < 0
        ):
            raise ValueError("instrument must be a nonnegative integer index")
        object.__setattr__(self, "quantity", finite_float(self.quantity, "quantity"))
        object.__setattr__(self, "fee", finite_float(self.fee, "fee"))
        if self.quantity == 0 or self.fee < 0:
            raise ValueError("quantity nonzero and fee nonnegative required")
        if self.price is not None:
            object.__setattr__(self, "price", finite_float(self.price, "price"))
            if self.price < 0:
                raise ValueError("price must be nonnegative")


@dataclass(frozen=True)
class BookState:
    """Owned readonly current observations; no history or future references."""

    time: float
    spots: NDArray[np.float64]
    quantities: NDArray[np.float64]
    quotes: NDArray[np.float64]
    cash: float
    instruments: tuple[BookInstrument, ...]
    rate: float


BookSignal = Callable[[BookState], Sequence[Order] | None]


@dataclass(frozen=True)
class BookPaths:
    """Position arrays (paths,times,instruments); cash (paths,times).

    quotes are per underlying unit, values include signed quantity/multiplier.
    trade_cashflows, settlements and financing are signed income; fees positive.
    Expiry clears holdings without recording a sale. No external capital flows.
    """

    times: NDArray[np.float64]
    spots: NDArray[np.float64]
    instruments: tuple[BookInstrument, ...]
    initial_cash: float
    rate: float
    quantities: NDArray[np.float64]
    quotes: NDArray[np.float64]
    values: NDArray[np.float64]
    trades: NDArray[np.float64]
    trade_cashflows: NDArray[np.float64]
    fees: NDArray[np.float64]
    turnover: NDArray[np.float64]
    settlements: NDArray[np.float64]
    cash: NDArray[np.float64]
    financing: NDArray[np.float64]

    @property
    def wealth(self) -> NDArray[np.float64]:
        return np.asarray(self.cash + self.values.sum(axis=-1), dtype=np.float64)


def _readonly(value: NDArray[np.float64]) -> NDArray[np.float64]:
    result = value.copy()
    result.setflags(write=False)
    return result


def simulate_book(
    market: GBMPaths,
    instruments: Sequence[BookInstrument],
    *,
    initial_cash: float,
    initial_orders: Sequence[Order] = (),
    signal: BookSignal | None = None,
    rate: float = 0.0,
    fixed_fee: float = 0.0,
    proportional_fee: float = 0.0,
) -> BookPaths:
    """Initial orders execute immediately; current signals execute next grid point.

    Time in years starting at zero, strictly increasing; positive finite spots.
    Every option expiry within horizon must occur on grid (1e-10 year tolerance).
    Cash financing is zero in this base engine. Stock shorts and borrowing rejected;
    signed options supported. Orders execute in supplied order, atomically validated
    against resulting cash. Fixed/proportional fees plus explicit per-order fee.
    Events: financing, cash settlement/clear expiry, orders, ex-event valuation,
    signal. Trading an expired option raises ValueError, including delayed orders.
    Quotes use a constant continuous pricing rate and instrument model volatility.
    """
    times = finite_array(market.times, "times").copy()
    spots = finite_array(market.prices, "prices").copy()
    instruments = tuple(instruments)
    if (
        times.ndim != 1
        or times[0] != 0
        or np.any(np.diff(times) <= 2 * TIME_TOLERANCE)
        or spots.ndim != 3
        or spots.shape[1] != times.size
        or np.any(spots <= 0)
    ):
        raise ValueError("invalid book grid or positive prices")
    if not instruments or any(
        not isinstance(x, Stock | EuropeanOption) or x.asset >= spots.shape[2]
        for x in instruments
    ):
        raise ValueError("instruments must be stocks/options with available assets")
    if len(set(instruments)) != len(instruments):
        raise ValueError("duplicate instruments")
    initial_cash = finite_float(initial_cash, "initial_cash")
    rate = finite_float(rate, "rate")
    fixed_fee = finite_float(fixed_fee, "fixed_fee")
    proportional_fee = finite_float(proportional_fee, "proportional_fee")
    if initial_cash < 0 or fixed_fee < 0 or proportional_fee < 0:
        raise ValueError("capital and fees must be nonnegative")
    if signal is not None and not callable(signal):
        raise ValueError("signal must be callable")
    expiries: dict[int, int] = {}
    for j, instrument in enumerate(instruments):
        if (
            isinstance(instrument, EuropeanOption)
            and instrument.maturity <= times[-1] + TIME_TOLERANCE
        ):
            matches = np.flatnonzero(abs(times - instrument.maturity) <= TIME_TOLERANCE)
            if matches.size != 1:
                raise ValueError("option expiry must match exactly one grid point")
            expiries[j] = int(matches[0])
    shape = (*spots.shape[:2], len(instruments))
    quantities, quotes, values, trades, trade_cf, fees, turnover, settlements = (
        np.zeros(shape) for _ in range(8)
    )
    cash, financing = (np.zeros(spots.shape[:2]) for _ in range(2))
    multipliers = np.array(
        [x.multiplier if isinstance(x, EuropeanOption) else 1.0 for x in instruments]
    )
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            for p in range(spots.shape[0]):
                holding = np.zeros(len(instruments))
                balance = initial_cash
                pending = tuple(initial_orders)
                for t, time in enumerate(times):
                    for j, instrument in enumerate(instruments):
                        spot = spots[p, t, instrument.asset]
                        if isinstance(instrument, Stock):
                            quotes[p, t, j] = spot
                        elif j in expiries and t >= expiries[j]:
                            if t == expiries[j]:
                                payment = (
                                    holding[j]
                                    * instrument.multiplier
                                    * float(
                                        option_payoff(
                                            spot,
                                            instrument.strike,
                                            kind=instrument.kind,
                                        )
                                    )
                                )
                                settlements[p, t, j] = payment
                                balance += payment
                                holding[j] = 0
                        else:
                            quotes[p, t, j] = float(
                                black_scholes(
                                    spot,
                                    instrument.strike,
                                    instrument.maturity - time,
                                    rate=rate,
                                    volatility=instrument.volatility,
                                    dividend_yield=instrument.dividend_yield,
                                    kind=instrument.kind,
                                )
                            )
                    for order in pending:
                        if not isinstance(order, Order) or order.instrument >= len(
                            instruments
                        ):
                            raise ValueError(
                                "order must address an available instrument"
                            )
                        j = order.instrument
                        if j in expiries and t >= expiries[j]:
                            raise ValueError("cannot trade option at/after expiry")
                        quote = quotes[p, t, j] if order.price is None else order.price
                        amount = order.quantity * quote * multipliers[j]
                        charge = order.fee + fixed_fee + proportional_fee * abs(amount)
                        holding[j] += order.quantity
                        balance -= amount + charge
                        trades[p, t, j] += order.quantity
                        trade_cf[p, t, j] -= amount
                        fees[p, t, j] += charge
                        turnover[p, t, j] += abs(amount)
                    if balance < -1e-10 or any(
                        isinstance(x, Stock) and holding[j] < 0
                        for j, x in enumerate(instruments)
                    ):
                        raise ValueError("book cannot borrow cash or short stocks")
                    balance = max(balance, 0.0)
                    quantities[p, t] = holding
                    values[p, t] = holding * quotes[p, t] * multipliers
                    cash[p, t] = balance
                    pending = ()
                    if signal is not None and t < times.size - 1:
                        state = BookState(
                            float(time),
                            _readonly(spots[p, t]),
                            _readonly(holding),
                            _readonly(quotes[p, t]),
                            float(balance),
                            instruments,
                            rate,
                        )
                        pending = tuple(signal(state) or ())
    except (FloatingPointError, OverflowError) as error:
        raise ValueError("unrepresentable book values") from error
    if not all(
        np.all(np.isfinite(x))
        for x in (
            quantities,
            quotes,
            values,
            trades,
            trade_cf,
            fees,
            turnover,
            settlements,
            cash,
        )
    ):
        raise ValueError("unrepresentable book values")
    return BookPaths(
        times,
        spots,
        instruments,
        initial_cash,
        rate,
        quantities,
        quotes,
        values,
        trades,
        trade_cf,
        fees,
        turnover,
        settlements,
        cash,
        financing,
    )
