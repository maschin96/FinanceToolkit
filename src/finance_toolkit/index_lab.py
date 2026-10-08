"""Index configuration/normalized-data adapter and offline/online CLI."""

import argparse
import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import ArrayLike

from finance_toolkit import __version__
from finance_toolkit.indices import IndexPaths, calculate_index
from finance_toolkit.yahoo import Bar, DataError, History, YahooClient, _unit


@dataclass(frozen=True)
class IndexResult:
    price: IndexPaths
    total_return: IndexPaths
    metadata: dict[str, Any]


def build_indices(
    histories: Mapping[str, History],
    *,
    base_date: str,
    weights: ArrayLike | None = None,
    base_value: float = 100.0,
    calendar_policy: Literal["strict", "intersection"] = "strict",
    rebalance_dates: Sequence[str] = (),
    monthly: bool = False,
) -> IndexResult:
    """Aligned fixed universe, split-adjusted Close vs dividend-adjusted Adj Close.

    Strict common sessions by default. Intersection opt-in records every excluded
    and missing date; never forward fills. No FX; minor units explicitly scaled.
    Monthly signals at first observed session of a new month, execution following
    session, so no future session list is needed for the decision.
    """
    if (
        not histories
        or calendar_policy not in ("strict", "intersection")
        or type(monthly) is not bool
        or (monthly and rebalance_dates)
    ):
        raise ValueError(
            "nonempty history, explicit calendar and one rebalance rule required"
        )
    tickers = tuple(histories)
    currencies = {_unit(x.currency)[0] for x in histories.values()}
    if len(currencies) != 1:
        raise ValueError("common currency required; no implicit FX conversion")
    maps: dict[str, dict[str, Bar]] = {}
    for ticker, history in histories.items():
        if (
            ticker != history.ticker
            or history.adjustment != "split_adjusted_close_dividend_adjusted_adj_close"
        ):
            raise ValueError("symbol or adjustment model mismatch")
        maps[ticker] = {
            bar.time.astimezone(ZoneInfo(history.timezone)).date().isoformat(): bar
            for bar in history.bars
        }
    calendars = [set(rows) for rows in maps.values()]
    union = set.union(*calendars)
    common = set.intersection(*calendars)
    if calendar_policy == "strict" and union != common:
        raise ValueError("calendar mismatch; opt into documented intersection policy")
    dates = sorted(common)
    if not dates:
        raise ValueError("no common trading sessions")
    scales = [_unit(histories[ticker].currency)[1] for ticker in tickers]
    close = np.array(
        [
            [
                maps[ticker][day].close * scale
                for ticker, scale in zip(tickers, scales, strict=True)
            ]
            for day in dates
        ]
    )
    adjusted = np.array(
        [
            [
                maps[ticker][day].adjusted_close * scale
                for ticker, scale in zip(tickers, scales, strict=True)
            ]
            for day in dates
        ]
    )
    signals = tuple(rebalance_dates)
    if monthly:
        signals = tuple(
            day
            for previous, day in zip(dates, dates[1:], strict=False)
            if day[:7] != previous[:7] and day >= base_date
        )
    price = calculate_index(
        dates,
        close,
        tickers=tickers,
        weights=weights,
        base_date=base_date,
        base_value=base_value,
        rebalance_dates=signals,
    )
    total = calculate_index(
        dates,
        adjusted,
        tickers=tickers,
        weights=weights,
        base_date=base_date,
        base_value=base_value,
        rebalance_dates=signals,
    )
    metadata = {
        "version": __version__,
        "numpy_version": np.__version__,
        "currency": next(iter(currencies)),
        "tickers": list(tickers),
        "base_date": base_date,
        "base_value": base_value,
        "weights": price.weights[0].tolist(),
        "calendar_policy": calendar_policy,
        "excluded_sessions": sorted(union - common),
        "missing_sessions_by_symbol": {
            ticker: sorted(union - set(rows)) for ticker, rows in maps.items()
        },
        "rebalance_rule": "monthly_first_observed_session"
        if monthly
        else "explicit"
        if signals
        else "buy_and_hold",
        "rebalance_signals": list(signals),
        "rebalance_executions": list(price.rebalance_executions),
        "price_model": "split-adjusted close; dividends excluded",
        "total_return_model": (
            "dividend-adjusted Adj Close; no corporate-action double application"
        ),
        "units": {
            "level": "base index points",
            "holdings": "synthetic units of adjusted series",
            "weights": "fractions",
            "contributions": "interval return fractions",
        },
        "sources": {
            ticker: {
                "hash": history.data_hash,
                "fetched_at": history.fetched_at.isoformat(),
                "source": history.source,
                "mode": history.source_mode,
                "exchange": history.exchange,
                "timezone": history.timezone,
                "adjustment": history.adjustment,
                "repair_enabled": history.repaired,
                "currency": history.currency,
                "original_currency": history.original_currency,
                "unit_scale": history.unit_scale,
                "additional_index_unit_scale": scale,
            }
            for (ticker, history), scale in zip(histories.items(), scales, strict=True)
        },
    }
    return IndexResult(price, total, metadata)


def export_indices(result: IndexResult, directory: Path, *, plot: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)

    def encode(index: IndexPaths) -> dict[str, Any]:
        values = asdict(index)
        for name in ("levels", "returns", "holdings", "weights", "contributions"):
            values[name] = getattr(index, name).tolist()
        return values

    (directory / "index.json").write_text(
        json.dumps(
            {
                "metadata": result.metadata,
                "price": encode(result.price),
                "total_return": encode(result.total_return),
            },
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with (directory / "index.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "kind",
                "date",
                "level",
                "return",
                "ticker",
                "holdings",
                "weight",
                "contribution",
            ]
        )
        for kind, index in [
            ("price", result.price),
            ("total_return", result.total_return),
        ]:
            for t, day in enumerate(index.dates):
                for j, ticker in enumerate(index.tickers):
                    writer.writerow(
                        [
                            kind,
                            day,
                            index.levels[t],
                            index.returns[t],
                            ticker,
                            index.holdings[t, j],
                            index.weights[t, j],
                            index.contributions[t, j],
                        ]
                    )
    if plot:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        figure = Figure(figsize=(8, 5))
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        for label, index in [
            ("Price", result.price),
            ("Total return", result.total_return),
        ]:
            ax.plot(index.dates, index.levels, label=label)
        ax.set(
            xlabel="Session", ylabel="Index points", title="Fixed universe custom index"
        )
        ax.legend()
        figure.autofmt_xdate()
        figure.savefig(directory / "index.png")


def demo_histories(tickers: Sequence[str]) -> dict[str, History]:
    """Original synthetic reference, no Yahoo data or external service access."""
    result = {}
    for j, ticker in enumerate(tickers):
        prices = [
            100.0,
            120.0 if j % 2 == 0 else 80.0,
            150.0 if j % 2 == 0 else 100.0,
            150.0 if j % 2 == 0 else 120.0,
        ]
        bars = tuple(
            Bar(
                datetime(2026, 1, day, tzinfo=UTC),
                spot,
                spot,
                spot,
                spot,
                spot,
                1000,
                0,
                0,
            )
            for day, spot in zip((1, 2, 5, 6), prices, strict=True)
        )
        result[ticker] = History(
            ticker,
            "USD",
            "SYNTHETIC",
            "UTC",
            datetime(2026, 1, 7, tzinfo=UTC),
            bars,
            False,
            source="original synthetic FinanceToolkit demo",
            source_mode="synthetic",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Custom indices from Yahoo cache or synthetic demo"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("outputs/yahoo"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("outputs/index-lab"))
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        tickers = tuple(str(x).strip().upper() for x in config["tickers"])
        if (
            not tickers
            or len(set(tickers)) != len(tickers)
            or any(not x for x in tickers)
        ):
            raise ValueError("nonempty distinct tickers required")
        histories = (
            demo_histories(tickers)
            if args.demo
            else YahooClient(cache=args.cache).history(
                tickers,
                start=config["start"],
                end=config["end"],
                repair=config.get("repair", False),
                offline=args.offline,
            )
        )
        rule = config.get("rebalance", "buy_and_hold")
        if rule not in ("buy_and_hold", "monthly", "explicit"):
            raise ValueError("unknown rebalance rule")
        signals = config.get("rebalance_dates", [])
        if rule == "buy_and_hold" and signals:
            raise ValueError("buy_and_hold cannot include rebalance dates")
        result = build_indices(
            histories,
            base_date=config["base_date"],
            weights=config.get("weights"),
            base_value=config.get("base_value", 100),
            calendar_policy=config.get("calendar_policy", "strict"),
            rebalance_dates=signals,
            monthly=rule == "monthly",
        )
        result.metadata["input_config"] = config
        export_indices(result, args.output, plot=args.plot)
    except (DataError, ValueError, OSError, KeyError, ImportError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
