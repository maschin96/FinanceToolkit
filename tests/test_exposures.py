"""Cashflow derivative and signed position references, in currency/years."""

import numpy as np
import pytest

from finance_toolkit.instruments.bonds import Bond
from finance_toolkit.portfolio import EuropeanOption, Stock
from finance_toolkit.risk import (
    PortfolioSnapshot,
    bond_sensitivity,
    portfolio_exposures,
)


def test_zero_coupon_derivatives():
    b = Bond(100, 0, 2)
    g = bond_sensitivity(b, 0, rate=0)
    np.testing.assert_allclose(
        [g.rho, g.dv01, g.second_derivative, g.convexity],
        [-200, 0.02, 400, 4],
        rtol=1e-12,
        atol=1e-12,
    )
    assert float(bond_sensitivity(b, 2, rate=0.03).convexity) == 0


def test_coupon_derivatives_from_independent_sum():
    b = Bond(100, 0.06, 2, 2)
    t = 0.5
    r = 0.04
    delays = np.array([0.5, 1, 1.5])
    flows = np.array([3.0, 3.0, 103.0])
    pv = flows * np.exp(-r * delays)
    g = bond_sensitivity(b, t, rate=r)
    np.testing.assert_allclose(
        [g.rho, g.second_derivative, g.convexity],
        [
            -np.sum(delays * pv),
            np.sum(delays**2 * pv),
            np.sum(delays**2 * pv) / sum(pv),
        ],
        rtol=1e-12,
        atol=1e-12,
    )
    h = 1e-4
    np.testing.assert_allclose(
        g.rho,
        (b.price(t, rate=r + h) - b.price(t, rate=r - h)) / (2 * h),
        rtol=2e-7,
        atol=1e-8,
    )


def test_asset_labels_signs_and_multiplier():
    o = EuropeanOption(0, 100, 1, 0.2, multiplier=10)
    snap = PortfolioSnapshot(
        0,
        (Stock(0), Stock(1), o, o, Bond(100, 0, 2)),
        [2, 3, 1, -1, 2],
        [100, 200],
        0,
        50,
    )
    e = portfolio_exposures(snap)
    np.testing.assert_allclose(e.asset_delta, [2, 3], rtol=0, atol=1e-12)
    np.testing.assert_allclose(e.asset_gamma, [0, 0], rtol=0, atol=1e-12)
    assert e.vega == pytest.approx(0, abs=1e-12)
    assert e.rho == pytest.approx(-400)
    assert e.position_delta[2] == pytest.approx(-e.position_delta[3])
    assert e.position_dv01[-1] == pytest.approx(0.04)
    assert e.cash == 50


def test_matured_instruments_are_zero():
    snap = PortfolioSnapshot(
        2, (EuropeanOption(0, 100, 1, 0), Bond(100, 0.03, 2)), [1, 1], [100], 0.03, 100
    )
    e = portfolio_exposures(snap)
    assert e.rho == 0
    assert e.vega == 0
    np.testing.assert_array_equal(e.asset_delta, [0])


@pytest.mark.parametrize(
    "field,value",
    [
        ("time", -1),
        ("spots", [-1]),
        ("quantities", [1, 2]),
        ("rate", float("nan")),
        ("cash", float("inf")),
    ],
)
def test_snapshot_validation(field, value):
    args = dict(
        time=0, instruments=(Stock(),), quantities=[1], spots=[100], rate=0.03, cash=0
    )
    args[field] = value
    with pytest.raises(ValueError):
        PortfolioSnapshot(**args)


def test_active_zero_vol_greeks_rejected_and_bad_asset():
    with pytest.raises(ValueError):
        portfolio_exposures(
            PortfolioSnapshot(0, (EuropeanOption(0, 100, 1, 0),), [1], [100], 0, 0)
        )
    with pytest.raises(ValueError):
        PortfolioSnapshot(0, (Stock(2),), [1], [100], 0, 0)
