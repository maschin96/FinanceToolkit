"""Offline index references, opt-in network boundary and cache replay."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import pytest

from finance_toolkit.index_lab import demo_histories
from finance_toolkit.tui.config import decode_workspace
from finance_toolkit.yahoo import Quote, YahooClient


def test_demo_preview_then_two_asset_index_reference():
    from finance_toolkit.tui.index_service import (
        calculate_prepared_index,
        prepare_index,
    )

    config = decode_workspace({})
    prepared = prepare_index(config)
    assert prepared.excluded_sessions == ()
    result = calculate_prepared_index(prepared, config)
    np.testing.assert_allclose(
        result.index.price.levels, [100, 100, 125, 135], rtol=0, atol=1e-10
    )
    np.testing.assert_array_equal(
        result.index.total_return.levels, result.index.price.levels
    )
    np.testing.assert_allclose(
        result.index.price.contributions.sum(axis=1),
        result.index.price.returns,
        rtol=0,
        atol=1e-12,
    )
    assert result.index.metadata["sources"]["A"]["mode"] == "synthetic"
    weighted = replace(config, index=replace(config.index, weights=(0.2, 0.8)))
    np.testing.assert_allclose(
        calculate_prepared_index(prepared, weighted).index.price.levels,
        [100, 88, 110, 126],
        rtol=0,
        atol=1e-10,
    )
    with pytest.raises(ValueError, match="data request changed"):
        calculate_prepared_index(
            prepared, replace(config, index=replace(config.index, tickers=("A", "C")))
        )


def test_yahoo_opt_in_cache_replay_and_quote_metadata(tmp_path):
    from finance_toolkit.tui.index_service import (
        calculate_prepared_index,
        prepare_index,
        run_quotes,
    )

    class Provider:
        calls = 0

        def history(self, ticker, start, end, timeout, repair):
            self.calls += 1
            return replace(
                demo_histories([ticker])[ticker], repaired=repair, source_mode="online"
            )

        def quote(self, ticker, timeout):
            self.calls += 1
            return Quote(
                ticker,
                100,
                "USD",
                "SYNTHETIC",
                "UTC",
                datetime(2026, 1, 6, tzinfo=UTC),
                datetime(2026, 1, 7, tzinfo=UTC),
                None,
                "UNKNOWN",
                "online",
                source="synthetic fake",
            )

    provider = Provider()
    client = YahooClient(provider=provider, cache=tmp_path, retries=0)
    config = decode_workspace(
        {"index": {"source": "yahoo", "cache": str(tmp_path), "repair": True}}
    )
    with pytest.raises(ValueError, match="explicit"):
        prepare_index(config, client=client)
    assert provider.calls == 0
    online = prepare_index(config, client=client, online_authorized=True)
    expected_calls = provider.calls
    replay_config = replace(config, index=replace(config.index, source="replay"))
    replay = prepare_index(replay_config, client=client)
    assert provider.calls == expected_calls
    assert replay.histories["A"].source_mode == "cache"
    assert replay.histories["A"].data_hash == online.histories["A"].data_hash
    np.testing.assert_array_equal(
        calculate_prepared_index(replay, replay_config).index.price.levels,
        calculate_prepared_index(online, config).index.price.levels,
    )
    with pytest.raises(ValueError, match="explicit"):
        run_quotes(config, client=client)
    quotes = run_quotes(config, client=client, online_authorized=True)
    assert quotes.quotes["A"].currency == "USD"
    assert quotes.quotes["A"].delay_seconds is None


def test_preview_missing_sessions_before_intersection_and_mixed_currency_rejection():
    from finance_toolkit.tui.index_service import (
        calculate_prepared_index,
        prepare_index,
    )

    class Client:
        def history(self, *args, **kwargs):
            data = demo_histories(["A", "B"])
            data["B"] = replace(data["B"], bars=data["B"].bars[:1] + data["B"].bars[2:])
            return data

    config = decode_workspace(
        {"index": {"source": "replay", "calendar_policy": "intersection"}}
    )
    prepared = prepare_index(config, client=Client())
    assert prepared.excluded_sessions == ("2026-01-02",)
    assert prepared.missing_sessions["B"] == ("2026-01-02",)
    with pytest.raises(ValueError, match="calendar"):
        calculate_prepared_index(
            prepared,
            replace(config, index=replace(config.index, calendar_policy="strict")),
        )
    assert (
        "2026-01-02" not in calculate_prepared_index(prepared, config).index.price.dates
    )
    bad = replace(
        prepared,
        histories={
            **prepared.histories,
            "B": replace(prepared.histories["B"], currency="EUR"),
        },
    )
    with pytest.raises(ValueError, match="currency"):
        calculate_prepared_index(bad, config)


def test_headless_offline_data_preview_and_index():
    pytest.importorskip("textual")
    from finance_toolkit.tui.app import create_app

    async def scenario():
        app = create_app()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("ctrl+5", "ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert "Sitzungen" in str(app.query_one("#index-preview").render())
            app.query_one("#calculate-index").focus()
            await pilot.press("enter")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.exportable
            assert app.query_one("#index-levels").row_count == 4
            assert "Punkte" in str(app.query_one("#index-summary").render())
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_missing_yahoo_extra_has_actionable_error(monkeypatch):
    import importlib

    from finance_toolkit.tui.index_service import prepare_index
    from finance_toolkit.yahoo import DataError

    original = importlib.import_module

    def without_yahoo(name, *args, **kwargs):
        if name == "yfinance":
            raise ModuleNotFoundError("blocked", name="yfinance")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", without_yahoo)
    with pytest.raises(DataError, match=r"finance-toolkit\[yahoo\]"):
        prepare_index(
            decode_workspace({"index": {"source": "yahoo", "retries": 0}}),
            online_authorized=True,
        )


def test_headless_online_action_and_cache_miss_remain_explicit(tmp_path):
    pytest.importorskip("textual")
    from textual.widgets import Input

    from finance_toolkit.tui.app import create_app

    class Provider:
        calls = 0

        def history(self, ticker, start, end, timeout, repair):
            self.calls += 1
            return replace(demo_histories([ticker])[ticker], source_mode="online")

    provider = Provider()
    client = YahooClient(provider=provider, cache=tmp_path, retries=0)

    async def scenario():
        app = create_app(data_client=client)
        async with app.run_test(size=(120, 40)) as pilot:
            assert provider.calls == 0
            await pilot.press("ctrl+5")
            app.query_one("#index-source", Input).value = "yahoo"
            await pilot.pause()
            await pilot.press("ctrl+r")
            assert provider.calls == 0
            assert app.jobs.run_id == 0
            app.query_one("#fetch-index").focus()
            await pilot.press("enter")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.state == "succeeded"
            assert provider.calls == 2
            app.query_one("#index-source", Input).value = "replay"
            app.query_one("#index-start", Input).value = "2026-02-01"
            app.query_one("#index-end", Input).value = "2026-02-05"
            await pilot.pause()
            await pilot.press("ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.state == "failed"
            assert "cache" in app.jobs.error
            assert provider.calls == 2
            await pilot.press("ctrl+q")

    asyncio.run(scenario())
