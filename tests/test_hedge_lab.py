import csv
import json
import subprocess
import sys

import numpy as np
import pytest

from finance_toolkit.attribution import attribute_book
from finance_toolkit.hedge_lab import ComparisonCase, compare_hedges, export_comparison
from finance_toolkit.simulation import GBMPaths


@pytest.mark.parametrize(
    "name", ["protective_put", "covered_call", "collar", "bull_call", "bear_put"]
)
def test_equal_hedge_and_strategy_names_have_lossless_deterministic_exports(
    tmp_path, name
):
    market = GBMPaths(
        np.array([0.0, 0.5, 1.0]),
        np.array([[100, 110, 120], [100, 90, 80]])[:, :, None],
    )
    result = compare_hedges(market, (ComparisonCase(name),), initial_cash=1000)
    export_comparison(result, tmp_path)
    summary = json.loads((tmp_path / "comparison.json").read_text())
    expected_exports = []
    for kind, books in [("hedge", result.books), ("strategy", result.strategies)]:
        for case_name, book in books.items():
            directory = tmp_path / kind / case_name
            data = json.loads((directory / "attribution.json").read_text())
            expected = attribute_book(book)
            expected_exports.append(
                dict(
                    kind=kind,
                    name=case_name,
                    json=f"{kind}/{case_name}/attribution.json",
                    csv=f"{kind}/{case_name}/attribution.csv",
                )
            )
            for field in (
                "market",
                "execution",
                "settlements",
                "fees",
                "borrow",
                "delta",
                "gamma",
                "vega",
                "theta",
                "rho",
                "residual",
                "events",
                "financing",
                "relative_pnl",
            ):
                # Serialization of already verified core results is lossless;
                # no new numerical approximation or tolerance is involved.
                np.testing.assert_array_equal(data[field], getattr(expected, field))
            np.testing.assert_array_equal(data["times"], expected.times)
            np.testing.assert_array_equal(data["pnl"], expected.reconciled)
            # Independent cash/value balance, currency scale around 1000:
            # summation roundoff uses the established attribution tolerance.
            np.testing.assert_allclose(
                data["pnl"], np.diff(book.wealth, axis=1), rtol=1e-12, atol=1e-10
            )
            with (directory / "attribution.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            assert len(rows) == np.prod(expected.market.shape)
            for row in rows:
                p = int(row["path"])
                t = list(expected.times).index(float(row["time"]))
                j = int(row["instrument"])
                assert row["events"] == str(expected.events[p, t, j])
                for field in (
                    "market",
                    "execution",
                    "settlements",
                    "fees",
                    "borrow",
                    "delta",
                    "gamma",
                    "vega",
                    "theta",
                    "rho",
                    "residual",
                ):
                    assert float(row[field]) == getattr(expected, field)[p, t, j]
                assert float(row["portfolio_financing"]) == expected.financing[p, t]
                assert float(row["portfolio_pnl"]) == expected.reconciled[p, t]
                assert float(row["relative_pnl"]) == expected.relative_pnl[p][t]
    assert summary["attributions"] == expected_exports
    assert not (tmp_path / name / "attribution.json").exists()
    before = {
        file.relative_to(tmp_path): file.read_bytes()
        for file in tmp_path.rglob("*")
        if file.is_file()
    }
    export_comparison(result, tmp_path)
    after = {
        file.relative_to(tmp_path): file.read_bytes()
        for file in tmp_path.rglob("*")
        if file.is_file()
    }
    assert before == after


def test_coupled_comparison_common_opening_and_hand_control(tmp_path):
    market = GBMPaths(np.array([0.0, 0.25, 0.5, 0.75, 1.0]), np.full((2, 5, 1), 100.0))
    cases = (ComparisonCase("none", 1), ComparisonCase("calendar", 2, calendar_every=1))
    result = compare_hedges(market, cases, initial_cash=1000)
    control = result.books["none"]
    np.testing.assert_equal(result.books["calendar"].spots, market.prices[:, ::2])
    assert (
        control.trade_cashflows[0, 0, 1]
        == result.books["calendar"].trade_cashflows[0, 0, 1]
    )
    assert control.wealth[0, 0] == 1000
    assert result.metrics[0]["mean_pnl"] == pytest.approx(control.cash[0, -1] - 1000)
    assert result.metrics[0]["mean_fees"] == 0
    export_comparison(result, tmp_path)
    data = json.loads((tmp_path / "comparison.json").read_text())
    assert data["config"]["path_hash"] == result.config["path_hash"]
    assert (tmp_path / "comparison.csv").is_file()
    assert (tmp_path / "wealth.csv").is_file()
    assert (tmp_path / "strategies.csv").is_file()
    assert (tmp_path / "hedge" / "calendar" / "attribution.json").is_file()


def test_reproducible_offline_cli(tmp_path):
    outputs = []
    for name in ("a", "b"):
        path = tmp_path / name
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "finance_toolkit.hedge_lab",
                "--paths",
                "4",
                "--steps",
                "8",
                "--seed",
                "123",
                "--output",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, run.stderr
        outputs.append((path / "comparison.json").read_text())
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize(
    "case",
    [
        ComparisonCase("bad", 3),
        ComparisonCase("bad", 1, threshold=-1),
        ComparisonCase("bad", 1, fixed_fee=-1),
    ],
)
def test_invalid_cases(case):
    with pytest.raises(ValueError):
        compare_hedges(
            GBMPaths(np.linspace(0, 1, 5), np.full((1, 5, 1), 100.0)),
            (case,),
            initial_cash=1000,
        )


def test_optional_plot_uses_same_results(tmp_path):
    market = GBMPaths(np.linspace(0, 1, 5), np.full((1, 5, 1), 100.0))
    result = compare_hedges(market, (ComparisonCase("none"),), initial_cash=1000)
    export_comparison(result, tmp_path, plot=True)
    assert (tmp_path / "comparison.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert (tmp_path / "market.csv").is_file()
    assert (tmp_path / "ledgers.csv").is_file()
