"""CLI input errors are concise and deterministic; programmer errors remain visible."""

import json
import subprocess
import sys
import textwrap

import pytest


def _run_cli(module, arguments):
    # No invalid-input probe may accidentally contact the provider.
    code = textwrap.dedent("""
        import importlib
        import sys
        from finance_toolkit.yahoo import YFinanceProvider

        def forbidden(*args, **kwargs):
            raise AssertionError('unexpected provider access')

        YFinanceProvider.history = forbidden
        YFinanceProvider.quote = forbidden
        module = sys.argv[1]
        sys.argv = sys.argv[1:]
        raise SystemExit(importlib.import_module(module).main())
    """)
    return subprocess.run(
        [sys.executable, "-c", code, module, *arguments], capture_output=True, text=True
    )


@pytest.mark.parametrize(
    "module,arguments,message",
    [
        ("examples", ["--paths", "0"], "paths"),
        ("examples", ["--maturity", "0"], "maturity"),
        ("examples", ["--maturity", "0.3"], "maturity"),
        ("risk_lab", ["--paths", "0"], "paths"),
        ("risk_lab", ["--steps", "0"], "steps"),
        ("hedge_lab", ["--paths", "0"], "paths"),
        ("hedge_lab", ["--steps", "0"], "steps"),
        ("yahoo", ["quote", "A", "--timeout", "0"], "timeout"),
        ("yahoo", ["quote", "A", "--timeout", "-1"], "timeout"),
        ("yahoo", ["quote", "A", "--retries", "-1"], "retries"),
        ("yahoo", ["quote", "A", "--retries", "6"], "retries"),
    ],
)
def test_model_input_errors_have_exit_one_without_traceback(
    tmp_path, module, arguments, message
):
    output = tmp_path / "output"
    result = _run_cli(
        f"finance_toolkit.{module}", [*arguments, "--output", str(output)]
    )
    assert result.returncode == 1, result.stderr
    assert message in result.stderr.lower()
    assert "Traceback" not in result.stderr
    assert "unexpected provider access" not in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "module", ["examples", "risk_lab", "hedge_lab", "index_lab", "yahoo"]
)
def test_parser_errors_keep_exit_two(module):
    result = _run_cli(f"finance_toolkit.{module}", ["--unknown-option"])
    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "tickers", ["A", 1, None, {"A": 1}, [1], [None], [True], [""], ["  "]]
)
def test_index_config_rejects_symbol_types_before_provider_access(tmp_path, tickers):
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            dict(
                tickers=tickers,
                base_date="2026-01-01",
                start="2026-01-01",
                end="2026-01-07",
            )
        )
    )
    result = _run_cli("finance_toolkit.index_lab", ["--config", str(config)])
    assert result.returncode == 1
    assert "tickers" in result.stderr
    assert "Traceback" not in result.stderr
    assert "unexpected provider access" not in result.stderr


@pytest.mark.parametrize("payload", [None, [], 1, "A", {}])
def test_index_config_root_and_required_fields_are_concrete_errors(tmp_path, payload):
    config = tmp_path / "config.json"
    config.write_text(json.dumps(payload))
    result = _run_cli("finance_toolkit.index_lab", ["--config", str(config), "--demo"])
    assert result.returncode == 1
    assert "configuration" in result.stderr or "tickers" in result.stderr
    assert "Traceback" not in result.stderr


def test_invalid_json_and_missing_config_are_handled(tmp_path):
    config = tmp_path / "config.json"
    config.write_text("{bad json}")
    for path in (config, tmp_path / "missing.json"):
        result = _run_cli(
            "finance_toolkit.index_lab", ["--config", str(path), "--demo"]
        )
        assert result.returncode == 1
        assert result.stderr.strip()
        assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_date", 1),
        ("start", None),
        ("end", []),
        ("rebalance_dates", 1),
        ("rebalance_dates", [None]),
        ("repair", "yes"),
    ],
)
def test_index_config_field_types_fail_before_provider_access(tmp_path, field, value):
    config = dict(
        tickers=["A"], base_date="2026-01-01", start="2026-01-01", end="2026-01-07"
    )
    config[field] = value
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    result = _run_cli("finance_toolkit.index_lab", ["--config", str(path)])
    assert result.returncode == 1
    assert field in result.stderr
    assert "Traceback" not in result.stderr
    assert "unexpected provider access" not in result.stderr


@pytest.mark.parametrize("exception", [TypeError, KeyError])
def test_index_cli_does_not_hide_programming_errors(tmp_path, monkeypatch, exception):
    from finance_toolkit import index_lab

    config = tmp_path / "config.json"
    config.write_text(json.dumps(dict(tickers=["A"], base_date="2026-01-01")))
    monkeypatch.setattr(sys, "argv", ["index_lab", "--config", str(config), "--demo"])

    def broken(*args, **kwargs):
        raise exception("internal programming failure")

    monkeypatch.setattr(index_lab, "build_indices", broken)
    with pytest.raises(exception, match="internal programming failure"):
        index_lab.main()


@pytest.mark.parametrize(
    "module,arguments",
    [
        ("examples", ["--paths", "1"]),
        ("risk_lab", ["--paths", "1", "--steps", "4"]),
        ("hedge_lab", ["--paths", "1", "--steps", "4"]),
    ],
)
def test_output_filesystem_errors_are_concise(tmp_path, module, arguments):
    parent = tmp_path / "file"
    parent.write_text("not a directory")
    result = _run_cli(
        f"finance_toolkit.{module}", [*arguments, "--output", str(parent / "output")]
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
