"""Bounded background jobs; all state transitions happen on the UI thread."""

import traceback
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Generic, Literal, TypeVar

from finance_toolkit.tui.config import Workspace, decode_workspace, encode_workspace

T = TypeVar("T")
JobState = Literal["idle", "running", "succeeded", "failed", "cancelled"]


class Jobs(Generic[T]):
    """One physical worker, no queue; cancellation suppresses later publication.

    Call start/changed/cancel/poll/close from the owning UI thread. The worker
    receives an owned immutable snapshot and never touches this object or UI.
    A cancelled core call may keep running; another run remains blocked until
    it finishes. close does not forcibly terminate or wait for that thread.
    """

    def __init__(self, work: Callable[[Workspace], T]) -> None:
        self.work = work
        self.state: JobState = "idle"
        self.run_id = 0
        self.revision = 0
        self.run_revision = 0
        self.result: T | None = None
        self.error = ""
        self.diagnostic = ""
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="finance-tui"
        )
        self._future: Future[T] | None = None
        self._closed = False
        self._cancel_guard: Callable[[], bool] | None = None

    @property
    def busy(self) -> bool:
        """True until the physical worker completes, including after cancellation."""
        return self._future is not None and not self._future.done()

    @property
    def stale(self) -> bool:
        """A completed result predates an edit, even if the edit was invalid."""
        return self.result is not None and self.revision != self.run_revision

    @property
    def exportable(self) -> bool:
        """Only a successful result for the current input revision can be exported."""
        return self.state == "succeeded" and self.result is not None and not self.stale

    def changed(self) -> None:
        """Invalidate published/running results as soon as a field changes."""
        self.revision += 1
        if self._cancel_guard is not None:
            self.cancel()

    def start(
        self, workspace: Workspace, *, cancel_guard: Callable[[], bool] | None = None
    ) -> int:
        """Start one owned input snapshot or reject closed/busy state."""
        if self._closed:
            raise ValueError("workspace is closed")
        if self.busy:
            raise ValueError(
                "one active calculation per workspace; wait for completion"
            )
        self.poll()
        snapshot = decode_workspace(encode_workspace(workspace))
        self.run_id += 1
        self._cancel_guard = cancel_guard
        self.run_revision = self.revision
        self.state = "running"
        self.result = None
        self.error = self.diagnostic = ""
        self._future = self._executor.submit(self.work, snapshot)
        return self.run_id

    def cancel(self) -> None:
        """Discard this run's result; interrupt only a not-yet-started future."""
        if self.state == "running":
            if self._cancel_guard is not None and not self._cancel_guard():
                self.poll()
                return
            self.state = "cancelled"
            self.result = None
            if self._future is not None:
                self._future.cancel()

    def poll(self) -> None:
        """Publish a completed worker only if this run has not been cancelled."""
        future = self._future
        if future is None or not future.done():
            return
        self._future = None
        if self.state != "running" or self._closed:
            return
        try:
            self.result = future.result()
        except Exception as error:
            self.state = "failed"
            self.error = f"{type(error).__name__}: {error}"
            self.diagnostic = "".join(traceback.format_exception(error))
            self.result = None
        else:
            self.state = "succeeded"

    def wait_for_worker(self, timeout: float) -> None:
        """Controlled synchronization for tests; never used to block the UI."""
        future = self._future
        if future is not None:
            # wait() observes completion without consuming/suppressing failures.
            from concurrent.futures import wait

            done, _ = wait([future], timeout=timeout)
            if not done:
                raise TimeoutError("worker did not complete")

    def close(self) -> None:
        """Cancel publication and stop accepting jobs without blocking navigation."""
        self.cancel()
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
