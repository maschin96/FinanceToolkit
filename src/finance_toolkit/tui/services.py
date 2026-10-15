"""Typed UI adapter boundaries; numerical formulas remain in public core APIs."""

from dataclasses import dataclass, fields, is_dataclass
from typing import Any

import numpy as np

from finance_toolkit.analytics import PortfolioAnalysis, analyze_portfolio
from finance_toolkit.instruments.bonds import TIME_TOLERANCE, Bond
from finance_toolkit.instruments.options import black_scholes
from finance_toolkit.portfolio import (
    EuropeanOption,
    PortfolioPaths,
    Stock,
    value_portfolio,
)
from finance_toolkit.simulation import GBMPaths, simulate_gbm
from finance_toolkit.tui.config import Workspace, decode_workspace, encode_workspace


@dataclass(frozen=True)
class PortfolioResult:
    """Owned run outputs with full precision; monetary arrays (paths, times)."""

    config: Workspace
    market: GBMPaths
    portfolio: PortfolioPaths
    analysis: PortfolioAnalysis


def simulate_market(workspace: Workspace) -> tuple[Workspace, GBMPaths]:
    """Validate/copy inputs and generate one owned market for all comparisons."""
    snapshot = decode_workspace(encode_workspace(workspace))
    simulation = snapshot.simulation
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
    return snapshot, market


def run_portfolio(workspace: Workspace) -> PortfolioResult:
    """Copy/validate and value via public APIs; propagate concrete domain errors.

    No filesystem/network I/O. Core enforces event-grid matching; the adapter
    never shifts a payment. Unexpected exceptions retain their diagnostics.
    """
    snapshot, market = simulate_market(workspace)
    portfolio = snapshot.portfolio
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


def position_rows(
    result: PortfolioResult, path: int, time_index: int
) -> list[dict[str, str | float]]:
    """Selected post-event holdings/quotes; prices use public instrument APIs.

    Rows contain full precision. Quotes are per unit, signed value is per
    position. Options at/after settlement have zero ex-event quote/value.
    Bond clean/dirty/accrued values are per bond, currency as in the snapshot.
    Raises ValueError for out-of-range or non-integer selection.
    """
    if type(path) is not int or not 0 <= path < result.config.simulation.paths:
        raise ValueError("path outside simulation")
    if (
        type(time_index) is not int
        or not 0 <= time_index <= result.config.simulation.steps
    ):
        raise ValueError("time_index outside simulation")
    time = float(result.market.times[time_index])
    rows: list[dict[str, str | float]] = []
    for index, instrument in enumerate(result.portfolio.instruments):
        row: dict[str, str | float] = {
            "instrument": str(instrument),
            "quantity": float(result.portfolio.quantities[time_index, index]),
            "value": float(result.portfolio.instrument_values[path, time_index, index]),
        }
        if isinstance(instrument, Bond):
            row.update(
                quote=float(instrument.price(time, rate=result.config.portfolio.rate)),
                dirty=float(instrument.price(time, rate=result.config.portfolio.rate)),
                clean=float(
                    instrument.price(
                        time, rate=result.config.portfolio.rate, clean=True
                    )
                ),
                accrued=instrument.accrued_interest(time),
            )
        else:
            spot = float(result.market.prices[path, time_index, instrument.asset])
            if isinstance(instrument, Stock):
                row["quote"] = spot
            elif isinstance(instrument, EuropeanOption):
                row["quote"] = (
                    0.0
                    if time >= instrument.maturity - TIME_TOLERANCE
                    else float(
                        black_scholes(
                            spot,
                            instrument.strike,
                            instrument.maturity - time,
                            instrument.volatility,
                            result.config.portfolio.rate,
                            dividend_yield=instrument.dividend_yield,
                            kind=instrument.kind,
                        )
                    )
                )
        rows.append(row)
    return rows


def numerical_payload(value: object) -> Any:
    """Copy typed result containers to JSON primitives without display rounding."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: numerical_payload(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): numerical_payload(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [numerical_payload(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise ValueError(f"Unsupported result type: {type(value).__name__}")


def portfolio_payload(result: PortfolioResult) -> dict[str, Any]:
    """Full numerical export boundary for C/G; no file writes or volatile data.

    CSV/file selection/version provenance follow in #80. JSON primitives retain
    every path/time/asset, instrument identity and precision; UI sampling has no
    effect on the payload. Caller owns returned lists/dicts.
    """
    portfolio = numerical_payload(result.portfolio)
    portfolio["instruments"] = [
        {"kind": type(instrument).__name__, "parameters": numerical_payload(instrument)}
        for instrument in result.portfolio.instruments
    ]
    return {
        "schema_version": 1,
        "parameters": encode_workspace(result.config),
        "units": {
            "time": "years",
            "currency": result.config.currency,
            "rates": "annual decimal",
        },
        "axes": {
            "prices": ["path", "time", "asset"],
            "wealth": ["path", "time"],
            "instrument_values": ["path", "time", "instrument"],
        },
        "market": numerical_payload(result.market),
        "portfolio": portfolio,
        "analysis": numerical_payload(result.analysis),
    }
