"""Reproducibility and exported values are checked against public model APIs."""

import csv
import json

import numpy as np
import pytest

from finance_toolkit import __version__
from finance_toolkit.analytics import tail_risk
from finance_toolkit.risk import StressScenario, portfolio_exposures, stress_portfolio
from finance_toolkit.risk_lab import build_risk_lab, main, write_risk_lab


def test_common_seeded_paths_and_capital():
    a = build_risk_lab(seed=7, paths=10, steps=4)
    b = build_risk_lab(seed=7, paths=10, steps=4)
    assert set(a.strategies) == {"buy_and_hold", "calendar", "threshold"}
    for name, r in a.strategies.items():
        np.testing.assert_array_equal(r.prices, a.market.prices)
        np.testing.assert_array_equal(r.wealth, b.strategies[name].wealth)
        np.testing.assert_array_equal(
            r.fees[:, 0], a.strategies["buy_and_hold"].fees[:, 0]
        )
        risk = tail_risk(r.initial_cash - r.wealth[:, -1])
        assert a.metrics[name]["value_at_risk"] == risk.value_at_risk
        assert a.metrics[name]["expected_shortfall"] == risk.expected_shortfall
    assert set(a.option_portfolios) == {"stock", "protective_put"}
    assert a.configuration["seed"] == 7
    assert a.configuration["version"] == __version__
    snap = a.snapshots["protective_put"]
    assert a.exposures["protective_put"].rho == portfolio_exposures(snap).rho
    assert (
        a.stresses["protective_put"][1].total_pnl
        == stress_portfolio(snap, StressScenario("crash", -0.2, 0.1, 0.01)).total_pnl
    )


def test_exports_match_api_values(tmp_path):
    report = build_risk_lab(seed=5, paths=3, steps=4)
    write_risk_lab(report, tmp_path)
    data = json.loads((tmp_path / "summary.json").read_text())
    assert data["configuration"] == report.configuration
    assert data["metrics"] == report.metrics
    with (tmp_path / "wealth.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 5 * 3 * 5
    row = next(
        r
        for r in rows
        if r["portfolio"] == "calendar"
        and r["path"] == "0"
        and r["time_years"] == "1.0"
    )
    assert float(row["wealth"]) == report.strategies["calendar"].wealth[0, -1]
    assert float(row["pnl"]) == report.strategies["calendar"].wealth[0, -1] - 20000
    with (tmp_path / "stress.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    row = next(
        r
        for r in rows
        if r["portfolio"] == "protective_put"
        and r["scenario"] == "crash"
        and r["position"] == "total"
    )
    assert float(row["pnl"]) == report.stresses["protective_put"][1].total_pnl
    with (tmp_path / "exposures.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    row = next(
        r for r in rows if r["portfolio"] == "protective_put" and r["position"] == "1"
    )
    assert float(row["delta"]) == report.exposures["protective_put"].position_delta[1]
    assert (tmp_path / "strategy_ledger.csv").is_file()
    assert (tmp_path / "asset_exposures.csv").is_file()
    with (tmp_path / "stress_grid.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) == 15


def test_cli_numeric_exports_do_not_import_plots(tmp_path, monkeypatch):
    import builtins

    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("matplotlib"):
            raise AssertionError("optional plot import")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert main(["--paths", "3", "--steps", "4", "--output", str(tmp_path)]) == 0
    assert (tmp_path / "summary.json").is_file()
    assert not (tmp_path / "strategies.png").exists()


def test_optional_charts(tmp_path):
    pytest.importorskip("matplotlib")
    assert (
        main(["--paths", "3", "--steps", "4", "--output", str(tmp_path), "--plot"]) == 0
    )
    for name in ["strategies.png", "protective_put.png", "stress.png"]:
        assert (tmp_path / name).read_bytes().startswith(b"\x89PNG")


def test_cash_financing_exported_once_per_portfolio_time(tmp_path):
    report = build_risk_lab(paths=1, steps=4)
    write_risk_lab(report, tmp_path)
    with (tmp_path / "wealth.csv").open() as stream:
        row = next(
            r
            for r in csv.DictReader(stream)
            if r["portfolio"] == "calendar" and r["time_years"] == "1.0"
        )
    assert float(row["financing"]) == report.strategies["calendar"].financing[0, -1]
