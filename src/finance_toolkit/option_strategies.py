"""European strategy constructors: ordinary legs, no additional pricing engine."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_array, finite_float
from finance_toolkit.instruments.options import option_payoff
from finance_toolkit.options_book import BookInstrument, Order
from finance_toolkit.portfolio import EuropeanOption, Stock, Trade

StrategyName = Literal[
    "protective_put", "covered_call", "collar", "bull_call", "bear_put"
]


@dataclass(frozen=True)
class OptionStrategy:
    """Leg quantities in shares/contracts; terminal payoff excludes cash/costs.

    Profit is payoff minus net opening premium plus separate cash financing
    minus fees and loan charges. Bounds on payoff are not bounds on financed P&L.
    """

    name: StrategyName
    instruments: tuple[BookInstrument, ...]
    quantities: tuple[float, ...]

    def orders(self, *, close: bool = False) -> tuple[Order, ...]:
        """Opening or opposite closing quantities; execution quotes from ledger."""
        return tuple(
            Order(j, -q if close else q) for j, q in enumerate(self.quantities)
        )

    def trades(self, time: float = 0.0, *, close: bool = False) -> tuple[Trade, ...]:
        """Generic M1 trades; closing time must precede every option expiry."""
        return tuple(
            Trade(time, x, -q if close else q)
            for x, q in zip(self.instruments, self.quantities, strict=True)
        )

    def payoff(self, terminal_spot: ArrayLike) -> NDArray[np.float64]:
        """Sum of undiscounted legs at their common expiry, one currency."""
        spots = finite_array(terminal_spot, "terminal_spot")
        if np.any(spots < 0):
            raise ValueError("terminal spot must be nonnegative")
        result = np.zeros(spots.shape)
        for instrument, quantity in zip(self.instruments, self.quantities, strict=True):
            if isinstance(instrument, Stock):
                result += quantity * spots
            else:
                result += (
                    quantity
                    * instrument.multiplier
                    * option_payoff(spots, instrument.strike, kind=instrument.kind)
                )
        return result


def build_strategy(
    name: StrategyName,
    *,
    lower_strike: float,
    upper_strike: float,
    maturity: float,
    volatility: float,
    asset: int = 0,
    contracts: float = 1.0,
    multiplier: float = 100.0,
    dividend_yield: float = 0.0,
) -> OptionStrategy:
    """Common asset/expiry/model parameters prevent incompatible option legs.

    Protective put uses lower strike; covered call upper strike; collar both.
    Bull call buys lower and sells upper call; bear put buys upper and sells
    lower put. Covered stock equals contracts * multiplier shares. Positive
    contracts/multiplier and 0<lower<upper required even for single-option legs.
    Invalid names, assets and option parameters raise ValueError.
    """
    lower_strike = finite_float(lower_strike, "lower_strike")
    upper_strike = finite_float(upper_strike, "upper_strike")
    contracts = finite_float(contracts, "contracts")
    if not 0 < lower_strike < upper_strike or contracts <= 0:
        raise ValueError("ordered positive strikes and positive contracts required")
    stock = Stock(asset)
    put_low = EuropeanOption(
        asset, lower_strike, maturity, volatility, "put", multiplier, dividend_yield
    )
    put_high = EuropeanOption(
        asset, upper_strike, maturity, volatility, "put", multiplier, dividend_yield
    )
    call_low = EuropeanOption(
        asset, lower_strike, maturity, volatility, "call", multiplier, dividend_yield
    )
    call_high = EuropeanOption(
        asset, upper_strike, maturity, volatility, "call", multiplier, dividend_yield
    )
    legs: dict[str, tuple[tuple[BookInstrument, ...], tuple[float, ...]]] = {
        "protective_put": ((stock, put_low), (contracts * multiplier, contracts)),
        "covered_call": ((stock, call_high), (contracts * multiplier, -contracts)),
        "collar": (
            (stock, put_low, call_high),
            (contracts * multiplier, contracts, -contracts),
        ),
        "bull_call": ((call_low, call_high), (contracts, -contracts)),
        "bear_put": ((put_high, put_low), (contracts, -contracts)),
    }
    if name not in legs:
        raise ValueError("unknown option strategy")
    instruments, quantities = legs[name]
    return OptionStrategy(name, instruments, quantities)
