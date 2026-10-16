"""Optional entry points and immutable, strict TUI configuration contracts."""

import dataclasses
import json
import subprocess
import sys

import numpy as np
import pytest


def test_workspace_roundtrip_and_owned_snapshot():
    from finance_toolkit.tui.config import Workspace, decode_workspace, encode_workspace

    original = Workspace()
    payload = encode_workspace(original)
    restored = decode_workspace(json.loads(json.dumps(payload)))
    assert restored == original
    payload["simulation"]["spots"][0] = 999
    assert original.simulation.spots == (100.0,)
    with pytest.raises(dataclasses.FrozenInstanceError):
        original.currency = "USD"


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"currency": 42},
        {"unknown": 1},
        {"simulation": {"paths": True}},
        {"simulation": {"spots": [float("nan")]}},
        {"simulation": {"spots": [100, 200], "drifts": [0.1]}},
        {"simulation": {"seed": -1}},
        {"simulation": {"correlation": [[0.5]]}},
        {"portfolio": {"trades": [{"instrument": {"kind": "future"}}]}},
        {"index": {"source": "automatic"}},
    ],
)
def test_reject_invalid_workspace(change):
    from finance_toolkit.tui.config import decode_workspace

    with pytest.raises(ValueError):
        decode_workspace(change)


def test_percentage_boundary():
    from finance_toolkit.tui.config import percent_to_decimal

    assert percent_to_decimal("3.5") == 0.035
    assert percent_to_decimal("-2") == -0.02
    for value in ("nan", "inf", "three"):
        with pytest.raises(ValueError, match="percent"):
            percent_to_decimal(value)


def test_portfolio_adapter_independent_cash_reference():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.services import run_portfolio

    config = decode_workspace(
        {
            "simulation": {"paths": 2, "steps": 4, "volatilities": [0.0]},
            "portfolio": {
                "initial_cash": 1000.0,
                "trades": [
                    {
                        "time": 0.0,
                        "quantity": 2.0,
                        "fee": 3.0,
                        "instrument": {"kind": "stock", "asset": 0},
                    }
                ],
            },
        }
    )
    result = run_portfolio(config)
    # Currency values: deterministic GBM, no financing; roundoff <1e-10 EUR.
    expected = 797.0 + 200.0 * np.exp(0.06)
    np.testing.assert_allclose(
        result.portfolio.wealth[:, -1], expected, rtol=0, atol=1e-10
    )
    np.testing.assert_array_equal(result.portfolio.cash, 797.0)
    again = run_portfolio(config)
    np.testing.assert_array_equal(result.market.prices, again.market.prices)


def test_missing_extra_entrypoint_without_traceback():
    code = """
import importlib.abc
import runpy
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'textual':
            raise ModuleNotFoundError("blocked", name="textual")
sys.meta_path.insert(0, Block())
runpy.run_module('finance_toolkit.tui', run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "finance-toolkit[tui]" in result.stderr
    assert "Traceback" not in result.stderr


def test_entrypoint_help():
    from importlib.util import find_spec

    result = subprocess.run(
        [sys.executable, "-m", "finance_toolkit.tui", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "FinanceToolkit" in result.stdout
    assert find_spec("finance_toolkit.tui") is not None


@pytest.mark.parametrize("entry", ["module", "console"])
def test_entrypoint_terminal_start_and_keyboard_quit(tmp_path, entry):
    """Real POSIX terminal driver; automated smoke, not manual acceptance."""
    import fcntl
    import os
    import pty
    import select
    import struct
    import termios
    from importlib.util import find_spec
    from pathlib import Path
    from time import monotonic

    command = (
        [sys.executable, "-m", "finance_toolkit.tui"]
        if entry == "module"
        else [str(Path(sys.executable).parent / "finance-toolkit-tui")]
    )
    if find_spec("textual") is None:
        completed = subprocess.run(
            command, capture_output=True, text=True, cwd=tmp_path
        )
        assert completed.returncode == 2
        assert "finance-toolkit[tui]" in completed.stderr
        assert "Traceback" not in completed.stderr
        return
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    process = subprocess.Popen(
        command,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=tmp_path,
        env={**os.environ, "TERM": "xterm-256color"},
        start_new_session=True,
    )
    os.close(slave)
    transcript = bytearray()
    try:
        deadline = monotonic() + 15
        while b"Offline-Demo" not in transcript and monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                try:
                    transcript.extend(os.read(master, 65536))
                except OSError:
                    break
        assert b"Offline-Demo" in transcript, transcript.decode(errors="replace")
        # These are real legacy xterm F-key bytes, not synthetic Pilot events.
        for sequence, marker in (
            (b"\x1bOS", b"GBM:"),  # F4: portfolio
            (b"\x1b[15~", b"expliziter Snapshot"),  # F5: risk
            (b"\x1b[17~", b"Openingannahmen"),  # F6: strategies
            (b"\x1b[18~", b"Sitzungen"),  # F7: indices
            (b"\x1b[19~", b"Konfigurationsdatei"),  # F8: workspace
            (b"\x1bOR", b"Offline-Demo"),  # F3: start
        ):
            os.write(master, sequence)
            screen_output = bytearray()
            deadline = monotonic() + 10
            while marker not in screen_output and monotonic() < deadline:
                readable, _, _ = select.select([master], [], [], 0.1)
                if readable:
                    try:
                        screen_output.extend(os.read(master, 65536))
                    except OSError:
                        break
            transcript.extend(screen_output)
            assert marker in screen_output, screen_output.decode(errors="replace")
        os.write(master, b"\x11")  # Ctrl+Q through the real terminal input driver
        deadline = monotonic() + 10
        # Keep consuming output: waiting without reading can fill the PTY buffer
        # and block Textual while it restores the terminal on shutdown.
        while process.poll() is None and monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                try:
                    transcript.extend(os.read(master, 65536))
                except OSError:
                    break
        assert process.wait(timeout=1) == 0
        assert b"Traceback" not in transcript
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        os.close(master)
