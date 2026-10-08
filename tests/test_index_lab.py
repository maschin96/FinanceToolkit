import json
import subprocess
import sys
from datetime import UTC, datetime

import numpy as np
import pytest

from finance_toolkit.index_lab import build_indices, export_indices
from finance_toolkit.yahoo import Bar, History


def history(ticker, close, adjusted, currency="USD", days=(1, 2, 5)):
    bars = tuple(
        Bar(
            datetime(2026, 1, day, tzinfo=UTC),
            price,
            price,
            price,
            price,
            adj,
            100,
            1 if i == 2 else 0,
            2 if i == 1 else 0,
        )
        for i, (day, price, adj) in enumerate(zip(days, close, adjusted, strict=True))
    )
    return History(
        ticker,
        currency,
        "SYNTHETIC",
        "UTC",
        datetime(2026, 1, 6, tzinfo=UTC),
        bars,
        False,
        source="synthetic test fixture",
    )


def test_split_neutral_dividend_only_in_total_return_and_export(tmp_path):
    data = {"A": history("A", [50, 50, 49], [49, 49, 49])}
    result = build_indices(data, base_date="2026-01-01")
    np.testing.assert_allclose(result.price.levels, [100, 100, 98], atol=1e-12)
    np.testing.assert_equal(result.total_return.levels, [100, 100, 100])
    assert result.metadata["sources"]["A"]["hash"] == data["A"].data_hash
    export_indices(result, tmp_path)
    assert (tmp_path / "index.csv").is_file()
    assert (
        json.loads((tmp_path / "index.json").read_text())["metadata"]["currency"]
        == "USD"
    )


def test_missing_sessions_explicit_and_currency_unit_normalized():
    data = {
        "A": history("A", [100, 110, 120], [100, 110, 120]),
        "B": history("B", [100, 110], [100, 110], days=(1, 5)),
    }
    with pytest.raises(ValueError, match="calendar"):
        build_indices(data, base_date="2026-01-01")
    result = build_indices(data, base_date="2026-01-01", calendar_policy="intersection")
    assert result.metadata["excluded_sessions"] == ["2026-01-02"]
    gbp = {
        "A": history("A", [100, 110, 120], [100, 110, 120], currency="GBP"),
        "B": history("B", [10000, 11000, 12000], [10000, 11000, 12000], currency="GBp"),
    }
    normalized = build_indices(gbp, base_date="2026-01-01")
    np.testing.assert_allclose(normalized.price.levels, [100, 110, 120], atol=1e-12)
    gbp["B"] = history("B", [100, 110, 120], [100, 110, 120], currency="EUR")
    with pytest.raises(ValueError, match="currency"):
        build_indices(gbp, base_date="2026-01-01")


def test_offline_demo_cli_is_reproducible(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            dict(
                tickers=["ALPHA", "BETA"],
                start="2026-01-01",
                end="2026-01-07",
                base_date="2026-01-01",
                weights=[0.5, 0.5],
                base_value=100,
            )
        )
    )
    outputs = []
    for name in ("a", "b"):
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "finance_toolkit.index_lab",
                "--config",
                str(config),
                "--demo",
                "--output",
                str(tmp_path / name),
            ],
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, run.stderr
        outputs.append((tmp_path / name / "index.json").read_text())
    assert outputs[0] == outputs[1]


def test_monthly_signal_is_current_session_and_next_session_execution():
    def make(ticker):
        bars = tuple(
            Bar(
                datetime(2026, month, day, tzinfo=UTC),
                price,
                price,
                price,
                price,
                price,
                100,
                0,
                0,
            )
            for month, day, price in ((1, 30, 100), (2, 2, 120), (2, 3, 150))
        )
        return History(
            ticker,
            "USD",
            "SYNTHETIC",
            "UTC",
            datetime(2026, 2, 4, tzinfo=UTC),
            bars,
            False,
        )

    data = {"A": make("A")}
    result = build_indices(data, base_date="2026-01-30", monthly=True)
    assert result.metadata["rebalance_signals"] == ["2026-02-02"]
    assert result.price.rebalance_executions == ("2026-02-03",)


def test_cached_cli_and_optional_png(tmp_path):
    from finance_toolkit.yahoo import YahooClient

    data = {"A": history("A", [50, 50, 49], [49, 49, 49])}

    class Provider:
        def history(self, ticker, start, end, timeout, repair):
            return data[ticker]

        def quote(self, ticker, timeout):
            raise AssertionError("no quotes needed")

    cache = tmp_path / "cache"
    YahooClient(provider=Provider(), cache=cache).history(
        ["A"], start="2026-01-01", end="2026-01-06"
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            dict(
                tickers=["A"],
                start="2026-01-01",
                end="2026-01-06",
                base_date="2026-01-01",
            )
        )
    )
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "finance_toolkit.index_lab",
            "--config",
            str(config),
            "--offline",
            "--cache",
            str(cache),
            "--output",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert (
        json.loads((tmp_path / "out" / "index.json").read_text())["metadata"][
            "sources"
        ]["A"]["mode"]
        == "cache"
    )


def test_optional_index_plot(tmp_path):
    pytest.importorskip("matplotlib")
    data = {"A": history("A", [50, 50, 49], [49, 49, 49])}
    export_indices(
        build_indices(data, base_date="2026-01-01"), tmp_path / "plot", plot=True
    )
    assert (
        (tmp_path / "plot" / "index.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    )
