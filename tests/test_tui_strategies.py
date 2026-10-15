"""Same-market strategies, delayed orders and exact attribution balances."""

import asyncio

import numpy as np
import pytest


def test_scheduled_order_execution_costs_and_attribution_balance():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.strategy_service import run_strategies

    result = run_strategies(
        decode_workspace(
            {
                "simulation": {
                    "paths": 1,
                    "steps": 2,
                    "spots": [100],
                    "drifts": [0],
                    "volatilities": [0],
                },
                "portfolio": {"initial_cash": 1000, "rate": 0},
                "strategy": {
                    "multiplier": 1,
                    "orders": [{"time": 0.5, "quantity": 2, "fee": 3}],
                },
            }
        )
    )
    book = result.books["dynamic/scheduled"]
    np.testing.assert_array_equal(book.trades[0, :, 0], [0, 2, 0])
    # GBM log/exp roundoff at ~1000 EUR; established currency tolerance 1e-10.
    np.testing.assert_allclose(book.cash[0], [1000, 797, 797], rtol=0, atol=1e-10)
    np.testing.assert_allclose(book.wealth[0], [1000, 997, 997], rtol=0, atol=1e-10)
    attr = result.attributions["dynamic/scheduled"]
    np.testing.assert_allclose(attr.reconciled, [[-3, 0]], rtol=0, atol=1e-10)
    for name, item in result.books.items():
        np.testing.assert_allclose(
            result.attributions[name].reconciled,
            np.diff(item.wealth, axis=1),
            rtol=1e-12,
            atol=1e-10,
        )
    assert result.comparison is None


def test_hedge_strides_share_exact_paths_and_names_are_categorized():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.strategy_service import run_strategies

    result = run_strategies(
        decode_workspace(
            {
                "simulation": {"paths": 2, "steps": 4},
                "hedge": {
                    "enabled": True,
                    "allow_short": True,
                    "allow_borrowing": True,
                    "case_names": ["protective_put", "coarse"],
                    "calendar_every": 1,
                },
            }
        )
    )
    assert "hedge/protective_put" in result.books
    assert "strategy/protective_put" in result.books
    np.testing.assert_array_equal(
        result.books["hedge/coarse"].spots, result.market.prices[:, ::2]
    )
    assert result.hedges["hedge/coarse"].residual_delta.shape == (2, 3, 1)
    assert (
        result.books["hedge/coarse"].initial_cash
        == result.config.portfolio.initial_cash
    )


def test_actual_residual_delta_respects_delayed_execution():
    from scipy.special import ndtr

    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.strategy_service import run_strategies

    result = run_strategies(
        decode_workspace(
            {
                "simulation": {
                    "paths": 1,
                    "steps": 4,
                    "drifts": [0],
                    "volatilities": [0],
                },
                "portfolio": {"rate": 0},
                "hedge": {
                    "enabled": True,
                    "allow_short": True,
                    "allow_borrowing": True,
                    "calendar_every": 1,
                },
            }
        )
    )
    # S=K=100, r=q=0, model sigma=.2; BSM delta=Phi(sigma*sqrt(tau)/2).
    # At t=.5 the stock hedge still executes the t=0 target, so it is not zero.
    expected = ndtr(0.1) - ndtr(0.2 * np.sqrt(0.5) / 2)
    actual = result.hedges["hedge/coarse"].residual_delta[0, :, 0]
    assert actual[1] == pytest.approx(expected, rel=0, abs=1e-12)
    assert actual[-1] == 0


def test_explicit_financing_and_short_loan_parameters_are_forwarded():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.strategy_service import run_strategies

    config = {
        "simulation": {"paths": 1, "steps": 2, "drifts": [0], "volatilities": [0]},
        "portfolio": {
            "initial_cash": 1000,
            "rate": 0,
            "lending_rate": 0.03,
            "borrowing_rate": 0.07,
        },
        "strategy": {
            "multiplier": 1,
            "allow_short": True,
            "allow_borrowing": True,
            "stock_borrow_rate": 0.02,
            "orders": [{"quantity": -1}],
        },
    }
    result = run_strategies(decode_workspace(config))
    book = result.books["dynamic/scheduled"]
    expected_cash = (1100 * np.exp(0.015) - 1) * np.exp(0.015) - 1
    assert book.cash[0, -1] == pytest.approx(expected_cash, rel=0, abs=1e-10)
    np.testing.assert_allclose(book.stock_borrow_costs[0, 1:, 0], 1, rtol=0, atol=1e-10)
    config["strategy"]["orders"] = [{"quantity": 20}]
    borrowed = run_strategies(decode_workspace(config)).books["dynamic/scheduled"]
    assert borrowed.cash[0, -1] == pytest.approx(-1000 * np.exp(0.07), rel=0, abs=1e-10)


@pytest.mark.parametrize(
    "change",
    [
        {"hedge": {"enabled": True}},
        {
            "hedge": {
                "enabled": True,
                "allow_short": True,
                "allow_borrowing": True,
                "option_quantity": 0,
            }
        },
        {
            "hedge": {
                "enabled": True,
                "allow_short": True,
                "allow_borrowing": True,
                "strides": [1, 5],
            }
        },
        {"strategy": {"weights": [1.1]}},
        {"strategy": {"calendar": [0], "threshold": 0.1}},
        {"strategy": {"orders": [{"time": 0.13}]}},
    ],
)
def test_preconditions_rejected_before_market_generation(change, monkeypatch):
    import finance_toolkit.tui.strategy_service as service
    from finance_toolkit.tui.config import decode_workspace

    def forbidden(*args, **kwargs):
        raise AssertionError("market must not be generated")

    monkeypatch.setattr(service, "simulate_market", forbidden)
    with pytest.raises(ValueError):
        service.run_strategies(decode_workspace(change))


def test_headless_strategy_and_hedge_controls():
    pytest.importorskip("textual")
    from textual.widgets import Input

    from finance_toolkit.tui.app import create_app

    async def scenario():
        app = create_app()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("ctrl+4")
            app.query_one("#add-order").focus()
            await pilot.press("enter")
            app.screen.query_one("#trade-time", Input).value = "0.5"
            app.screen.query_one("#save-trade").focus()
            await pilot.press("enter")
            assert app.workspace.strategy.orders[0].time == 0.5
            app.query_one("#strategy-multiplier", Input).value = "1"
            app.query_one("#hedge-enabled", Input).value = "ja"
            app.query_one("#hedge-allow_short", Input).value = "ja"
            app.query_one("#hedge-allow_borrowing", Input).value = "ja"
            await pilot.pause()
            await pilot.press("ctrl+r")
            await asyncio.to_thread(app.jobs.wait_for_worker, 10)
            app.poll_jobs()
            assert app.jobs.exportable
            assert app.jobs.result.comparison is not None
            assert app.query_one("#strategy-books").row_count >= 7
            assert "Opening" in str(app.query_one("#strategy-summary").render())
            app.query_one("#strategy-books").move_cursor(row=len(app.jobs.result.books))
            await pilot.pause()
            assert app.query_one("#book-ledger").row_count == 13
            app.query_one("#delete-order").focus()
            await pilot.press("enter")
            assert not app.workspace.strategy.orders
            assert app.jobs.stale
            app.query_one("#add-case").focus()
            await pilot.press("enter")
            app.screen.query_one("#case-name", Input).value = "unhedged"
            app.screen.query_one("#save-case").focus()
            await pilot.press("enter")
            assert app.workspace.hedge.cases[0].name == "unhedged"
            app.query_one("#delete-case").focus()
            await pilot.press("enter")
            assert not app.workspace.hedge.cases
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_independent_hedge_rules_and_costs_per_case():
    from finance_toolkit.tui.config import decode_workspace
    from finance_toolkit.tui.strategy_service import run_strategies

    result = run_strategies(
        decode_workspace(
            {
                "simulation": {"paths": 1, "steps": 4},
                "hedge": {
                    "enabled": True,
                    "allow_short": True,
                    "allow_borrowing": True,
                    "cases": [
                        {"name": "unhedged"},
                        {"name": "calendar", "calendar_every": 1, "fixed_fee": 0.5},
                        {"name": "threshold", "threshold": 0.1},
                    ],
                },
            }
        )
    )
    assert set(result.hedges) == {"hedge/unhedged", "hedge/calendar", "hedge/threshold"}
    assert result.books["hedge/calendar"].fees.sum() > 0
    np.testing.assert_array_equal(result.books["hedge/unhedged"].trades[:, :, 0], 0)
