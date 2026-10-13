import json
from dataclasses import asdict, replace
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


class HistoryProvider(Provider):
    def __init__(self, history):
        super().__init__()
        self.response = history

    def history(self, ticker, start, end, timeout, repair):
        self.calls += 1
        return self.response


def _synthetic_history(labels, zone):
    return History(
        "A",
        "USD",
        "TEST",
        zone,
        NOW,
        tuple(
            Bar(datetime.fromisoformat(label), 100, 101, 99, 100, 100, 0, 0, 0)
            for label in labels
        ),
        False,
    )


@pytest.mark.parametrize("offline", [False, True])
@pytest.mark.parametrize(
    "zone,start,end,label",
    [
        ("UTC", "2026-01-05", "2026-01-06", "2020-01-01T00:00:00+00:00"),
        ("UTC", "2026-01-05", "2026-01-06", "2026-01-04T23:59:59+00:00"),
        ("UTC", "2026-01-05", "2026-01-06", "2026-01-06T00:00:00+00:00"),
        ("UTC", "2026-01-05", "2026-01-06", "2026-01-07T00:00:00+00:00"),
        # DST begins March 8: UTC is within the request, local session is not.
        ("America/New_York", "2026-03-08", "2026-03-10", "2026-03-08T04:59:59+00:00"),
        ("America/New_York", "2026-03-08", "2026-03-10", "2026-03-10T04:00:00+00:00"),
        ("Asia/Tokyo", "2026-01-05", "2026-01-06", "2026-01-05T15:00:00+00:00"),
        # DST ends November 1: exclusive end is midnight EST (05:00 UTC).
        ("America/New_York", "2026-11-01", "2026-11-02", "2026-11-02T05:00:00+00:00"),
    ],
)
def test_history_rejects_outside_local_sessions_online_and_cache(
    tmp_path, offline, zone, start, end, label
):
    bad = _synthetic_history([label], zone)
    provider = HistoryProvider(bad)
    client = YahooClient(provider=provider, cache=tmp_path, retries=0)
    if offline:
        # Seed a legitimate cache, then model an old, internally consistent
        # cache containing out-of-request data. Hash/identity remain valid.
        provider.response = _synthetic_history([f"{start}T12:00:00+00:00"], zone)
        client.history(["A"], start=start, end=end)
        path = next(tmp_path.glob("*.json"))
        payload = json.loads(path.read_text())
        payload.update(history=asdict(bad), hash=bad.data_hash)
        path.write_text(json.dumps(payload, default=lambda value: value.isoformat()))
        before = path.read_bytes()
        calls = provider.calls
    with pytest.raises(DataError, match="A:.*outside.*interval"):
        client.history(["A"], start=start, end=end, offline=offline)
    if offline:
        assert provider.calls == calls
        assert path.read_bytes() == before
    else:
        assert provider.calls == 1
        assert list(tmp_path.glob("*.json")) == []


@pytest.mark.parametrize(
    "zone,start,end,labels",
    [
        ("UTC", "2026-01-05", "2026-01-06", ["2026-01-05T00:00:00+00:00"]),
        ("UTC", "2026-01-05", "2026-01-06", ["2026-01-05T23:59:59+00:00"]),
        ("Asia/Tokyo", "2026-01-05", "2026-01-06", ["2026-01-04T15:00:00+00:00"]),
        (
            "America/New_York",
            "2026-03-08",
            "2026-03-10",
            ["2026-03-08T05:00:00+00:00", "2026-03-09T04:00:00+00:00"],
        ),
        ("America/New_York", "2026-03-08", "2026-03-10", ["2026-03-10T03:59:59+00:00"]),
        ("America/New_York", "2026-11-01", "2026-11-02", ["2026-11-02T04:59:59+00:00"]),
        # Good Friday / weekend gaps are deliberately not filled or rejected.
        (
            "UTC",
            "2026-04-02",
            "2026-04-07",
            ["2026-04-02T00:00:00+00:00", "2026-04-06T00:00:00+00:00"],
        ),
    ],
)
def test_history_accepts_local_inclusive_start_exclusive_end_and_partial_intervals(
    tmp_path, zone, start, end, labels
):
    expected = _synthetic_history(labels, zone)
    provider = HistoryProvider(expected)
    client = YahooClient(provider=provider, cache=tmp_path, retries=0)
    live = client.history(["A"], start=start, end=end)["A"]
    replay = client.history(["A"], start=start, end=end, offline=True)["A"]
    assert live == expected
    assert replay == replace(expected, source_mode="cache")
    assert provider.calls == 1
    assert [bar.time.isoformat() for bar in replay.bars] == labels


def test_invalid_response_does_not_overwrite_previous_valid_cache(tmp_path):
    provider = Provider()
    client = YahooClient(provider=provider, cache=tmp_path)
    client.history(["A"], start="2026-01-01", end="2026-01-06")
    path = next(tmp_path.glob("*.json"))
    before = path.read_bytes()
    client.provider = HistoryProvider(
        _synthetic_history(["2020-01-01T00:00:00+00:00"], "UTC")
    )
    with pytest.raises(DataError, match="A:.*outside.*interval"):
        client.history(["A"], start="2026-01-01", end="2026-01-06")
    assert path.read_bytes() == before
    assert (
        client.history(["A"], start="2026-01-01", end="2026-01-06", offline=True)["A"]
        .bars[0]
        .time
        == NOW
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
