import csv
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


@pytest.mark.parametrize("offset", [-5e-11, 0.0, 5e-11])
@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("quantity,multiplier", [(2, 1), (-3, 10)])
def test_tolerant_expiry_reconciles_and_exports_once(
    tmp_path, offset, kind, quantity, multiplier
):
    market = GBMPaths(
        np.array([0.0, 0.5, 1.0 + offset, 1.5]),
        np.array([[100, 110, 120, 130], [100, 90, 80, 70]])[:, :, None],
    )
    option = EuropeanOption(0, 100, 1, 0.2, kind=kind, multiplier=multiplier)
    book = simulate_book(
        market,
        (option,),
        initial_cash=1000,
        initial_orders=(Order(0, quantity),),
        allow_borrowing=True,
    )
    result = attribute_book(book)
    # Intrinsic values at expiry are 20/0 (call) or 0/20 (put), in currency
    # per share. The signed contract scale applies once, including zero payoffs.
    payoff = np.array([20, 0] if kind == "call" else [0, 20])
    payment = quantity * multiplier * payoff
    np.testing.assert_array_equal(book.settlements[:, 2, 0], payment)
    np.testing.assert_array_equal(book.settlements[:, 3, 0], 0)
    np.testing.assert_array_equal(book.quantities[:, 2:, 0], 0)
    np.testing.assert_allclose(
        book.wealth[:, -1],
        1000 + book.trade_cashflows[:, 0, 0] + payment,
        rtol=1e-12,
        atol=1e-10,
    )
    np.testing.assert_array_equal(result.events[:, 1, 0], True)
    np.testing.assert_array_equal(result.events[:, 2, 0], False)
    for name in ("delta", "gamma", "vega", "theta", "rho"):
        np.testing.assert_array_equal(getattr(result, name)[:, 1:, 0], 0)
    # Roundoff in currency sums around 1000: 1e-10 absolute / 1e-12 relative.
    np.testing.assert_allclose(
        result.reconciled, np.diff(book.wealth, axis=1), rtol=1e-12, atol=1e-10
    )
    np.testing.assert_allclose(
        result.residual[:, 1, 0], result.market[:, 1, 0], rtol=0, atol=1e-10
    )
    export_attribution(result, tmp_path)
    data = json.loads((tmp_path / "attribution.json").read_text())
    assert data["events"] == result.events.tolist()
    np.testing.assert_array_equal(data["settlements"], result.settlements)
    with (tmp_path / "attribution.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6
    for row in rows:
        if float(row["time"]) == market.times[2]:
            assert row["events"] == "True"
            assert float(row["theta"]) == 0


@pytest.mark.parametrize("offset", [-5e-11, 0.0, 5e-11])
def test_standalone_move_normalizes_expiry_endpoints(offset):
    result = explain_option_move(
        EuropeanOption(0, 100, 1, 0.2, multiplier=10),
        quantity=-2,
        spot_start=110,
        spot_end=120,
        time_start=1 + offset,
        time_end=1 + offset,
        volatility_start=0.2,
        volatility_end=0.2,
        rate_start=0.03,
        rate_end=0.03,
    )
    assert result["event"]
    assert result["actual"] == -200
    assert result["residual"] == -200
    for name in ("delta", "gamma", "vega", "theta", "rho"):
        assert result[name] == 0


@pytest.mark.parametrize(
    "start,end",
    [(0, 1 + 2e-10), (1 + 2e-10, 1 + 3e-10), (1 + 5e-11, 1), (-5e-11, 0)],
)
def test_standalone_move_rejects_invalid_times(start, end):
    with pytest.raises(ValueError, match="times must be ordered within option life"):
        explain_option_move(
            EuropeanOption(0, 100, 1, 0.2),
            quantity=1,
            spot_start=100,
            spot_end=110,
            time_start=start,
            time_end=end,
            volatility_start=0.2,
            volatility_end=0.2,
            rate_start=0.03,
            rate_end=0.03,
        )


def test_outside_expiry_tolerance_keeps_smooth_move_and_grid_contract():
    option = EuropeanOption(0, 100, 1, 0.2, multiplier=1)
    result = explain_option_move(
        option,
        quantity=1,
        spot_start=100,
        spot_end=100,
        time_start=0.5,
        time_end=1 - 2e-10,
        volatility_start=0.2,
        volatility_end=0.2,
        rate_start=0,
        rate_end=0,
    )
    assert not result["event"]
    assert result["theta"] != 0
    with pytest.raises(ValueError, match="expiry must match exactly one grid point"):
        simulate_book(
            GBMPaths(np.array([0.0, 1 + 2e-10]), np.full((1, 2, 1), 100.0)),
            (option,),
            initial_cash=1000,
        )


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
