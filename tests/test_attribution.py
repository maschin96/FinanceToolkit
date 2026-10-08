import json

import numpy as np
import pytest

from finance_toolkit.attribution import (
    attribute_book,
    explain_option_move,
    export_attribution,
)
from finance_toolkit.options_book import Order, simulate_book
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.simulation import GBMPaths


def test_stock_cash_trades_fees_exact_reconciliation(tmp_path):
    market = GBMPaths(
        np.array([0.0, 0.5, 1.0]), np.array([100.0, 110.0, 120.0])[None, :, None]
    )
    book = simulate_book(
        market,
        (Stock(),),
        initial_cash=1000,
        initial_orders=(Order(0, 2, fee=1),),
        lending_rate=0.1,
        signal=lambda s: (Order(0, -1, price=112, fee=2),) if s.time == 0 else None,
    )
    result = attribute_book(book)
    np.testing.assert_allclose(result.market[0, :, 0], [20, 10], atol=1e-12)
    np.testing.assert_allclose(result.execution[0, :, 0], [2, 0], atol=1e-12)
    np.testing.assert_allclose(
        result.reconciled, np.diff(book.wealth, axis=1), atol=1e-10
    )
    np.testing.assert_allclose(result.delta, result.market, atol=1e-12)
    export_attribution(result, tmp_path)
    data = json.loads((tmp_path / "attribution.json").read_text())
    assert data["units"]["theta"] == "currency per elapsed year times dt"
    assert (tmp_path / "attribution.csv").is_file()


def test_option_expiry_is_explicit_event_and_nonpositive_percentage():
    market = GBMPaths(
        np.array([0.0, 0.5, 1.0]), np.array([100.0, 110.0, 120.0])[None, :, None]
    )
    book = simulate_book(
        market,
        (EuropeanOption(0, 100, 1, 0.2, multiplier=1),),
        initial_cash=0,
        allow_borrowing=True,
        initial_orders=(Order(0, -1),),
    )
    result = attribute_book(book)
    np.testing.assert_allclose(
        result.reconciled, np.diff(book.wealth, axis=1), atol=1e-10
    )
    assert result.events[0, -1, 0]
    assert result.theta[0, -1, 0] == 0
    assert result.relative_pnl[0][0] is None
    np.testing.assert_allclose(
        result.approximation + result.residual, result.market, atol=1e-10
    )


@pytest.mark.parametrize(
    "shock",
    [
        dict(spot_end=100.1),
        dict(volatility_end=0.2001),
        dict(rate_end=0.0301),
        dict(time_end=0.001),
    ],
)
def test_independent_small_shocks_and_taylor_remainder(shock):
    option = EuropeanOption(0, 100, 1, 0.2, multiplier=1)
    base = dict(
        spot_start=100,
        spot_end=100,
        rate_start=0.03,
        rate_end=0.03,
        volatility_start=0.2,
        volatility_end=0.2,
        time_start=0,
        time_end=0,
    )
    base.update(shock)
    large = explain_option_move(option, quantity=2, **base)
    half = base.copy()
    for end, start in [
        ("spot_end", "spot_start"),
        ("rate_end", "rate_start"),
        ("volatility_end", "volatility_start"),
        ("time_end", "time_start"),
    ]:
        half[end] = (base[end] + base[start]) / 2
    small = explain_option_move(option, quantity=2, **half)
    assert abs(small["residual"]) < 0.4 * abs(large["residual"])
    assert large["actual"] == pytest.approx(
        sum(large[x] for x in ("delta", "gamma", "vega", "theta", "rho", "residual")),
        abs=1e-12,
    )


def test_cash_only_and_simultaneous_shocks():
    book = simulate_book(
        GBMPaths(np.array([0.0, 1.0]), np.full((1, 2, 1), 100.0)),
        (Stock(),),
        initial_cash=100,
        lending_rate=0.03,
    )
    result = attribute_book(book)
    assert result.market.sum() == 0
    assert result.financing[0, 0] == pytest.approx(100 * np.expm1(0.03))
    move = explain_option_move(
        EuropeanOption(0, 100, 1, 0.2, multiplier=2),
        quantity=-3,
        spot_start=100,
        spot_end=100.1,
        time_start=0,
        time_end=0.001,
        volatility_start=0.2,
        volatility_end=0.2001,
        rate_start=0.03,
        rate_end=0.0301,
    )
    assert move["actual"] == pytest.approx(
        sum(move[x] for x in ("delta", "gamma", "vega", "theta", "rho", "residual")),
        abs=1e-12,
    )
