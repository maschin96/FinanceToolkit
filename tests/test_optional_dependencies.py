"""Core imports and offline CLIs must work even when extras are unavailable."""

import json
import subprocess
import sys
import textwrap

import pytest

IMPORT_GUARD = textwrap.dedent("""
    import importlib.abc
    import sys

    class NoOptionalImports(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            optional = {'matplotlib', 'pandas', 'yfinance', 'textual'}
            if fullname.split('.')[0] in optional:
                raise AssertionError(f'Unexpected optional dependency: {fullname}')

    sys.meta_path.insert(0, NoOptionalImports())
""")


def test_package_modules_import_without_optional_dependencies():
    # Even an all-extras environment must not conceal accidental eager imports.
    code = IMPORT_GUARD + textwrap.dedent("""
        import importlib
        import pkgutil
        import finance_toolkit

        modules = pkgutil.walk_packages(finance_toolkit.__path__, 'finance_toolkit.')
        for module in modules:
            importlib.import_module(module.name)
    """)
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "module,arguments,artifacts",
    [
        (
            "finance_toolkit.examples",
            ["--paths", "2"],
            ["summary.csv", "risk.json", "parameters.json"],
        ),
        (
            "finance_toolkit.risk_lab",
            ["--paths", "2", "--steps", "4"],
            ["summary.json", "wealth.csv", "stress.csv"],
        ),
        (
            "finance_toolkit.hedge_lab",
            ["--paths", "2", "--steps", "4"],
            ["comparison.json", "market.csv", "ledgers.csv"],
        ),
        ("finance_toolkit.index_lab", ["--demo"], ["index.json", "index.csv"]),
    ],
)
def test_offline_clis_do_not_import_optional_dependencies(
    tmp_path, module, arguments, artifacts
):
    output = tmp_path / "output"
    cli_args = [*arguments, "--output", str(output)]
    if module == "finance_toolkit.index_lab":
        # Self-contained synthetic input also works in wheel tests outside repo.
        config = tmp_path / "config.json"
        config.write_text(json.dumps(dict(tickers=["A"], base_date="2026-01-01")))
        cli_args.extend(["--config", str(config)])
    code = IMPORT_GUARD + textwrap.dedent("""
        import runpy

        module = sys.argv[1]
        sys.argv = sys.argv[1:]
        runpy.run_module(module, run_name='__main__')
    """)
    result = subprocess.run(
        [sys.executable, "-c", code, module, *cli_args],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for name in artifacts:
        assert (output / name).stat().st_size > 0
    assert not list(output.rglob("*.png"))
