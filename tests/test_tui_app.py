"""Keyboard and background responsiveness tested through Textual Pilot."""

import asyncio
from threading import Event

import pytest


@pytest.mark.parametrize("size", [(80, 24), (120, 40)])
def test_keyboard_navigation_help_and_resize(size):
    pytest.importorskip("textual")
    from finance_toolkit.tui.app import create_app

    async def scenario():
        app = create_app()
        async with app.run_test(size=size) as pilot:
            assert app.focused is not None
            for number, page in enumerate(
                ("start", "portfolio", "risk", "strategy", "index", "workspace"), 1
            ):
                await pilot.press(f"ctrl+{number}")
                assert app.query_one("#pages").current == page
                await pilot.press("tab", "shift+tab")
                assert app.focused is not None
            await pilot.press("f1")
            assert app.screen.id == "help"
            await pilot.resize_terminal(60, 16)
            await pilot.pause()
            await pilot.press("escape")
            assert app.screen.id != "help"
            await pilot.resize_terminal(120, 40)
            assert not app.query_one("#size-warning").display
            await pilot.resize_terminal(60, 16)
            assert app.query_one("#size-warning").display
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_ui_quit_during_active_worker():
    pytest.importorskip("textual")
    from finance_toolkit.tui.app import create_app

    started, release = Event(), Event()

    def work(snapshot):
        started.set()
        assert release.wait(5)
        return snapshot

    async def scenario():
        app = create_app(work=work)
        try:
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("ctrl+r")
                assert await asyncio.to_thread(started.wait, 5)
                await pilot.press("ctrl+q")
                assert app.jobs.state == "cancelled"
                assert app.jobs.busy
            assert not release.is_set()
        finally:
            release.set()
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.jobs.close()
        assert app.jobs.result is None

    asyncio.run(scenario())


def test_ui_remains_responsive_and_cancelled_result_is_not_published():
    pytest.importorskip("textual")
    from finance_toolkit.tui.app import create_app

    started, release = Event(), Event()

    def work(snapshot):
        started.set()
        assert release.wait(5)
        return "late"

    async def scenario():
        app = create_app(work=work)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("ctrl+r")
            assert await asyncio.to_thread(started.wait, 5)
            assert app.jobs.state == "running"
            await pilot.press("ctrl+3")
            assert app.query_one("#pages").current == "risk"
            await pilot.press("escape")
            assert app.jobs.state == "cancelled"
            release.set()
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.result is None
            assert not app.jobs.exportable
            await pilot.press("ctrl+q")

    try:
        asyncio.run(scenario())
    finally:
        release.set()


def test_ui_invalid_edit_stale_results_and_failure_diagnostics():
    pytest.importorskip("textual")
    from textual.widgets import Input, Static

    from finance_toolkit.tui.app import create_app

    def work(snapshot):
        if snapshot.simulation.seed == 13:
            raise RuntimeError("controlled defect")
        return snapshot

    async def scenario():
        app = create_app(work=work)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.exportable
            field = app.query_one("#seed", Input)
            field.value = "invalid"
            await pilot.pause()
            assert app.jobs.stale
            old_run = app.jobs.run_id
            await pilot.press("ctrl+r")
            assert app.jobs.run_id == old_run
            assert "Seed" in str(app.query_one("#status", Static).render())
            field.value = "13"
            await pilot.pause()
            await pilot.press("ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.state == "failed"
            await pilot.press("f2")
            assert "RuntimeError: controlled defect" in str(
                app.screen.query_one("#diagnostic", Static).render()
            )
            await pilot.press("escape", "ctrl+q")

    asyncio.run(scenario())


@pytest.mark.parametrize("size", [(80, 24), (120, 40)])
def test_navigation_without_control_digits(size):
    pytest.importorskip("textual")
    from textual.widgets import Input, Tabs

    from finance_toolkit.tui.app import create_app

    calls = []

    def forbidden(snapshot):
        calls.append(snapshot)
        raise AssertionError("navigation must not calculate")

    async def scenario():
        app = create_app(work=forbidden)
        async with app.run_test(size=size) as pilot:
            navigation = app.query_one("#navigation", Tabs)
            assert navigation.display
            navigation.focus()
            for page in (
                "portfolio",
                "risk",
                "strategy",
                "index",
                "workspace",
                "start",
            ):
                await pilot.press("right")
                assert app.query_one("#pages").current == page
                assert navigation.active == f"nav-{page}"
                assert app.focused is navigation
            await pilot.press("left")
            assert app.query_one("#pages").current == "workspace"
            await pilot.press("tab")
            assert app.focused is not navigation
            await pilot.press("shift+tab")
            assert app.focused is navigation
            for number, page in enumerate(
                ("start", "portfolio", "risk", "strategy", "index", "workspace"), 3
            ):
                # Start with a focused field: function keys cannot edit text.
                current = app.query_one("#pages").current
                field = app.query_one(f"#{current}").query(Input).first()
                field.focus()
                original_value = field.value
                await pilot.press(f"f{number}")
                assert app.query_one("#pages").current == page
                assert navigation.active == f"nav-{page}"
                assert field.value == original_value
                assert app.query_one("#seed", Input).value == "42"
            await pilot.press("f1")
            assert "F3" in str(app.screen.query_one("Static").render())
            await pilot.press("escape", "ctrl+q")
            assert not calls
            assert app.jobs.run_id == 0

    asyncio.run(scenario())
