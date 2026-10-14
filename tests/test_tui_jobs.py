"""Deterministic barriers prove single-flight, cancellation and revision safety."""

from dataclasses import replace
from threading import Event

import pytest

from finance_toolkit.tui.config import Workspace


def test_cancel_drops_late_result_and_retains_physical_single_flight():
    from finance_toolkit.tui.jobs import Jobs

    started, release = Event(), Event()

    def work(snapshot):
        started.set()
        assert release.wait(5)
        return snapshot.currency

    jobs = Jobs(work)
    try:
        assert jobs.state == "idle"
        first = jobs.start(Workspace())
        assert started.wait(5)
        assert jobs.state == "running"
        jobs.cancel()
        assert jobs.state == "cancelled"
        assert jobs.result is None
        with pytest.raises(ValueError, match="active"):
            jobs.start(Workspace())
        release.set()
        jobs.wait_for_worker(5)
        jobs.poll()
        assert jobs.result is None
        second = jobs.start(Workspace())
        assert second > first
        jobs.wait_for_worker(5)
        jobs.poll()
        assert jobs.state == "succeeded"
        assert jobs.result == "EUR"
    finally:
        release.set()
        jobs.close()


def test_changed_inputs_make_result_stale_and_snapshot_stays_owned():
    from finance_toolkit.tui.jobs import Jobs

    started, release = Event(), Event()

    def work(snapshot):
        started.set()
        assert release.wait(5)
        return snapshot

    jobs = Jobs(work)
    try:
        original = Workspace()
        jobs.start(original)
        assert started.wait(5)
        jobs.changed()
        release.set()
        jobs.wait_for_worker(5)
        jobs.poll()
        assert jobs.state == "succeeded"
        assert jobs.stale
        assert jobs.result == original
        assert jobs.result is not original
        assert not jobs.exportable
        jobs.start(replace(original, currency="USD"))
        jobs.wait_for_worker(5)
        jobs.poll()
        assert jobs.exportable
        assert jobs.result.currency == "USD"
        jobs.changed()
        assert not jobs.exportable
    finally:
        release.set()
        jobs.close()


@pytest.mark.parametrize("error", [ValueError("input invalid"), RuntimeError("defect")])
def test_failed_jobs_preserve_diagnostics_and_have_no_export(error):
    from finance_toolkit.tui.jobs import Jobs

    def work(snapshot):
        raise error

    jobs = Jobs(work)
    try:
        jobs.start(Workspace())
        jobs.wait_for_worker(5)
        jobs.poll()
        assert jobs.state == "failed"
        assert str(error) in jobs.error
        assert type(error).__name__ in jobs.diagnostic
        assert not jobs.exportable
    finally:
        jobs.close()


def test_close_prevents_restart():
    from finance_toolkit.tui.jobs import Jobs

    jobs = Jobs(lambda snapshot: snapshot)
    jobs.close()
    with pytest.raises(ValueError, match="closed"):
        jobs.start(Workspace())
