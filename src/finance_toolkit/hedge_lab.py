"""Reproducible offline hedge/strategy comparisons on one coupled base market."""

import argparse
import csv
import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from finance_toolkit import __version__
from finance_toolkit._validation import positive_integer
from finance_toolkit.analytics import drawdown, tail_risk
from finance_toolkit.attribution import attribute_book, export_attribution
from finance_toolkit.hedging import HedgePaths, simulate_hedge
from finance_toolkit.option_strategies import StrategyName, build_strategy
from finance_toolkit.options_book import BookPaths, Order, simulate_book
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.simulation import GBMPaths, simulate_gbm


@dataclass(frozen=True)
class ComparisonCase:
    """Subsample stride dividing base steps; rule and nonnegative currency fees."""

    name: str
    stride: int = 1
    calendar_every: int | None = None
    threshold: float | None = None
    fixed_fee: float = 0.0
    proportional_fee: float = 0.0


@dataclass(frozen=True)
class Comparison:
    config: dict[str, object]
    books: dict[str, BookPaths]
    hedges: dict[str, HedgePaths]
    metrics: list[dict[str, str | float | None]]
    strategies: dict[str, BookPaths]
    strategy_metrics: list[dict[str, str | float | None]]


def _metrics(
    name: str, book: BookPaths, hedge: HedgePaths | None = None
) -> dict[str, str | float | None]:
    pnl = book.wealth[:, -1] - book.initial_cash
    risk = tail_risk(-pnl)
    return {
        "name": name,
        "mean_pnl": float(pnl.mean()),
        "rms_replication_pnl": float(np.sqrt(np.mean(pnl**2))),
        "mean_terminal_wealth": float(book.wealth[:, -1].mean()),
        "mean_return": float(pnl.mean() / book.initial_cash)
        if book.initial_cash > 0
        else None,
        "var_95": risk.value_at_risk,
        "es_95": risk.expected_shortfall,
        "mean_max_drawdown": float(drawdown(book.wealth).max(axis=1).mean())
        if np.all(book.wealth > 0)
        else None,
        "mean_fees": float(book.fees.sum(axis=(1, 2)).mean()),
        "mean_turnover": float(book.turnover.sum(axis=(1, 2)).mean()),
        "mean_financing": float(book.financing.sum(axis=1).mean()),
        "mean_stock_borrow": float(book.stock_borrow_costs.sum(axis=(1, 2)).mean()),
        "rms_residual_delta": float(np.sqrt(np.mean(hedge.residual_delta**2)))
        if hedge
        else None,
    }


def compare_hedges(
    market: GBMPaths,
    cases: Sequence[ComparisonCase],
    *,
    initial_cash: float,
    option: EuropeanOption | None = None,
    option_quantity: float = -1.0,
    rate: float = 0.0,
    lending_rate: float = 0.0,
    borrowing_rate: float = 0.0,
    stock_borrow_rate: float = 0.0,
    simulation_config: dict[str, float | int] | None = None,
) -> Comparison:
    """Same opening options/capital/prices; coarse paths are exact base subsets.

    RMS replication P&L targets zero terminal gain for the short-option hedge
    under risk-neutral zero-cost financing assumptions. With capital/costs/rates
    it is a descriptive P&L RMS, no universal pricing error or ranking.
    Strategy builder controls run on the unchanged fine grid without trade fees.
    """
    if not cases or len({x.name for x in cases}) != len(cases):
        raise ValueError("distinct nonempty comparison cases required")
    option = option or EuropeanOption(
        0, 100, float(market.times[-1]), 0.2, multiplier=1
    )
    if option.maturity != market.times[-1]:
        raise ValueError("comparison horizon must equal option maturity")
    assets = market.prices.shape[2]
    instruments = tuple(Stock(j) for j in range(assets)) + (option,)
    opening = (Order(assets, option_quantity),)
    books: dict[str, BookPaths] = {}
    hedges: dict[str, HedgePaths] = {}
    metrics = []
    for case in cases:
        stride = positive_integer(case.stride, "stride")
        if (
            not re.fullmatch(r"[A-Za-z0-9_-]+", case.name)
            or (market.times.size - 1) % stride
        ):
            raise ValueError("safe case name and stride dividing base steps required")
        sub = GBMPaths(market.times[::stride], market.prices[:, ::stride])
        calendar = None
        if case.calendar_every is not None:
            frequency = positive_integer(case.calendar_every, "calendar_every")
            calendar = sub.times[:-1:frequency]
        hedge = simulate_hedge(
            sub,
            instruments,
            initial_cash=initial_cash,
            initial_orders=opening,
            calendar=calendar,
            threshold=case.threshold,
            rate=rate,
            fixed_fee=case.fixed_fee,
            proportional_fee=case.proportional_fee,
            lending_rate=lending_rate,
            borrowing_rate=borrowing_rate,
            stock_borrow_rate=stock_borrow_rate,
        )
        books[case.name] = hedge.book
        hedges[case.name] = hedge
        metrics.append(_metrics(case.name, hedge.book, hedge))
    strategy_books: dict[str, BookPaths] = {}
    names: tuple[StrategyName, ...] = (
        "protective_put",
        "covered_call",
        "collar",
        "bull_call",
        "bear_put",
    )
    for name in names:
        strategy = build_strategy(
            name,
            lower_strike=option.strike * 0.9,
            upper_strike=option.strike * 1.1,
            maturity=option.maturity,
            volatility=option.volatility,
            asset=option.asset,
            multiplier=option.multiplier,
            dividend_yield=option.dividend_yield,
        )
        strategy_books[name] = simulate_book(
            market,
            strategy.instruments,
            initial_cash=initial_cash,
            initial_orders=strategy.orders(),
            rate=rate,
            allow_borrowing=True,
            lending_rate=lending_rate,
            borrowing_rate=borrowing_rate,
        )
    digest = hashlib.sha256(
        market.times.tobytes() + market.prices.tobytes()
    ).hexdigest()
    config: dict[str, object] = {
        "version": __version__,
        "numpy_version": np.__version__,
        "simulation": simulation_config,
        "path_hash": digest,
        "base_times": market.times.tolist(),
        "prices_shape": list(market.prices.shape),
        "initial_cash": initial_cash,
        "option": asdict(option),
        "option_quantity": option_quantity,
        "rate": rate,
        "lending_rate": lending_rate,
        "borrowing_rate": borrowing_rate,
        "stock_borrow_rate": stock_borrow_rate,
        "cases": [asdict(x) for x in cases],
        "strategy_controls": list(names),
        "strategy_control_fees": 0,
        "units": {
            "time": "years",
            "prices": "currency per share",
            "pnl": "currency",
            "delta_threshold": "shares",
            "rates": "annual decimal",
            "VaR_ES": "loss currency; empirical confidence .95",
        },
    }
    return Comparison(
        config,
        books,
        hedges,
        metrics,
        strategy_books,
        [_metrics(name, book) for name, book in strategy_books.items()],
    )


def export_comparison(
    result: Comparison, directory: Path, *, plot: bool = False
) -> None:
    """CSV/JSON including full config, actual ledgers and attribution; optional PNG."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "comparison.json").write_text(
        json.dumps(
            {
                "config": result.config,
                "metrics": result.metrics,
                "strategies": result.strategy_metrics,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for filename, rows in [
        ("comparison.csv", result.metrics),
        ("strategies.csv", result.strategy_metrics),
    ]:
        with (directory / filename).open("w", newline="", encoding="utf-8") as stream:
            metrics_writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            metrics_writer.writeheader()
            metrics_writer.writerows(rows)
    with (directory / "wealth.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "kind",
                "name",
                "path",
                "time",
                "wealth",
                "cash",
                "financing",
                "fees",
                "stock_borrow",
                "turnover",
                "target_shares",
                "before_delta",
                "residual_delta",
            ]
        )
        for kind, books in [("hedge", result.books), ("strategy", result.strategies)]:
            for name, book in books.items():
                hedge = result.hedges.get(name) if kind == "hedge" else None
                for p in range(book.wealth.shape[0]):
                    for t, time in enumerate(book.times):
                        writer.writerow(
                            [
                                kind,
                                name,
                                p,
                                time,
                                book.wealth[p, t],
                                book.cash[p, t],
                                book.financing[p, t],
                                book.fees[p, t].sum(),
                                book.stock_borrow_costs[p, t].sum(),
                                book.turnover[p, t].sum(),
                                json.dumps(hedge.target_shares[p, t].tolist())
                                if hedge
                                else None,
                                json.dumps(hedge.before_delta[p, t].tolist())
                                if hedge
                                else None,
                                json.dumps(hedge.residual_delta[p, t].tolist())
                                if hedge
                                else None,
                            ]
                        )
                export_attribution(attribute_book(book), directory / name)
    fine_book = next(iter(result.strategies.values()))
    with (directory / "market.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["path", "time", "asset", "spot"])
        for p in range(fine_book.spots.shape[0]):
            for t, time in enumerate(fine_book.times):
                for asset in range(fine_book.spots.shape[2]):
                    writer.writerow([p, time, asset, fine_book.spots[p, t, asset]])
    with (directory / "ledgers.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        fields = (
            "quantities",
            "quotes",
            "values",
            "trades",
            "trade_cashflows",
            "fees",
            "settlements",
            "stock_borrow_costs",
            "turnover",
        )
        writer.writerow(["kind", "name", "path", "time", "instrument", *fields])
        for kind, books in [("hedge", result.books), ("strategy", result.strategies)]:
            for name, book in books.items():
                for p in range(book.wealth.shape[0]):
                    for t, time in enumerate(book.times):
                        for j in range(len(book.instruments)):
                            writer.writerow(
                                [
                                    kind,
                                    name,
                                    p,
                                    time,
                                    j,
                                    *[
                                        getattr(book, field)[p, t, j]
                                        for field in fields
                                    ],
                                ]
                            )
    if plot:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        figure = Figure(figsize=(8, 5))
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        for name, book in result.books.items():
            ax.plot(book.times, book.wealth.mean(axis=0), label=name)
        ax.set(
            xlabel="Time (years)",
            ylabel="Mean wealth (currency)",
            title="Coupled hedge comparison",
        )
        ax.legend()
        figure.savefig(directory / "comparison.png")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline coupled hedge/strategy comparison"
    )
    parser.add_argument("--paths", type=int, default=100)
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--seed", type=int, default=314)
    parser.add_argument("--output", type=Path, default=Path("outputs/hedge-lab"))
    parser.add_argument("--calendar-every", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.1, 0.25])
    parser.add_argument("--fees", type=float, nargs="+", default=[0.0, 0.05])
    parser.add_argument("--strides", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    try:
        market = simulate_gbm(
            100,
            drift=0,
            volatility=0.2,
            horizon=1,
            steps=args.steps,
            paths=args.paths,
            seed=args.seed,
        )
        cases = [ComparisonCase("unhedged")]
        for stride in args.strides:
            for fee_index, fee in enumerate(args.fees):
                for frequency in args.calendar_every:
                    cases.append(
                        ComparisonCase(
                            f"calendar_s{stride}_n{frequency}_f{fee_index}",
                            stride,
                            calendar_every=frequency,
                            fixed_fee=fee,
                        )
                    )
                for index, threshold in enumerate(args.thresholds):
                    cases.append(
                        ComparisonCase(
                            f"threshold_s{stride}_n{index}_f{fee_index}",
                            stride,
                            threshold=threshold,
                            fixed_fee=fee,
                        )
                    )
        result = compare_hedges(
            market,
            cases,
            initial_cash=1000,
            simulation_config={
                "seed": args.seed,
                "spot": 100,
                "drift": 0,
                "volatility": 0.2,
                "horizon": 1,
                "steps": args.steps,
                "paths": args.paths,
            },
        )
        export_comparison(result, args.output, plot=args.plot)
    except (ValueError, ImportError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
