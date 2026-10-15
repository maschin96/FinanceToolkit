"""Versioned configs and protected, full-precision transactional exports."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterator
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from threading import Lock
from typing import Any, TypeAlias

import numpy as np

from finance_toolkit.attribution import export_attribution
from finance_toolkit.examples import write_examples
from finance_toolkit.hedge_lab import export_comparison
from finance_toolkit.index_lab import export_indices
from finance_toolkit.risk_lab import RiskLab, write_risk_lab
from finance_toolkit.tui.config import Workspace, decode_workspace, encode_workspace
from finance_toolkit.tui.index_service import IndexRunResult, QuoteResult
from finance_toolkit.tui.risk_service import RiskResult
from finance_toolkit.tui.services import PortfolioResult, numerical_payload
from finance_toolkit.tui.strategy_service import StrategyResult

NumericResult: TypeAlias = (
    PortfolioResult | RiskResult | StrategyResult | IndexRunResult | QuoteResult
)
RESULT_TYPES = (
    PortfolioResult,
    RiskResult,
    StrategyResult,
    IndexRunResult,
    QuoteResult,
)


@dataclass(frozen=True)
class ExportedResult:
    """Successful file operation retains the underlying completed calculation."""

    result: NumericResult
    directory: Path


class ExportToken:
    """Linearize accepted cancellation against the short publication operation.

    Preparation stays cancellable. After publication commits, cancel returns
    False: the file operation has completed and must not be labelled cancelled.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._cancelled = False
        self._committed = False

    def request_cancel(self) -> bool:
        with self._lock:
            if self._committed:
                return False
            self._cancelled = True
            return True

    def check(self) -> None:
        with self._lock:
            if self._cancelled:
                raise ValueError("export cancelled before publication")

    def commit(self, action: Callable[[], None]) -> None:
        with self._lock:
            if self._cancelled:
                raise ValueError("export cancelled before publication")
            if self._committed:
                raise ValueError("export already published")
            action()
            self._committed = True


def save_workspace(
    workspace: Workspace, path: Path, *, overwrite: bool = False
) -> None:
    """Save exact JSON inputs; atomic replace or exclusive creation, never execute."""
    payload = (
        json.dumps(
            encode_workspace(workspace), indent=2, sort_keys=True, allow_nan=False
        )
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".finance-config-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_workspace(path: Path) -> Workspace:
    """Read/validate at most 2 MiB of config; no network, calculation or state edit."""
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("workspace configuration exceeds 2 MiB")
    return decode_workspace(json.loads(path.read_text(encoding="utf-8")))


def result_workspace(result: NumericResult) -> Workspace:
    """Return the immutable input snapshot associated with a numerical result."""
    return result.base.config if isinstance(result, RiskResult) else result.config


def unwrap_result(value: object) -> object:
    """Unwrap an export receipt without claiming a new numerical calculation."""
    return value.result if isinstance(value, ExportedResult) else value


def _structured(
    result: NumericResult,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    provenance: dict[str, Any] = {}
    volatile: dict[str, Any] = {}
    if isinstance(result, PortfolioResult):
        kind = "portfolio"
        values = dict(
            market=result.market, portfolio=result.portfolio, analysis=result.analysis
        )
        market = result.market
    elif isinstance(result, RiskResult):
        kind = "risk"
        values = dict(
            market=result.base.market,
            portfolio=result.base.portfolio,
            analysis=result.base.analysis,
            snapshot=result.snapshot,
            exposures=result.exposures,
            exposure_error=result.exposure_error,
            scenarios=result.scenarios,
            grid=result.grid,
        )
        market = result.base.market
    elif isinstance(result, StrategyResult):
        kind = "strategy"
        values = dict(
            market=result.market,
            rebalancing={
                name: dict(
                    ledger=book, wealth=book.wealth, pnl=book.wealth - book.initial_cash
                )
                for name, book in result.rebalancing.items()
            },
            books={
                name: dict(
                    ledger=book,
                    wealth=book.wealth,
                    pnl=book.wealth - book.initial_cash,
                    instrument_types=[
                        type(instrument).__name__ for instrument in book.instruments
                    ],
                )
                for name, book in result.books.items()
            },
            hedges={
                name: dict(
                    target_shares=hedge.target_shares,
                    before_delta=hedge.before_delta,
                    residual_delta=hedge.residual_delta,
                )
                for name, hedge in result.hedges.items()
            },
            attributions={
                name: dict(components=attribution, reconciled=attribution.reconciled)
                for name, attribution in result.attributions.items()
            },
        )
        market = result.market
        if result.comparison is not None:
            provenance["comparison"] = result.comparison.config
    elif isinstance(result, IndexRunResult):
        metadata = deepcopy(result.index.metadata)
        volatile["history_fetched_at"] = {
            ticker: source.pop("fetched_at")
            for ticker, source in metadata["sources"].items()
        }
        provenance["index"] = metadata
        provenance["data_request"] = asdict(result.data.config.index)
        return (
            "index",
            dict(price=result.index.price, total_return=result.index.total_return),
            provenance,
            volatile,
        )
    else:
        values = {
            ticker: dict(
                price=quote.price,
                currency=quote.currency,
                market_time=quote.market_time.isoformat(),
                exchange=quote.exchange,
                timezone=quote.timezone,
                delay_seconds=quote.delay_seconds,
                session=quote.session,
                source=quote.source,
                source_mode=quote.source_mode,
            )
            for ticker, quote in result.quotes.items()
        }
        volatile["quote_fetched_at"] = {
            ticker: quote.fetched_at.isoformat()
            for ticker, quote in result.quotes.items()
        }
        provenance["online_quote_action"] = True
        return "quotes", values, provenance, volatile
    provenance["path_hash"] = hashlib.sha256(
        market.times.tobytes() + market.prices.tobytes()
    ).hexdigest()
    return kind, values, provenance, volatile


def _versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {"python": sys.version.split()[0]}
    for package in (
        "finance-toolkit",
        "numpy",
        "scipy",
        "textual",
        "matplotlib",
        "yfinance",
    ):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    return result


def _arrays(
    value: object, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], np.ndarray]]:
    if isinstance(value, np.ndarray):
        yield path, value
    elif is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from _arrays(getattr(value, field.name), (*path, field.name))
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _arrays(item, (*path, str(key)))
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            yield from _arrays(item, (*path, str(index)))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _legacy_exports(result: NumericResult, stage: Path, *, plot: bool) -> None:
    if isinstance(result, PortfolioResult):
        write_examples({"portfolio": result.portfolio}, stage)
        _write_json(stage / "risk.json", {"portfolio": asdict(result.analysis.risk)})
    elif isinstance(result, RiskResult):
        analysis = result.base.analysis
        metrics = dict(
            mean_terminal_pnl=float(analysis.pnl[:, -1].mean()),
            mean_terminal_return=float(analysis.returns[:, -1].mean())
            if analysis.returns is not None
            else None,
            value_at_risk=analysis.risk.value_at_risk,
            expected_shortfall=analysis.risk.expected_shortfall,
        )
        report = RiskLab(
            {"workspace": encode_workspace(result.base.config)},
            result.base.market,
            {},
            {"portfolio": result.base.portfolio},
            {"portfolio": metrics},
            {"portfolio": result.snapshot},
            {"portfolio": result.exposures} if result.exposures is not None else {},
            {"portfolio": result.scenarios},
        )
        write_risk_lab(
            report,
            stage,
            grid_snapshot=result.snapshot,
            spot_shocks=result.base.config.risk.spot_shocks,
            volatility_shocks=result.base.config.risk.grid_volatility_shocks,
        )
        if plot:
            from finance_toolkit.risk_plots import plot_stress_heatmap

            plot_stress_heatmap(
                result.snapshot,
                result.base.config.risk.spot_shocks,
                result.base.config.risk.grid_volatility_shocks,
                stage / "stress_heatmap.png",
            )
    elif isinstance(result, StrategyResult):
        if result.comparison is not None:
            export_comparison(result.comparison, stage, plot=plot)
        for identity, attribution in result.attributions.items():
            kind, name = identity.split("/", 1)
            export_attribution(attribution, stage / kind / name)
    elif isinstance(result, IndexRunResult):
        export_indices(result.index, stage, plot=plot)
    if plot and isinstance(result, PortfolioResult | RiskResult | StrategyResult):
        _plot_wealth(result, stage / "wealth.png")


def _plot_wealth(
    result: PortfolioResult | RiskResult | StrategyResult, path: Path
) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(9, 5), layout="constrained")
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    if isinstance(result, StrategyResult):
        for name, book in result.books.items():
            axis.plot(book.times, book.wealth.mean(axis=0), label=name)
    else:
        base = result.base if isinstance(result, RiskResult) else result
        axis.plot(
            base.market.times, base.analysis.wealth.mean(axis=0), label="portfolio"
        )
    axis.set(
        xlabel="Time (years)",
        ylabel=f"Mean wealth ({result_workspace(result).currency})",
    )
    axis.legend(fontsize=7)
    figure.savefig(path)


def _preserve_unmanaged(target: Path, stage: Path) -> None:
    # New managed files already exist in an empty stage. Never follow an old
    # symlink while writing them; copy only noncolliding existing paths later.
    for source in target.rglob("*"):
        destination = stage / source.relative_to(target)
        if destination.exists() or destination.is_symlink():
            continue
        if source.is_symlink():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(
                os.readlink(source), target_is_directory=source.is_dir()
            )
        elif source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=False)


def _publish(stage: Path, target: Path, *, overwrite: bool) -> None:
    if target.is_symlink():
        raise ValueError("export target must be a real directory, not a symlink")
    if not target.exists():
        os.rename(stage, target)
        return
    if not overwrite:
        raise FileExistsError(f"Export exists: {target}; explicit overwrite required")
    if not target.is_dir():
        raise NotADirectoryError(str(target))
    backup = Path(tempfile.mkdtemp(prefix=".finance-backup-", dir=target.parent))
    backup.rmdir()
    os.replace(target, backup)
    try:
        os.replace(stage, target)
    except OSError:
        os.replace(backup, target)
        raise
    shutil.rmtree(backup)


def export_result(
    result: NumericResult,
    directory: Path,
    *,
    overwrite: bool = False,
    plot: bool = False,
    token: ExportToken | None = None,
) -> ExportedResult:
    """Stage complete CSV/JSON then publish with rollback and explicit overwrite.

    Unknown files at an existing target are preserved. Accepted cancellation
    before commit publishes nothing. Publication serializes with cancellation;
    an already committed operation cannot subsequently be labelled cancelled.
    Network access and recalculation are never initiated by export.
    """
    if not isinstance(result, RESULT_TYPES):
        raise ValueError("a completed numerical result is required before export")
    cancellation = token or ExportToken()
    cancellation.check()
    target = directory.absolute()
    if target.exists() and not overwrite:
        raise FileExistsError(f"Export exists: {target}; explicit overwrite required")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".finance-export-", dir=target.parent))
    try:
        config = result_workspace(result)
        kind, numerical, provenance, volatile = _structured(result)
        _write_json(
            stage / "result.json",
            dict(
                schema_version=1,
                kind=kind,
                parameters=encode_workspace(config),
                units={
                    "time": "years",
                    "portfolio_currency": config.currency,
                    "rates": "annual decimal",
                    "index": "base index points",
                },
                versions=_versions(),
                provenance=numerical_payload(provenance),
                numerical=numerical_payload(numerical),
                volatile_metadata=volatile,
            ),
        )
        _write_json(stage / "parameters.json", encode_workspace(config))
        array_info = {}
        with (stage / "arrays.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["field", "index", "value"])
            for field, array in _arrays(numerical):
                cancellation.check()
                key = json.dumps(field)
                array_info[key] = {
                    "shape": list(array.shape),
                    "dtype": str(array.dtype),
                }
                for index in np.ndindex(array.shape):
                    writer.writerow([key, json.dumps(index), array[index].item()])
        _legacy_exports(result, stage, plot=plot)
        cancellation.check()
        files = {
            str(path.relative_to(stage)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(stage.rglob("*"))
            if path.is_file()
        }
        _write_json(
            stage / "export_manifest.json",
            dict(
                schema_version=1,
                complete=True,
                kind=kind,
                files=files,
                arrays=array_info,
                volatile_fields=[
                    "result.json:volatile_metadata",
                    "index.json:metadata.sources.*.fetched_at",
                ],
            ),
        )
        if target.exists():
            if not overwrite:
                raise FileExistsError(str(target))
            _preserve_unmanaged(target, stage)
        cancellation.commit(lambda: _publish(stage, target, overwrite=overwrite))
        return ExportedResult(result, target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
