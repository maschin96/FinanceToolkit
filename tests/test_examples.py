"""Offline examples satisfy payoff bounds and event cash conservation."""

import csv

import numpy as np

from finance_toolkit.examples import build_examples, main


def test_examples_are_reproducible_and_reconcile_cash() -> None:
    first = build_examples(seed=7, paths=80)
    second = build_examples(seed=7, paths=80)
    assert set(first) == {
        "stock",
        "protective_put",
        "covered_call",
        "bonds",
        "bonds_rising_rates",
        "bonds_falling_rates",
    }
    for name, result in first.items():
        np.testing.assert_array_equal(result.wealth, second[name].wealth)
        assert result.wealth.shape == (80, 25)
        flows = (
            result.trade_cashflows
            + result.fee_cashflows
            + result.coupon_cashflows
            + result.principal_cashflows
            + result.option_cashflows
            + result.financing_cashflows
        )
        np.testing.assert_allclose(
            result.cash, result.initial_cash + np.cumsum(flows, axis=1), atol=1e-9
        )
    put = first["protective_put"]
    call = first["covered_call"]
    # Same initial stock investment and premium at t=0, no subsequent trades/interest.
    assert np.all(put.wealth[:, -1] >= put.cash[:, 0] + 10_000 - 1e-9)
    assert np.all(call.wealth[:, -1] <= call.cash[:, 0] + 10_000 + 1e-9)
    assert np.all(
        first["bonds_rising_rates"].wealth[:, 12] < first["bonds"].wealth[:, 12]
    )
    assert np.all(
        first["bonds_falling_rates"].wealth[:, 12] > first["bonds"].wealth[:, 12]
    )
    np.testing.assert_allclose(
        first["bonds"].wealth[:, -1],
        first["bonds_rising_rates"].wealth[:, -1],
        atol=1e-9,
    )
    assert first["bonds"].coupon_cashflows[0].sum() == 800
    assert first["bonds"].principal_cashflows[0].sum() == 10_000


def test_coupon_maturity_and_rate_are_configurable() -> None:
    short = build_examples(paths=5, maturity=1, coupon_rate=0.02, rate=0.01)["bonds"]
    long = build_examples(paths=5, maturity=3, coupon_rate=0.06, rate=0.05)["bonds"]
    assert short.wealth.shape == (5, 13)
    assert long.wealth.shape == (5, 37)
    assert short.coupon_cashflows[0].sum() == 200
    assert long.coupon_cashflows[0].sum() == 1800


def test_cli_exports_offline_summary_and_risk(tmp_path) -> None:
    assert main(["--paths", "20", "--output", str(tmp_path)]) == 0
    with (tmp_path / "summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6 * 25
    assert {row["scenario"] for row in rows} == set(build_examples(paths=1))
    assert (tmp_path / "risk.json").is_file()
    assert (tmp_path / "parameters.json").is_file()


def test_optional_plot_adapter_outputs_png(tmp_path) -> None:
    import pytest

    pytest.importorskip("matplotlib")
    assert main(["--paths", "10", "--output", str(tmp_path), "--plot"]) == 0
    assert (tmp_path / "wealth.png").read_bytes().startswith(b"\x89PNG")
    assert (tmp_path / "bond_rates.png").stat().st_size > 1000
