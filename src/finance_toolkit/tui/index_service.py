"""Two-step data preview and index calculation; online calls require opt-in."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from finance_toolkit.index_lab import IndexResult, build_indices, demo_histories
from finance_toolkit.tui.config import Workspace, decode_workspace, encode_workspace
from finance_toolkit.yahoo import History, Quote, YahooClient


class IndexClient(Protocol):
    def history(
        self,
        tickers: Sequence[str],
        *,
        start: str,
        end: str,
        repair: bool = False,
        offline: bool = False,
    ) -> dict[str, History]: ...


class QuoteClient(Protocol):
    def quotes(self, tickers: Sequence[str]) -> dict[str, Quote]: ...


@dataclass(frozen=True)
class IndexData:
    """Prepared data plus calendar audit, displayed before numerical use."""

    config: Workspace
    histories: dict[str, History]
    excluded_sessions: tuple[str, ...]
    missing_sessions: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class IndexRunResult:
    """Price/total-return index and original data-request provenance."""

    config: Workspace
    data: IndexData
    index: IndexResult


@dataclass(frozen=True)
class QuoteResult:
    """Explicit quote request, actual timestamps/units, no realtime assertion."""

    config: Workspace
    quotes: dict[str, Quote]


def prepare_index(
    workspace: Workspace,
    *,
    client: IndexClient | None = None,
    online_authorized: bool = False,
) -> IndexData:
    """Fetch only an explicit online request; demo/replay never fall back online."""
    snapshot = decode_workspace(encode_workspace(workspace))
    config = snapshot.index
    if (
        not config.tickers
        or len(set(config.tickers)) != len(config.tickers)
        or any(not ticker.strip() for ticker in config.tickers)
    ):
        raise ValueError("distinct nonempty tickers required")
    start, end = date.fromisoformat(config.start), date.fromisoformat(config.end)
    if start >= end:
        raise ValueError("start must precede exclusive end date")
    if config.source == "demo":
        histories = {}
        for ticker, history in demo_histories(config.tickers).items():
            bars = tuple(
                bar
                for bar in history.bars
                if start <= bar.time.astimezone(ZoneInfo(history.timezone)).date() < end
            )
            histories[ticker] = replace(history, bars=bars)
    else:
        if config.source == "yahoo" and not online_authorized:
            raise ValueError("online history requires explicit Yahoo action")
        data_client = client or YahooClient(
            cache=Path(config.cache), timeout=config.timeout, retries=config.retries
        )
        histories = data_client.history(
            config.tickers,
            start=config.start,
            end=config.end,
            repair=config.repair,
            offline=config.source == "replay",
        )
    calendars = {
        ticker: {
            bar.time.astimezone(ZoneInfo(history.timezone)).date().isoformat()
            for bar in history.bars
        }
        for ticker, history in histories.items()
    }
    union = set.union(*calendars.values())
    common = set.intersection(*calendars.values())
    return IndexData(
        snapshot,
        histories,
        tuple(sorted(union - common)),
        {
            ticker: tuple(sorted(union - sessions))
            for ticker, sessions in calendars.items()
        },
    )


def calculate_prepared_index(data: IndexData, workspace: Workspace) -> IndexRunResult:
    """Calculate only after preview; weights/calendar edits may reuse identical data.

    A changed ticker/interval/source/cache/repair request requires new preparation.
    Existing public build_indices preserves calendar, unit and currency rules.
    """
    snapshot = decode_workspace(encode_workspace(workspace))
    previous, config = data.config.index, snapshot.index
    for field in ("source", "tickers", "start", "end", "cache", "repair"):
        if getattr(previous, field) != getattr(config, field):
            raise ValueError("data request changed; prepare/preview data again")
    index = build_indices(
        data.histories,
        base_date=config.base_date,
        weights=config.weights,
        base_value=config.base_value,
        calendar_policy=config.calendar_policy,
        rebalance_dates=config.rebalance_dates,
        monthly=config.monthly,
    )
    return IndexRunResult(snapshot, data, index)


def run_quotes(
    workspace: Workspace,
    *,
    client: QuoteClient | None = None,
    online_authorized: bool = False,
) -> QuoteResult:
    """Run an explicit quote action with finite timeout/retries, never on startup."""
    if not online_authorized:
        raise ValueError("quotes require explicit Yahoo action")
    snapshot = decode_workspace(encode_workspace(workspace))
    config = snapshot.index
    data_client = client or YahooClient(timeout=config.timeout, retries=config.retries)
    return QuoteResult(snapshot, data_client.quotes(config.tickers))
