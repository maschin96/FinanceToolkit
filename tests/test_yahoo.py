from datetime import UTC, datetime, timedelta

import pytest

from finance_toolkit.yahoo import Bar, DataError, History, Quote, YahooClient

NOW = datetime(2026, 1, 5, 16, tzinfo=UTC)


class Provider:
    def __init__(self):
        self.calls = 0
        self.fail = 0

    def history(self, ticker, start, end, timeout, repair):
        self.calls += 1
        if self.calls <= self.fail:
            raise TimeoutError("timeout")
        return History(
            ticker,
            "USD",
            "NMS",
            "America/New_York",
            NOW,
            (Bar(NOW, 100, 101, 99, 100, 100, 1000, 0, 0),),
            False,
        )

    def quote(self, ticker, timeout):
        self.calls += 1
        return Quote(
            ticker,
            100,
            "USD",
            "NMS",
            "America/New_York",
            NOW - timedelta(minutes=15),
            NOW,
            None,
            "REGULAR",
            "online",
        )


def test_history_cache_replay_without_network_and_age(tmp_path):
    provider = Provider()
    client = YahooClient(provider=provider, cache=tmp_path, clock=lambda: NOW)
    live = client.history(["A", "B"], start="2026-01-01", end="2026-01-06")
    assert provider.calls == 2
    old = YahooClient(
        provider=provider, cache=tmp_path, clock=lambda: NOW + timedelta(days=2)
    )
    cached = old.history(["A", "B"], start="2026-01-01", end="2026-01-06", offline=True)
    assert provider.calls == 2
    assert cached["A"].source_mode == "cache"
    assert cached["A"].fetched_at == NOW
    assert cached["A"].data_hash == live["A"].data_hash


def test_bounded_retry_and_no_silent_partial(tmp_path):
    provider = Provider()
    provider.fail = 2
    sleeps = []
    client = YahooClient(
        provider=provider, retries=2, clock=lambda: NOW, sleep=sleeps.append
    )
    client.history(["A"], start="2026-01-01", end="2026-01-06")
    assert provider.calls == 3
    assert sleeps == [0.5, 1.0]
    provider.fail = 99
    with pytest.raises(DataError, match="A"):
        client.history(["A"], start="2026-01-01", end="2026-01-06")
    assert provider.calls == 6


def test_quote_unknown_delay_not_zero_polling_explicit():
    provider = Provider()
    client = YahooClient(provider=provider, clock=lambda: NOW, sleep=lambda _: None)
    quote = client.quotes(["A"])["A"]
    assert quote.delay_seconds is None
    assert quote.age_seconds(NOW) == 900
    assert len(list(client.watch(["A"], count=3, interval=0.01))) == 3
    with pytest.raises(DataError, match="stream"):
        client.stream(["A"])


@pytest.mark.parametrize(
    "bad", [dict(close=float("nan")), dict(low=102), dict(volume=-1), dict(split=-1)]
)
def test_bad_bars(bad):
    args = dict(
        time=NOW,
        open=100,
        high=101,
        low=99,
        close=100,
        adjusted_close=100,
        volume=1000,
        dividend=0,
        split=0,
    )
    args.update(bad)
    with pytest.raises(ValueError):
        Bar(**args)


def test_duplicate_timezone_and_missing_currency_rejected():
    bar = Bar(NOW, 100, 101, 99, 100, 100, 1000, 0, 0)
    with pytest.raises(ValueError):
        History("A", "USD", "NMS", "America/New_York", NOW, (bar, bar), False)
    with pytest.raises(ValueError):
        History("A", "", "NMS", "America/New_York", NOW, (bar,), False)
    with pytest.raises(ValueError):
        Bar(NOW.replace(tzinfo=None), 100, 101, 99, 100, 100, 1000, 0, 0)


def test_missing_cache_and_invalid_requests(tmp_path):
    client = YahooClient(provider=Provider(), cache=tmp_path, clock=lambda: NOW)
    with pytest.raises(DataError, match="cache"):
        client.history(["A"], start="2026-01-01", end="2026-01-06", offline=True)
    for tickers in ([], ["A", "A"], [""]):
        with pytest.raises(ValueError):
            client.history(tickers, start="2026-01-01", end="2026-01-06")


class Timestamp:
    def __init__(self, value):
        self.value = value

    def to_pydatetime(self):
        return self.value


class Frame:
    def __init__(self, rows):
        self.rows = rows
        self.columns = set(rows[0][1]) if rows else set()

    def iterrows(self):
        return iter(self.rows)


class Ticker:
    def __init__(self, multi=False):
        self.kwargs = None
        self.meta = dict(
            currency="GBp",
            exchangeName="LSE",
            exchangeTimezoneName="Europe/London",
            regularMarketPrice=10000,
            regularMarketTime=NOW.timestamp(),
        )
        row = dict(
            Open=10000, High=10100, Low=9900, Close=10000, Volume=1000, Dividends=50
        )
        row["Adj Close"] = 9950
        row["Stock Splits"] = 0
        if multi:
            row = {(key, "A"): value for key, value in row.items()}
        self.frame = Frame([(Timestamp(NOW), row)])

    def history(self, **kwargs):
        self.kwargs = kwargs
        return self.frame

    def get_history_metadata(self):
        return self.meta


@pytest.mark.parametrize("multi", [False, True])
def test_native_provider_schema_units_and_explicit_flags(multi):
    from finance_toolkit.yahoo import YFinanceProvider

    ticker = Ticker(multi)
    provider = YFinanceProvider(clock=lambda: NOW, ticker_factory=lambda _: ticker)
    history = provider.history("A", "2026-01-01", "2026-01-06", 4, False)
    assert history.currency == "GBP"
    assert history.original_currency == "GBp"
    assert history.bars[0].close == 100
    assert history.bars[0].dividend == 0.5
    assert history.raw_records[0]["Close"] == 10000
    assert ticker.kwargs["auto_adjust"] is False
    assert ticker.kwargs["back_adjust"] is False
    assert ticker.kwargs["repair"] is False
    assert ticker.kwargs["timeout"] == 4
    quote = provider.quote("A", 4)
    assert quote.price == 100
    assert quote.delay_seconds is None
    assert quote.session == "UNKNOWN"


def test_native_empty_partial_and_nan_data_are_errors():
    from finance_toolkit.yahoo import YFinanceProvider

    for mutation in ("empty", "partial", "nan"):
        ticker = Ticker()
        if mutation == "empty":
            ticker.frame = Frame([])
        if mutation == "partial":
            ticker.frame.columns.remove("Adj Close")
        if mutation == "nan":
            ticker.frame.rows[0][1]["Close"] = float("nan")
        client = YahooClient(
            provider=YFinanceProvider(
                clock=lambda: NOW, ticker_factory=lambda _, ticker=ticker: ticker
            )
        )
        with pytest.raises(DataError):
            client.history(["A"], start="2026-01-01", end="2026-01-06")


def test_timezone_dst_preserves_actual_instants_and_cache_tampering(tmp_path):
    from zoneinfo import ZoneInfo

    zone = ZoneInfo("America/New_York")
    bars = tuple(
        Bar(datetime(2026, 3, day, tzinfo=zone), 100, 101, 99, 100, 100, 0, 0, 0)
        for day in (6, 9)
    )
    history = History("A", "USD", "NMS", str(zone), NOW, bars, False)
    assert history.bars[0].time.utcoffset() != history.bars[1].time.utcoffset()
    client = YahooClient(provider=Provider(), cache=tmp_path, clock=lambda: NOW)
    client.history(["A"], start="2026-01-01", end="2026-01-06")
    path = next(tmp_path.glob("*.json"))
    path.write_text(path.read_text().replace('"close": 100.0', '"close": 99.0'))
    with pytest.raises(DataError, match="hash"):
        client.history(["A"], start="2026-01-01", end="2026-01-06", offline=True)


def test_offline_cli_and_core_imports_are_provider_free(tmp_path):
    import json
    import subprocess
    import sys

    client = YahooClient(
        provider=Provider(), cache=tmp_path / "cache", clock=lambda: NOW
    )
    client.history(["A"], start="2026-01-01", end="2026-01-06")
    output = tmp_path / "data.json"
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "finance_toolkit.yahoo",
            "history",
            "A",
            "--start",
            "2026-01-01",
            "--end",
            "2026-01-06",
            "--offline",
            "--cache",
            str(tmp_path / "cache"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(output.read_text())["A"]["source_mode"] == "cache"
    core = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import finance_toolkit.hedging; "
            "assert 'pandas' not in sys.modules; "
            "assert 'yfinance' not in sys.modules",
        ],
        capture_output=True,
        text=True,
    )
    assert core.returncode == 0, core.stderr


def test_native_quote_accepts_provider_converted_timezone_timestamp():
    from finance_toolkit.yahoo import YFinanceProvider

    ticker = Ticker()
    ticker.meta["regularMarketTime"] = NOW
    quote = YFinanceProvider(clock=lambda: NOW, ticker_factory=lambda _: ticker).quote(
        "A", 4
    )
    assert quote.market_time == NOW
