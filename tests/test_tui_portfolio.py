"""Editable offline portfolio, event-grid errors and independent cash references."""

import asyncio

import numpy as np
import pytest


def test_field_parsing_has_one_percent_boundary_and_strict_integers():
    from finance_toolkit.tui.forms import parse_field

    assert parse_field("3.5", float, percent=True) == 0.035
    assert parse_field("100, 200", tuple[float, ...]) == [100.0, 200.0]
    assert parse_field("1, .5; .5, 1", tuple[tuple[float, ...], ...]) == [
        [1.0, 0.5],
        [0.5, 1.0],
    ]
    assert parse_field("", float | None) is None
    for annotation, value in (
        (int, "1.5"),
        (float, "nan"),
        (tuple[float, ...], "1,inf"),
    ):
        with pytest.raises(ValueError):
            parse_field(value, annotation)


def test_keyboard_edit_run_select_and_trade_crud():
    pytest.importorskip("textual")
    from textual.widgets import Input

    from finance_toolkit.tui.app import create_app

    async def scenario():
        app = create_app()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("ctrl+2")
            app.query_one("#simulation-paths", Input).value = "2"
            app.query_one("#simulation-steps", Input).value = "4"
            app.query_one("#simulation-volatilities", Input).value = "0"
            app.query_one("#portfolio-initial_cash", Input).value = "1000"
            await pilot.pause()
            app.query_one("#edit-trade").focus()
            await pilot.press("enter")
            app.screen.query_one("#trade-quantity", Input).value = "2"
            app.screen.query_one("#trade-fee", Input).value = "3"
            app.screen.query_one("#save-trade").focus()
            await pilot.press("enter")
            assert app.workspace.portfolio.trades[0].quantity == 2
            await pilot.press("ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.exportable
            # sigma=0, mu=.06, no cash interest: EUR; roundoff at ~1000 EUR.
            np.testing.assert_allclose(
                app.jobs.result.portfolio.wealth[:, -1],
                797 + 200 * np.exp(0.06),
                rtol=1e-12,
                atol=1e-10,
            )
            app.query_one("#view-path", Input).value = "1"
            app.query_one("#view-time", Input).value = "4"
            await pilot.pause()
            assert app.jobs.exportable
            assert "EUR" in str(app.query_one("#portfolio-summary").render())
            app.query_one("#add-trade").focus()
            await pilot.press("enter")
            app.screen.query_one("#save-trade").focus()
            await pilot.press("enter")
            assert len(app.workspace.portfolio.trades) == 2
            app.query_one("#delete-trade").focus()
            await pilot.press("enter")
            assert len(app.workspace.portfolio.trades) == 1
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_invalid_form_edit_remains_blocking_until_corrected():
    pytest.importorskip("textual")
    from textual.widgets import Input

    from finance_toolkit.tui.app import create_app

    async def scenario():
        app = create_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("ctrl+2")
            spots = app.query_one("#simulation-spots", Input)
            spots.value = "invalid"
            await pilot.pause()
            app.query_one("#portfolio-rate", Input).value = "4"
            await pilot.pause()
            await pilot.press("ctrl+r")
            assert app.jobs.run_id == 0
            spots.value = "100.0"
            await pilot.pause()
            assert not app.input_error
            spots.value = "100,200"
            app.query_one("#simulation-drifts", Input).value = "6,4"
            app.query_one("#simulation-volatilities", Input).value = "20,10"
            await pilot.pause()
            assert not app.input_error
            assert app.workspace.simulation.spots == (100, 200)
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_position_quotes_parity_bond_cashflows_and_nonpositive_capital():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.services import position_rows, run_portfolio

    config = decode_workspace(
        {
            "simulation": {
                "paths": 1,
                "steps": 2,
                "drifts": [0.0],
                "volatilities": [0.0],
            },
            "portfolio": {
                "initial_cash": 0.0,
                "rate": 0.03,
                "trades": [
                    {"instrument": {"kind": "call"}},
                    {"instrument": {"kind": "put"}},
                    {
                        "instrument": {
                            "kind": "bond",
                            "frequency": 2,
                            "coupon_rate": 0.04,
                        }
                    },
                ],
            },
        }
    )
    result = run_portfolio(config)
    rows = position_rows(result, 0, 0)
    # Per-underlying quotes, EUR, BSM parity at S=K=100, T=1, q=0.
    assert rows[0]["quote"] - rows[1]["quote"] == pytest.approx(
        100 - 100 * np.exp(-0.03), rel=1e-12, abs=1e-10
    )
    assert result.analysis.returns is None
    np.testing.assert_array_equal(result.portfolio.coupon_cashflows, [[0, 20, 20]])
    np.testing.assert_array_equal(result.portfolio.principal_cashflows, [[0, 0, 1000]])
    mid = position_rows(result, 0, 1)[2]
    assert mid["dirty"] == pytest.approx(
        1020 * np.exp(-0.03 * 0.5), rel=1e-12, abs=1e-10
    )
    assert mid["clean"] == mid["dirty"]
    assert all(row["value"] == 0 for row in position_rows(result, 0, 2))
    with pytest.raises(ValueError, match="path"):
        position_rows(result, -1, 0)


@pytest.mark.parametrize("time", [0.1, 0.9])
def test_off_grid_trades_rejected_without_rounding(time):
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.services import run_portfolio

    config = decode_workspace(
        {
            "simulation": {"paths": 1, "steps": 2},
            "portfolio": {"trades": [{"time": time}]},
        }
    )
    with pytest.raises(ValueError, match="simulation time"):
        run_portfolio(config)


def test_multiple_assets_short_positions_and_multiplier_cash_settlement():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.services import run_portfolio

    config = decode_workspace(
        {
            "simulation": {
                "paths": 1,
                "steps": 2,
                "spots": [100, 200],
                "drifts": [0, 0],
                "volatilities": [0, 0],
                "correlation": [[1, 0.5], [0.5, 1]],
            },
            "portfolio": {
                "initial_cash": 1000,
                "rate": 0,
                "trades": [
                    {"quantity": -2, "instrument": {"kind": "stock", "asset": 1}},
                    {
                        "quantity": 2,
                        "instrument": {
                            "kind": "call",
                            "strike": 90,
                            "volatility": 0,
                            "multiplier": 10,
                        },
                    },
                ],
            },
        }
    )
    result = run_portfolio(config)
    np.testing.assert_allclose(
        result.portfolio.cash, [[1200, 1200, 1400]], rtol=0, atol=1e-10
    )
    np.testing.assert_allclose(
        result.portfolio.option_cashflows, [[0, 0, 200]], rtol=0, atol=1e-10
    )
    np.testing.assert_allclose(result.portfolio.wealth, 1000, rtol=0, atol=1e-10)


def test_numerical_export_boundary_retains_full_arrays_and_precision():
    import json

    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.services import portfolio_payload, run_portfolio

    result = run_portfolio(decode_workspace({"simulation": {"paths": 2, "steps": 64}}))
    payload = json.loads(json.dumps(portfolio_payload(result), allow_nan=False))
    np.testing.assert_array_equal(payload["market"]["prices"], result.market.prices)
    np.testing.assert_array_equal(payload["analysis"]["wealth"], result.analysis.wealth)
    assert len(payload["analysis"]["wealth"][0]) == 65
    assert payload["parameters"]["simulation"]["seed"] == 42
