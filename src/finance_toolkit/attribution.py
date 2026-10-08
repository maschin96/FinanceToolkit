"""Exact ledger reconciliation and local Greek approximation, never causality."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from finance_toolkit._validation import finite_float
from finance_toolkit.instruments.options import black_scholes, option_greeks
from finance_toolkit.options_book import BookPaths
from finance_toolkit.portfolio import EuropeanOption, Stock


def explain_option_move(
    option: EuropeanOption,
    *,
    quantity: float,
    spot_start: float,
    spot_end: float,
    time_start: float,
    time_end: float,
    volatility_start: float,
    volatility_end: float,
    rate_start: float,
    rate_end: float,
) -> dict[str, float | bool]:
    """Currency P&L for unchanged contracts, ex-open to end including settlement.

    Local Taylor: delta*dS + gamma*dS²/2 + vega*dSigma + theta*dt + rho*dr.
    Decimal annual sigma/r changes; elapsed time years. No cross/higher Greeks.
    At expiry/non-smooth beginning, no Taylor is claimed: components zero and
    full actual movement is explicitly an event residual. Beyond expiry reject.
    """
    quantity = finite_float(quantity, "quantity")
    time_start = finite_float(time_start, "time_start")
    time_end = finite_float(time_end, "time_end")
    if not 0 <= time_start <= time_end <= option.maturity:
        raise ValueError("times must be ordered within option life")
    start = float(
        black_scholes(
            spot_start,
            option.strike,
            option.maturity - time_start,
            volatility_start,
            rate_start,
            dividend_yield=option.dividend_yield,
            kind=option.kind,
        )
    )
    end = float(
        black_scholes(
            spot_end,
            option.strike,
            option.maturity - time_end,
            volatility_end,
            rate_end,
            dividend_yield=option.dividend_yield,
            kind=option.kind,
        )
    )
    scale = quantity * option.multiplier
    actual = scale * (end - start)
    result: dict[str, float | bool] = {
        name: 0.0 for name in ("delta", "gamma", "vega", "theta", "rho")
    }
    event = (
        time_end == option.maturity
        or spot_start == 0
        or volatility_start == 0
        or time_start == option.maturity
    )
    if not event and quantity != 0:
        g = option_greeks(
            spot_start,
            option.strike,
            option.maturity - time_start,
            volatility_start,
            rate_start,
            dividend_yield=option.dividend_yield,
            kind=option.kind,
        )
        ds = spot_end - spot_start
        result.update(
            delta=scale * float(g.delta) * ds,
            gamma=scale * float(g.gamma) * ds**2 / 2,
            vega=scale * float(g.vega) * (volatility_end - volatility_start),
            theta=scale * float(g.theta) * (time_end - time_start),
            rho=scale * float(g.rho) * (rate_end - rate_start),
        )
    approximation = sum(
        float(result[x]) for x in ("delta", "gamma", "vega", "theta", "rho")
    )
    result.update(actual=actual, residual=actual - approximation, event=event)
    return result


@dataclass(frozen=True)
class Attribution:
    """Intervals (paths,times-1,instruments); portfolio financing/P&L (paths,times-1).

    market includes settlements for interval-start holdings; execution includes
    trade cash plus new holdings' model value. fees/borrow positive charges.
    relative_pnl uses interval-start wealth or None for nonpositive basis.
    """

    times: NDArray[np.float64]
    market: NDArray[np.float64]
    execution: NDArray[np.float64]
    settlements: NDArray[np.float64]
    fees: NDArray[np.float64]
    borrow: NDArray[np.float64]
    financing: NDArray[np.float64]
    delta: NDArray[np.float64]
    gamma: NDArray[np.float64]
    vega: NDArray[np.float64]
    theta: NDArray[np.float64]
    rho: NDArray[np.float64]
    residual: NDArray[np.float64]
    events: NDArray[np.bool_]
    relative_pnl: list[list[float | None]]

    @property
    def approximation(self) -> NDArray[np.float64]:
        return np.asarray(
            self.delta + self.gamma + self.vega + self.theta + self.rho,
            dtype=np.float64,
        )

    @property
    def reconciled(self) -> NDArray[np.float64]:
        return np.asarray(
            (self.market + self.execution - self.fees - self.borrow).sum(axis=-1)
            + self.financing,
            dtype=np.float64,
        )


def attribute_book(book: BookPaths) -> Attribution:
    """Reconcile actual book intervals using unchanged beginning holdings.

    Opening trades/fees belong to initial wealth, not later period P&L. Payment
    is internal conversion of instrument value to cash; shown separately as
    settlements within market, never added twice. Execution slippage is visible.
    Book currently uses constant pricing rate/model vols; standalone move API
    additionally handles explicit rate/volatility shocks.
    """
    shape = book.quantities[:, 1:].shape
    market, execution, delta, gamma, vega, theta, rho = (
        np.zeros(shape) for _ in range(7)
    )
    events = np.zeros(shape, dtype=bool)
    for j, x in enumerate(book.instruments):
        multiplier = x.multiplier if isinstance(x, EuropeanOption) else 1.0
        market[:, :, j] = (
            book.quantities[:, :-1, j]
            * np.diff(book.quotes[:, :, j], axis=1)
            * multiplier
            + book.settlements[:, 1:, j]
        )
        execution[:, :, j] = (
            book.trades[:, 1:, j] * book.quotes[:, 1:, j] * multiplier
            + book.trade_cashflows[:, 1:, j]
        )
        if isinstance(x, Stock):
            delta[:, :, j] = market[:, :, j]
        else:
            for p in range(shape[0]):
                for t in range(shape[1]):
                    if book.quantities[p, t, j] == 0:
                        continue
                    components = explain_option_move(
                        x,
                        quantity=float(book.quantities[p, t, j]),
                        spot_start=float(book.spots[p, t, x.asset]),
                        spot_end=float(book.spots[p, t + 1, x.asset]),
                        time_start=float(book.times[t]),
                        time_end=float(book.times[t + 1]),
                        volatility_start=x.volatility,
                        volatility_end=x.volatility,
                        rate_start=book.rate,
                        rate_end=book.rate,
                    )
                    for name, array in [
                        ("delta", delta),
                        ("gamma", gamma),
                        ("vega", vega),
                        ("theta", theta),
                        ("rho", rho),
                    ]:
                        array[p, t, j] = float(components[name])
                    events[p, t, j] = bool(components["event"])
    residual = market - delta - gamma - vega - theta - rho
    pnl = np.diff(book.wealth, axis=1)
    relative = [
        [
            float(pnl[p, t] / book.wealth[p, t]) if book.wealth[p, t] > 0 else None
            for t in range(shape[1])
        ]
        for p in range(shape[0])
    ]
    result = Attribution(
        book.times[1:].copy(),
        market,
        execution,
        book.settlements[:, 1:].copy(),
        book.fees[:, 1:].copy(),
        book.stock_borrow_costs[:, 1:].copy(),
        book.financing[:, 1:].copy(),
        delta,
        gamma,
        vega,
        theta,
        rho,
        residual,
        events,
        relative,
    )
    if not np.allclose(result.reconciled, pnl, rtol=1e-12, atol=1e-10):
        raise ValueError("book P&L does not reconcile")
    return result


def export_attribution(result: Attribution, directory: Path) -> None:
    """Write inspectable position and portfolio components; null relative bases."""
    directory.mkdir(parents=True, exist_ok=True)
    names = (
        "market",
        "execution",
        "settlements",
        "fees",
        "borrow",
        "delta",
        "gamma",
        "vega",
        "theta",
        "rho",
        "residual",
        "events",
    )
    data = {name: getattr(result, name).tolist() for name in names}
    data.update(
        times=result.times.tolist(),
        financing=result.financing.tolist(),
        pnl=result.reconciled.tolist(),
        relative_pnl=result.relative_pnl,
        units={
            "values": "currency",
            "time": "years",
            "delta": "currency per share-price unit times dS",
            "gamma": "half currency per squared price unit times dS squared",
            "vega": "currency per decimal annual volatility times dSigma",
            "rho": "currency per decimal annual rate times dr",
            "theta": "currency per elapsed year times dt",
        },
    )
    (directory / "attribution.json").write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    with (directory / "attribution.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "path",
                "time",
                "instrument",
                *names,
                "portfolio_financing",
                "portfolio_pnl",
                "relative_pnl",
            ]
        )
        for p in range(result.market.shape[0]):
            for t, time in enumerate(result.times):
                for j in range(result.market.shape[2]):
                    writer.writerow(
                        [
                            p,
                            time,
                            j,
                            *[getattr(result, name)[p, t, j] for name in names],
                            result.financing[p, t],
                            result.reconciled[p, t],
                            result.relative_pnl[p][t],
                        ]
                    )
