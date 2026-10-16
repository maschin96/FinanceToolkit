"""Exact configs, protected exports, rollback/cancellation and UI roundtrip."""

import asyncio
import csv
import json
from dataclasses import replace

import numpy as np
import pytest

from finance_toolkit.tui.config import Workspace, decode_workspace
from finance_toolkit.tui.services import run_portfolio


def test_config_roundtrip_unknown_schema_and_no_calculation(tmp_path, monkeypatch):
    import finance_toolkit.simulation as simulation
    from finance_toolkit.tui.workspace import load_workspace, save_workspace

    def forbidden(*args, **kwargs):
        raise AssertionError("loading cannot calculate")

    monkeypatch.setattr(simulation, "simulate_gbm", forbidden)
    config = decode_workspace(
        {
            "currency": "CHF",
            "simulation": {"seed": 99},
            "portfolio": {"rate": 0.03123456789012345},
            "hedge": {"cases": [{"name": "custom", "stride": 2}]},
        }
    )
    path = tmp_path / "workspace.json"
    save_workspace(config, path)
    assert load_workspace(path) == config
    with pytest.raises(FileExistsError):
        save_workspace(Workspace(), path)
    save_workspace(Workspace(), path, overwrite=True)
    assert load_workspace(path) == Workspace()
    path.write_text('{"schema_version": 999}')
    with pytest.raises(ValueError):
        load_workspace(path)
    with pytest.raises(FileNotFoundError):
        load_workspace(tmp_path / "missing.json")


def test_full_precision_export_is_reproducible_and_preserves_existing_files(tmp_path):
    from finance_toolkit.tui.workspace import export_result

    result = run_portfolio(decode_workspace({"simulation": {"paths": 2, "steps": 4}}))
    target = tmp_path / "export"
    export_result(result, target)
    payload = json.loads((target / "result.json").read_text())
    np.testing.assert_array_equal(
        payload["numerical"]["analysis"]["wealth"], result.analysis.wealth
    )
    assert payload["parameters"]["simulation"]["seed"] == 42
    assert payload["versions"]["numpy"]
    assert payload["provenance"]["path_hash"]
    assert json.loads((target / "export_manifest.json").read_text())["complete"]
    assert (target / "portfolio_wealth.csv").exists()
    rows = list(csv.DictReader((target / "arrays.csv").open()))
    wealth = [row for row in rows if json.loads(row["field"]) == ["analysis", "wealth"]]
    assert len(wealth) == 10
    np.testing.assert_array_equal(
        [float(row["value"]) for row in wealth], result.analysis.wealth.ravel()
    )
    second = tmp_path / "second"
    export_result(result, second)
    assert (
        json.loads((second / "result.json").read_text())["numerical"]
        == payload["numerical"]
    )
    (target / "private.txt").write_text("preserve me")
    with pytest.raises(FileExistsError):
        export_result(result, target)
    export_result(result, target, overwrite=True)
    assert (target / "private.txt").read_text() == "preserve me"


def test_export_cancellation_and_publish_failure_leave_no_new_complete_export(
    tmp_path, monkeypatch
):
    import finance_toolkit.tui.workspace as module
    from finance_toolkit.tui.workspace import ExportToken, export_result

    result = run_portfolio(decode_workspace({"simulation": {"paths": 1, "steps": 2}}))
    token = ExportToken()
    assert token.request_cancel()
    with pytest.raises(ValueError, match="cancel"):
        export_result(result, tmp_path / "cancelled", token=token)
    assert not (tmp_path / "cancelled").exists()
    target = tmp_path / "existing"
    target.mkdir()
    (target / "private.txt").write_text("unchanged")
    replace_original = module.os.replace
    calls = 0

    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected publication failure")
        return replace_original(source, destination)

    monkeypatch.setattr(module.os, "replace", fail_second)
    with pytest.raises(OSError, match="publication"):
        export_result(result, target, overwrite=True)
    assert (target / "private.txt").read_text() == "unchanged"
    assert not (target / "export_manifest.json").exists()


@pytest.mark.parametrize("kind", ["risk", "strategy", "index"])
def test_other_exports_keep_lab_contracts_and_full_numeric_payload(tmp_path, kind):
    from finance_toolkit.tui.workspace import export_result

    config = decode_workspace(
        {
            "simulation": {"paths": 1, "steps": 4},
            "hedge": {
                "enabled": True,
                "allow_short": True,
                "allow_borrowing": True,
                "case_names": ["protective_put", "coarse"],
            },
        }
    )
    if kind == "risk":
        from finance_toolkit.tui.risk_service import run_risk

        result = run_risk(
            replace(config, portfolio=replace(config.portfolio, initial_cash=0))
        )
    elif kind == "strategy":
        from finance_toolkit.tui.strategy_service import run_strategies

        result = run_strategies(config)
    else:
        from finance_toolkit.tui.index_service import (
            calculate_prepared_index,
            prepare_index,
        )

        result = calculate_prepared_index(prepare_index(config), config)
    export_result(result, tmp_path / "out")
    payload = json.loads((tmp_path / "out" / "result.json").read_text())
    assert payload["kind"] == kind
    assert payload["numerical"]
    if kind == "risk":
        assert (tmp_path / "out" / "stress.csv").exists()
        rows = list(csv.DictReader((tmp_path / "out" / "wealth.csv").open()))
        assert all(row["return"] == "" for row in rows)
    elif kind == "strategy":
        assert (
            tmp_path / "out" / "hedge" / "protective_put" / "attribution.json"
        ).exists()
        assert (
            tmp_path / "out" / "strategy" / "protective_put" / "attribution.json"
        ).exists()
        assert (tmp_path / "out" / "dynamic" / "scheduled" / "attribution.csv").exists()
    else:
        assert (tmp_path / "out" / "index.csv").exists()
        assert payload["volatile_metadata"]["history_fetched_at"]


def test_headless_workspace_save_load_rerun_and_export(tmp_path):
    pytest.importorskip("textual")
    from textual.widgets import Input

    from finance_toolkit.tui.app import create_app

    async def scenario():
        app = create_app()
        async with app.run_test(size=(120, 40)) as pilot:
            app.query_one("#seed", Input).value = "99"
            await pilot.pause()
            await pilot.press("ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            original = app.jobs.result.market.prices.copy()
            await pilot.press("ctrl+6")
            app.query_one("#workspace-path", Input).value = str(
                tmp_path / "session.json"
            )
            app.query_one("#save-workspace").focus()
            await pilot.press("enter")
            saved = (tmp_path / "session.json").read_text()
            (tmp_path / "session.json").write_text('{"schema_version": 999}')
            before = app.workspace
            app.query_one("#load-workspace").focus()
            await pilot.press("enter")
            assert app.workspace == before
            (tmp_path / "session.json").write_text(saved)
            await pilot.pause(0.5)  # Textual button press animation/debounce
            app.query_one("#seed", Input).value = "123"
            await pilot.pause()
            old_run = app.jobs.run_id
            app.query_one("#load-workspace").focus()
            await pilot.press("enter")
            assert app.workspace.simulation.seed == 99
            assert app.jobs.run_id == old_run
            assert app.jobs.stale
            await pilot.press("ctrl+1", "ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            np.testing.assert_array_equal(app.jobs.result.market.prices, original)
            await pilot.press("ctrl+6")
            app.query_one("#export-path", Input).value = str(tmp_path / "export")
            app.query_one("#export-result").focus()
            await pilot.press("enter")
            await asyncio.to_thread(app.jobs.wait_for_worker, 10)
            app.poll_jobs()
            assert app.jobs.state == "succeeded"
            app.action_export_result()  # overwrite is still disabled
            await asyncio.to_thread(app.jobs.wait_for_worker, 10)
            app.poll_jobs()
            assert app.jobs.state == "failed"
            from textual.widgets import Checkbox

            app.query_one("#overwrite", Checkbox).value = True
            app.action_export_result()  # retry uses the completed numeric result
            await asyncio.to_thread(app.jobs.wait_for_worker, 10)
            app.poll_jobs()
            assert app.jobs.state == "succeeded"
            assert json.loads(
                (tmp_path / "export" / "export_manifest.json").read_text()
            )["complete"]
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_committed_export_guard_does_not_report_cancellation():
    from threading import Event

    from finance_toolkit.tui.jobs import Jobs

    started, release = Event(), Event()

    def work(snapshot):
        started.set()
        assert release.wait(5)
        return snapshot

    jobs = Jobs(work)
    try:
        jobs.start(Workspace(), cancel_guard=lambda: False)
        assert started.wait(5)
        jobs.cancel()
        assert jobs.state == "running"
        release.set()
        jobs.wait_for_worker(5)
        jobs.poll()
        assert jobs.state == "succeeded"
    finally:
        release.set()
        jobs.close()


def test_risk_lab_writer_accepts_selected_snapshot_grid_and_undefined_returns(tmp_path):
    from finance_toolkit.risk_lab import RiskLab, write_risk_lab
    from finance_toolkit.tui.risk_service import run_risk

    result = run_risk(
        decode_workspace(
            {"simulation": {"paths": 1, "steps": 2}, "portfolio": {"initial_cash": 0}}
        )
    )
    report = RiskLab(
        {},
        result.base.market,
        {},
        {"portfolio": result.base.portfolio},
        {},
        {"portfolio": result.snapshot},
        {},
        {"portfolio": result.scenarios},
    )
    write_risk_lab(
        report,
        tmp_path,
        grid_snapshot=result.snapshot,
        spot_shocks=[0],
        volatility_shocks=[0],
    )
    rows = list(csv.DictReader((tmp_path / "wealth.csv").open()))
    assert all(row["return"] == "" for row in rows)
    assert len(list(csv.DictReader((tmp_path / "stress_grid.csv").open()))) == 1


def test_edit_during_export_requests_cancellation():
    from threading import Event

    from finance_toolkit.tui.jobs import Jobs

    started, release = Event(), Event()
    cancellations = []

    def work(snapshot):
        started.set()
        assert release.wait(5)
        return snapshot

    jobs = Jobs(work)
    try:
        jobs.start(Workspace(), cancel_guard=lambda: cancellations.append(True) or True)
        assert started.wait(5)
        jobs.changed()
        assert cancellations == [True]
        assert jobs.state == "cancelled"
    finally:
        release.set()
        jobs.close()


def test_optional_workspace_plot(tmp_path):
    pytest.importorskip("matplotlib")
    from finance_toolkit.tui.workspace import export_result

    result = run_portfolio(decode_workspace({"simulation": {"paths": 1, "steps": 2}}))
    export_result(result, tmp_path / "out", plot=True)
    assert (tmp_path / "out" / "wealth.png").read_bytes().startswith(b"\x89PNG")
