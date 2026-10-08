"""Optional Yahoo boundary; normalized immutable records and explicit offline cache.

No provider/DataFrame imports until YFinanceProvider is used. Yahoo data is not
licensed by this package; library license grants no market-data usage rights.
"""

import argparse
import hashlib
import importlib
import json
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from functools import partial
from pathlib import Path
from typing import Any, Protocol, TypeVar
from zoneinfo import ZoneInfo

from finance_toolkit._validation import finite_float, positive_integer


class DataError(RuntimeError):
    """Unavailable/partial/schema-invalid provider or cache data, never zero prices."""


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")


@dataclass(frozen=True)
class Bar:
    """Provider daily bar label (not tick time), major currency per share.

    Close is Yahoo split-adjusted; adjusted_close also dividend-adjusted.
    Volume shares; dividend currency/share; split ratio (zero means no event).
    """

    time: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: float
    dividend: float
    split: float

    def __post_init__(self) -> None:
        _aware(self.time)
        for name in (
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
            "dividend",
            "split",
        ):
            object.__setattr__(self, name, finite_float(getattr(self, name), name))
        if (
            min(self.open, self.high, self.low, self.close, self.adjusted_close) <= 0
            or min(self.volume, self.dividend, self.split) < 0
            or self.low > min(self.open, self.close)
            or self.high < max(self.open, self.close)
        ):
            raise ValueError("invalid OHLCV or corporate action")


@dataclass(frozen=True)
class History:
    """Daily records with provenance; empty, duplicate or unsorted dates rejected."""

    ticker: str
    currency: str
    exchange: str
    timezone: str
    fetched_at: datetime
    bars: tuple[Bar, ...]
    repaired: bool
    source_mode: str = "online"
    source: str = "Yahoo Finance via yfinance"
    adjustment: str = "split_adjusted_close_dividend_adjusted_adj_close"
    original_currency: str = ""
    unit_scale: float = 1.0
    raw_records: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        _aware(self.fetched_at)
        ZoneInfo(self.timezone)
        if not all((self.ticker, self.currency, self.exchange)) or not self.bars:
            raise ValueError("nonempty history and symbol/currency/exchange required")
        if any(
            a.time >= b.time for a, b in zip(self.bars, self.bars[1:], strict=False)
        ):
            raise ValueError("duplicate or unordered bar timestamps")
        if len(
            {x.time.astimezone(ZoneInfo(self.timezone)).date() for x in self.bars}
        ) != len(self.bars):
            raise ValueError("duplicate daily session labels")
        if (
            type(self.repaired) is not bool
            or finite_float(self.unit_scale, "unit_scale") <= 0
        ):
            raise ValueError("invalid adjustment audit")

    @property
    def data_hash(self) -> str:
        """Stable hash of data/model identity, excluding cache/live presentation."""
        payload = asdict(self)
        payload.pop("source_mode")
        return hashlib.sha256(_json(payload).encode()).hexdigest()


@dataclass(frozen=True)
class Quote:
    """Latest regular-market quote; unknown delay stays None, no realtime claim."""

    ticker: str
    price: float
    currency: str
    exchange: str
    timezone: str
    market_time: datetime
    fetched_at: datetime
    delay_seconds: float | None
    session: str
    source_mode: str
    source: str = "Yahoo Finance via yfinance"

    def __post_init__(self) -> None:
        _aware(self.market_time)
        _aware(self.fetched_at)
        ZoneInfo(self.timezone)
        object.__setattr__(self, "price", finite_float(self.price, "price"))
        if self.price <= 0 or not all(
            (self.ticker, self.currency, self.exchange, self.session)
        ):
            raise ValueError("invalid quote metadata or price")
        if (
            self.delay_seconds is not None
            and finite_float(self.delay_seconds, "delay_seconds") < 0
        ):
            raise ValueError("delay must be nonnegative or unknown")

    def age_seconds(self, now: datetime) -> float:
        """Observed market timestamp age, not inferred exchange delay."""
        _aware(now)
        return max(0.0, (now - self.market_time).total_seconds())


class Provider(Protocol):
    def history(
        self, ticker: str, start: str, end: str, timeout: float, repair: bool
    ) -> History: ...
    def quote(self, ticker: str, timeout: float) -> Quote: ...


def _unit(currency: str) -> tuple[str, float]:
    return {"GBp": ("GBP", 0.01), "ZAc": ("ZAR", 0.01), "ILA": ("ILS", 0.01)}.get(
        currency, (currency, 1.0)
    )


def _json(value: Any) -> str:
    return json.dumps(
        value,
        default=lambda x: x.isoformat() if isinstance(x, datetime) else str(x),
        sort_keys=True,
        allow_nan=False,
    )


class YFinanceProvider:
    """Lazy yfinance boundary: single-symbol requests avoid ambiguous batch schemas.

    No silent repairs; explicit auto_adjust=False/back_adjust=False/actions=True.
    Request timeout bounds history calls. Metadata comes from that cached request.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        ticker_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.clock = clock
        self.factory = ticker_factory

    def _ticker(self, symbol: str) -> Any:
        if self.factory is not None:
            return self.factory(symbol)
        try:
            module = importlib.import_module("yfinance")
        except ImportError as error:
            raise DataError(
                "install finance-toolkit[yahoo] for online Yahoo access"
            ) from error
        return module.Ticker(symbol)

    def history(
        self, ticker: str, start: str, end: str, timeout: float, repair: bool
    ) -> History:
        obj = self._ticker(ticker)
        frame = obj.history(
            start=start,
            end=end,
            interval="1d",
            auto_adjust=False,
            back_adjust=False,
            actions=True,
            repair=repair,
            keepna=True,
            rounding=False,
            timeout=timeout,
            raise_errors=True,
        )
        meta = obj.get_history_metadata()
        original = str(meta.get("currency", ""))
        currency, scale = _unit(original)
        timezone = str(meta.get("exchangeTimezoneName", ""))
        exchange = str(meta.get("exchangeName", ""))
        rows: list[Bar] = []
        raw: list[dict[str, Any]] = []
        # A provider may expose MultiIndex columns; accept only this symbol.
        for timestamp, row in frame.iterrows():

            def field(name: str, row: Any = row) -> float:
                if name in frame.columns:
                    return float(row[name])
                for key in ((name, ticker), (ticker, name)):
                    if key in frame.columns:
                        return float(row[key])
                raise DataError(f"{ticker}: missing provider column {name}")

            dt = timestamp.to_pydatetime()
            data = {
                name: field(name)
                for name in (
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Adj Close",
                    "Volume",
                    "Dividends",
                    "Stock Splits",
                )
            }
            raw.append({"time": dt.isoformat(), **data})
            rows.append(
                Bar(
                    dt,
                    data["Open"] * scale,
                    data["High"] * scale,
                    data["Low"] * scale,
                    data["Close"] * scale,
                    data["Adj Close"] * scale,
                    data["Volume"],
                    data["Dividends"] * scale,
                    data["Stock Splits"],
                )
            )
        return History(
            ticker,
            currency,
            exchange,
            timezone,
            self.clock(),
            tuple(rows),
            repair,
            original_currency=original,
            unit_scale=scale,
            raw_records=tuple(raw),
        )

    def quote(self, ticker: str, timeout: float) -> Quote:
        obj = self._ticker(ticker)
        obj.history(
            period="1d",
            interval="1m",
            auto_adjust=False,
            back_adjust=False,
            actions=False,
            repair=False,
            timeout=timeout,
            raise_errors=True,
        )
        meta = obj.get_history_metadata()
        currency, scale = _unit(str(meta.get("currency", "")))
        try:
            price = float(meta["regularMarketPrice"]) * scale
            market_time = meta["regularMarketTime"]
            timestamp = (
                market_time.astimezone(UTC)
                if isinstance(market_time, datetime)
                else datetime.fromtimestamp(float(market_time), UTC)
            )
            delay = meta.get("exchangeDataDelayedBy")
            return Quote(
                ticker,
                price,
                currency,
                str(meta["exchangeName"]),
                str(meta["exchangeTimezoneName"]),
                timestamp,
                self.clock(),
                None if delay is None else float(delay) * 60,
                str(meta.get("marketState") or "UNKNOWN"),
                "online",
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DataError(f"{ticker}: incomplete quote metadata") from error


T = TypeVar("T")


def _symbols(tickers: Sequence[str]) -> tuple[str, ...]:
    result = tuple(x.strip().upper() for x in tickers)
    if not result or any(not x for x in result) or len(set(result)) != len(result):
        raise ValueError("nonempty distinct ticker symbols required")
    return result


class YahooClient:
    """Finite requests/retries; explicit cache replay; errors identify failed symbol."""

    def __init__(
        self,
        *,
        provider: Provider | None = None,
        cache: Path | None = None,
        timeout: float = 10.0,
        retries: int = 2,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.timeout = finite_float(timeout, "timeout")
        if (
            self.timeout <= 0
            or isinstance(retries, bool)
            or not isinstance(retries, int)
            or not 0 <= retries <= 5
        ):
            raise ValueError("positive timeout and retries integer 0..5 required")
        self.retries = retries
        self.cache = cache
        self.clock = clock
        self.sleep = sleep
        self.provider = provider or YFinanceProvider(clock=clock)

    def _retry(self, ticker: str, fetch: Callable[[], T]) -> T:
        for attempt in range(self.retries + 1):
            try:
                return fetch()
            except Exception as error:
                transient = isinstance(error, (TimeoutError, ConnectionError)) or type(
                    error
                ).__name__ in (
                    "YFRateLimitError",
                    "Timeout",
                    "RequestsError",
                    "ConnectionError",
                )
                if not transient or attempt == self.retries:
                    raise DataError(
                        f"{ticker}: {type(error).__name__}: {error}"
                    ) from error
                self.sleep(min(0.5 * 2**attempt, 8.0))
        raise AssertionError("unreachable retry")

    def _path(self, request: dict[str, Any]) -> Path:
        if self.cache is None:
            raise DataError("cache directory required")
        return self.cache / (
            hashlib.sha256(_json(request).encode()).hexdigest() + ".json"
        )

    def history(
        self,
        tickers: Sequence[str],
        *,
        start: str,
        end: str,
        repair: bool = False,
        offline: bool = False,
    ) -> dict[str, History]:
        symbols = _symbols(tickers)
        if (
            date.fromisoformat(start) >= date.fromisoformat(end)
            or type(repair) is not bool
            or type(offline) is not bool
        ):
            raise ValueError(
                "ordered dates (end exclusive) and boolean policies required"
            )
        result: dict[str, History] = {}
        for ticker in symbols:
            request = {
                "ticker": ticker,
                "start": start,
                "end": end,
                "repair": repair,
                "interval": "1d",
                "schema": 1,
            }
            if offline:
                try:
                    payload = json.loads(self._path(request).read_text())
                    data = payload["history"]
                    data["fetched_at"] = datetime.fromisoformat(data["fetched_at"])
                    data["bars"] = tuple(
                        Bar(**{**b, "time": datetime.fromisoformat(b["time"])})
                        for b in data["bars"]
                    )
                    data["raw_records"] = tuple(data["raw_records"])
                    history = History(**data)
                    if (
                        payload["request"] != request
                        or payload["hash"] != history.data_hash
                    ):
                        raise ValueError("cache identity/hash mismatch")
                    history = replace(history, source_mode="cache")
                except (OSError, ValueError, KeyError, TypeError) as error:
                    raise DataError(
                        f"{ticker}: invalid/missing cache: {error}"
                    ) from error
            else:
                history = self._retry(
                    ticker,
                    partial(
                        self.provider.history, ticker, start, end, self.timeout, repair
                    ),
                )
                if history.ticker != ticker or history.repaired != repair:
                    raise DataError(f"{ticker}: provider identity/repair mismatch")
                if self.cache is not None:
                    self.cache.mkdir(parents=True, exist_ok=True)
                    self._path(request).write_text(
                        _json(
                            {
                                "request": request,
                                "history": asdict(history),
                                "hash": history.data_hash,
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
            result[ticker] = history
        return result

    def quotes(self, tickers: Sequence[str]) -> dict[str, Quote]:
        result = {}
        for ticker in _symbols(tickers):
            quote = self._retry(
                ticker, partial(self.provider.quote, ticker, self.timeout)
            )
            if quote.ticker != ticker:
                raise DataError(f"{ticker}: provider quote identity mismatch")
            result[ticker] = quote
        return result

    def watch(
        self, tickers: Sequence[str], *, count: int, interval: float = 30.0
    ) -> Iterator[dict[str, Quote]]:
        """Explicit finite polling, stops on error or caller/KeyboardInterrupt."""
        count = positive_integer(count, "count")
        interval = finite_float(interval, "interval")
        if interval <= 0:
            raise ValueError("positive polling interval required")
        for index in range(count):
            if index:
                self.sleep(interval)
            yield self.quotes(tickers)

    def stream(self, tickers: Sequence[str]) -> None:
        _symbols(tickers)
        raise DataError(
            "native stream unsupported by this adapter; choose explicit polling watch"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Yahoo daily history or latest regular quotes; explicit polling"
    )
    parser.add_argument("action", choices=["history", "quote", "watch"])
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--interval", type=float, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    client = YahooClient(cache=args.cache, timeout=args.timeout, retries=args.retries)
    try:
        if args.action == "history":
            if not args.start or not args.end:
                parser.error("history requires --start and --end")
            histories = client.history(
                args.tickers,
                start=args.start,
                end=args.end,
                repair=args.repair,
                offline=args.offline,
            )
            output = _json(
                {
                    key: {**asdict(value), "data_hash": value.data_hash}
                    for key, value in histories.items()
                }
            )
        else:
            if args.offline or args.repair:
                parser.error("offline/repair supported only for history")
            batches = (
                client.watch(args.tickers, count=args.count, interval=args.interval)
                if args.action == "watch"
                else iter([client.quotes(args.tickers)])
            )
            lines = []
            for batch in batches:
                line = _json(
                    {
                        key: {
                            **asdict(value),
                            "age_seconds": value.age_seconds(datetime.now(UTC)),
                        }
                        for key, value in batch.items()
                    }
                )
                if args.output is None:
                    print(line, flush=True)
                lines.append(line)
            output = "\n".join(lines)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
        elif args.action == "history":
            print(output)
    except (DataError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    except KeyboardInterrupt:
        parser.exit(130, "polling stopped\n")


if __name__ == "__main__":
    main()
