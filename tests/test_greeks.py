"""Independent analytic, parity and difference references; see Doc/18."""

import numpy as np
import pytest
from scipy.special import ndtr

from finance_toolkit.instruments.options import black_scholes, option_greeks


def test_at_money_reference_and_units():
    g = option_greeks(100, 100, 1, 0.2, 0)
    phi = np.exp(-(0.1**2) / 2) / np.sqrt(2 * np.pi)
    np.testing.assert_allclose(
        [g.delta, g.gamma, g.vega, g.theta, g.rho],
        [ndtr(0.1), phi / 20, 100 * phi, -10 * phi, 100 * ndtr(-0.1)],
        rtol=1e-12,
        atol=1e-12,
    )
    assert g.vega_per_percent == pytest.approx(float(g.vega) * 0.01)
    assert g.rho_per_percent == pytest.approx(float(g.rho) * 0.01)


def test_parity_and_broadcasting():
    s = np.array([80.0, 100.0, 120.0])
    k = 100
    t = 2.0
    r = 0.03
    q = 0.01
    c = option_greeks(s, k, t, 0.25, r, dividend_yield=q)
    p = option_greeks(s, k, t, 0.25, r, dividend_yield=q, kind="put")
    np.testing.assert_allclose(
        c.delta - p.delta, np.exp(-q * t), rtol=1e-12, atol=1e-12
    )
    np.testing.assert_allclose(c.gamma, p.gamma, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(c.vega, p.vega, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(
        c.rho - p.rho, k * t * np.exp(-r * t), rtol=1e-12, atol=1e-12
    )
    np.testing.assert_allclose(
        c.theta - p.theta,
        q * s * np.exp(-q * t) - r * k * np.exp(-r * t),
        rtol=1e-12,
        atol=1e-12,
    )


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("h", [1e-3, 5e-4, 1e-4])
def test_central_price_derivatives(kind, h):
    s, k, t, v, r, q = 110.0, 100.0, 1.3, 0.23, 0.04, 0.02
    g = option_greeks(s, k, t, v, r, dividend_yield=q, kind=kind)

    def price(s=s, t=t, v=v, r=r):
        return black_scholes(s, k, t, v, r, dividend_yield=q, kind=kind)

    # Spot derivatives need a currency-scaled step to avoid cancellation.
    hs = h * s
    refs = [
        (price(s=s + hs) - price(s=s - hs)) / (2 * hs),
        (price(s=s + hs) - 2 * price() + price(s=s - hs)) / hs**2,
        (price(v=v + h) - price(v=v - h)) / (2 * h),
        -(price(t=t + h) - price(t=t - h)) / (2 * h),
        (price(r=r + h) - price(r=r - h)) / (2 * h),
    ]
    np.testing.assert_allclose(
        [g.delta, g.gamma, g.vega, g.theta, g.rho], refs, rtol=2e-5, atol=2e-7
    )


@pytest.mark.parametrize(
    "index,value",
    [(0, 0), (1, 0), (2, 0), (3, 0), (0, -1), (2, -1), (3, -1), (4, np.nan)],
)
def test_invalid_or_nonsmooth_domain(index, value):
    args = [100, 100, 1, 0.2, 0.03]
    args[index] = value
    with pytest.raises(ValueError):
        option_greeks(*args)


def test_invalid_kind_and_overflow():
    with pytest.raises(ValueError):
        option_greeks(100, 100, 1, 0.2, 0.03, kind="x")
    with pytest.raises(ValueError):
        option_greeks(100, 100, 1e308, 1e308, -1e308)
