"""Independent stress/DV01 references and headless snapshot selection."""

import asyncio

import numpy as np
import pytest


def test_stock_stress_zero_shock_and_snapshot_cash_are_independent():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.risk_service import run_risk

    config = decode_workspace(
        {
            "simulation": {"paths": 1},
            "risk": {
                "confidence": 0.9,
                "scenarios": [
                    {"name": "down20", "spot_shocks": -0.2},
                    {"name": "zero"},
                ],
            },
        }
    )
    result = run_risk(config)
    assert result.snapshot.cash == 10000
    assert result.scenarios[0].total_pnl == pytest.approx(-2000, rel=0, abs=1e-10)
    assert result.scenarios[0].stressed_value == pytest.approx(18000, rel=0, abs=1e-10)
    assert result.scenarios[1].total_pnl == 0
    np.testing.assert_array_equal(result.exposures.asset_delta, [100])
    assert result.base.analysis.risk.confidence == 0.9


def test_zero_coupon_dv01_and_expired_positions():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.risk_service import run_risk

    payload = {
        "simulation": {"paths": 1},
        "portfolio": {"trades": [{"instrument": {"kind": "bond", "coupon_rate": 0}}]},
    }
    result = run_risk(decode_workspace(payload))
    assert result.exposures.position_dv01[0] == pytest.approx(
        1000 * np.exp(-0.03) * 1e-4, rel=1e-12, abs=1e-12
    )
    assert result.exposures.bond_convexity[0] == pytest.approx(1, rel=0, abs=1e-12)
    payload["risk"] = {"time_index": 12}
    expired = run_risk(decode_workspace(payload))
    np.testing.assert_array_equal(expired.exposures.position_dv01, 0)
    np.testing.assert_array_equal(expired.grid, 0)


def test_nonsmooth_greek_preserves_price_cash_and_valid_stress():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.risk_service import run_risk

    result = run_risk(
        decode_workspace(
            {
                "simulation": {"paths": 1},
                "portfolio": {
                    "rate": 0,
                    "trades": [{"instrument": {"kind": "call", "volatility": 0}}],
                },
                "risk": {"grid_volatility_shocks": [0]},
            }
        )
    )
    assert result.exposures is None
    assert result.exposure_error
    assert result.snapshot.cash == 20000
    assert result.base.analysis.wealth[0, 0] == 20000
    assert result.grid.shape == (1, 3)


@pytest.mark.parametrize("shock", [-1.1, float("nan")])
def test_invalid_spot_shocks_are_never_clipped(shock):
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.risk_service import run_risk

    with pytest.raises(ValueError):
        run_risk(decode_workspace({"risk": {"scenarios": [{"spot_shocks": shock}]}}))


def test_counterpositions_cancel_and_negative_volatility_is_rejected():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.risk_service import run_risk

    neutral = run_risk(
        decode_workspace({"portfolio": {"trades": [{"quantity": 1}, {"quantity": -1}]}})
    )
    np.testing.assert_array_equal(neutral.exposures.asset_delta, 0)
    np.testing.assert_array_equal(neutral.grid, 0)
    with pytest.raises(ValueError, match="volatility"):
        run_risk(
            decode_workspace(
                {
                    "portfolio": {"trades": [{"instrument": {"kind": "call"}}]},
                    "risk": {"scenarios": [{"volatility_shocks": -0.3}]},
                }
            )
        )


def test_headless_risk_form_snapshot_and_terminal_grid():
    pytest.importorskip("textual")
    from textual.widgets import Input

    from finance_toolkit.tui.app import create_app

    async def scenario():
        app = create_app()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("ctrl+3")
            app.query_one("#risk-confidence", Input).value = "90"
            app.query_one("#risk-time_index", Input).value = "1"
            await pilot.pause()
            await pilot.press("ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 5)
            app.poll_jobs()
            assert app.jobs.exportable
            assert app.jobs.result.base.analysis.risk.confidence == 0.9
            assert app.jobs.result.snapshot.time == pytest.approx(1 / 12)
            assert app.query_one("#stress-grid").row_count == 2
            assert "hypothetisch" in str(app.query_one("#risk-summary").render())
            app.query_one("#add-scenario").focus()
            await pilot.press("enter")
            app.screen.query_one("#scenario-name", Input).value = "Down"
            app.screen.query_one("#scenario-spot_shocks", Input).value = "-20"
            app.screen.query_one("#save-scenario").focus()
            await pilot.press("enter")
            assert app.workspace.risk.scenarios[0].name == "Down"
            assert app.workspace.risk.scenarios[0].spot_shocks == -0.2
            assert app.jobs.stale
            app.query_one("#delete-scenario").focus()
            await pilot.press("enter")
            assert not app.workspace.risk.scenarios
            await pilot.press("ctrl+q")

    asyncio.run(scenario())
