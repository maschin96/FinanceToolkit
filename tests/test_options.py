"""European options: analytic invariants and independent payoff integrals."""

import math

import numpy as np
import pytest
from scipy.integrate import quad

from finance_toolkit.instruments.options import black_scholes, option_payoff


def test_known_black_scholes_prices() -> None:
    args = dict(spot=100.0, strike=100.0, maturity=1.0, volatility=0.2, rate=0.05)
    assert float(black_scholes(kind="call", **args)) == pytest.approx(
        10.450583572185565, abs=1e-11
    )
    assert float(black_scholes(kind="put", **args)) == pytest.approx(
        5.573526022256971, abs=1e-11
    )


@pytest.mark.parametrize("rate", [-0.03, 0.05])
def test_put_call_parity_with_dividends(rate: float) -> None:
    spots = np.array([0.0, 60.0, 100.0, 150.0])
    args = dict(
        spot=spots,
        strike=100,
        maturity=2,
        volatility=0.3,
        rate=rate,
        dividend_yield=0.02,
    )
    difference = black_scholes(kind="call", **args) - black_scholes(kind="put", **args)
    np.testing.assert_allclose(
        difference, spots * np.exp(-0.04) - 100 * np.exp(-rate * 2), atol=1e-11
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_expiry_zero_volatility_and_zero_spot(kind: str) -> None:
    spots = np.array([0.0, 80.0, 100.0, 120.0])
    payoff = option_payoff(spots, 100.0, kind=kind)
    np.testing.assert_array_equal(
        black_scholes(spots, 100, 0, 0.2, 0.03, kind=kind), payoff
    )
    discounted = np.exp(-0.03 * 2) * option_payoff(
        spots * np.exp((0.03 - 0.01) * 2), 100, kind=kind
    )
    np.testing.assert_allclose(
        black_scholes(spots, 100, 2, 0, 0.03, dividend_yield=0.01, kind=kind),
        discounted,
        atol=1e-12,
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_price_matches_independent_discounted_payoff_integral(kind: str) -> None:
    spot, strike, t, sigma, r, q = 85.0, 100.0, 1.5, 0.35, -0.01, 0.02
    mean = (r - q - sigma * sigma / 2) * t
    scale = sigma * math.sqrt(t)
    threshold = (math.log(strike / spot) - mean) / scale

    def integrand(z: float) -> float:
        terminal = spot * math.exp(mean + scale * z)
        payoff = (
            max(terminal - strike, 0) if kind == "call" else max(strike - terminal, 0)
        )
        return payoff * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    # ±12 normal standard deviations: negligible omitted probability/first moment.
    interval = (threshold, 12.0) if kind == "call" else (-12.0, threshold)
    expected = math.exp(-r * t) * quad(integrand, *interval, epsabs=1e-11)[0]
    assert float(
        black_scholes(spot, strike, t, sigma, r, dividend_yield=q, kind=kind)
    ) == pytest.approx(expected, abs=1e-9)


def test_broadcasting_bounds_and_monotonicity() -> None:
    spots = np.array([50.0, 100.0, 200.0])[:, None]
    sigmas = np.array([0.1, 0.2, 0.5])
    calls = black_scholes(spots, 100, 1, sigmas, 0.05)
    puts = black_scholes(spots, 100, 1, sigmas, 0.05, kind="put")
    assert calls.shape == (3, 3)
    assert np.all(np.diff(calls, axis=0) > 0)
    assert np.all(np.diff(puts, axis=0) < 0)
    assert np.all(np.diff(calls, axis=1) > 0)
    assert np.all(calls <= spots)
    assert np.all(calls >= np.maximum(spots - 100 * np.exp(-0.05), 0))
    assert np.all(puts <= 100 * np.exp(-0.05))


@pytest.mark.parametrize(
    "overrides",
    [
        {"spot": -1},
        {"spot": np.nan},
        {"strike": 0},
        {"strike": np.inf},
        {"maturity": -1},
        {"volatility": -0.2},
        {"rate": np.nan},
        {"dividend_yield": np.inf},
        {"kind": "american"},
        {"spot": [1, 2], "strike": [1, 2, 3]},
        {"rate": -1e308},
    ],
)
def test_invalid_option_parameters(overrides: dict) -> None:
    args = dict(spot=100, strike=100, maturity=1, volatility=0.2, rate=0.05)
    args.update(overrides)
    with pytest.raises(ValueError):
        black_scholes(**args)


def test_invalid_payoff_parameters() -> None:
    for spot, strike, kind in [(-1, 100, "call"), (100, 0, "put"), (100, 100, "other")]:
        with pytest.raises(ValueError):
            option_payoff(spot, strike, kind=kind)


@pytest.mark.parametrize(
    "kind,expected", [("call", [0, 0, 0, 10]), ("put", [100, 10, 0, 0])]
)
@pytest.mark.parametrize("rate,dividend", [(1e308, -1e308), (-1e308, 1e308)])
def test_expiry_ignores_extreme_finite_rates_and_volatility(
    kind, expected, rate, dividend
):
    # At T=0 the independent expectation is intrinsic value, regardless of
    # finite r/q/sigma. No discount or analytic branch is needed.
    with np.errstate(all="raise"):
        prices = black_scholes(
            [0, 90, 100, 110],
            100,
            0,
            1e308,
            rate,
            dividend_yield=dividend,
            kind=kind,
        )
    np.testing.assert_array_equal(prices, expected)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_mixed_broadcast_boundaries_and_active_reference(kind):
    # 2x4 broadcast: expiry, zero vol, zero spot, ordinary analytic quote.
    # Tiny T keeps r*T/q*T finite in the deterministic branch, although r-q
    # itself overflows. exp(+/-1) discounted legs give its independent value.
    spots = np.array([100, 110])[:, None]
    s = np.broadcast_to(spots, (2, 4)).copy()
    s[:, 2] = 0
    r = np.array([1e308, 1e308, 1e308, 0.05])
    q = np.array([-1e308, -1e308, -1e308, 0.0])
    prices = black_scholes(
        s,
        100,
        [0, 1e-308, 1, 1],
        [1e308, 0, 1e308, 0.2],
        r,
        dividend_yield=q,
        kind=kind,
    )
    assert prices.shape == (2, 4)
    np.testing.assert_array_equal(prices[:, 0], [0, 10] if kind == "call" else [0, 0])
    deterministic = np.maximum(
        spots[:, 0] * math.e - 100 / math.e
        if kind == "call"
        else 100 / math.e - spots[:, 0] * math.e,
        0,
    )
    np.testing.assert_allclose(prices[:, 1], deterministic, rtol=2e-15, atol=0)
    np.testing.assert_array_equal(prices[:, 2], 0)
    # Independent established ATM reference; ordinary broadcast row prices
    # must agree with scalar evaluation without boundary parameters.
    assert prices[0, 3] == pytest.approx(
        10.450583572185565 if kind == "call" else 5.573526022256971,
        abs=1e-11,
    )
    assert prices[1, 3] == float(black_scholes(110, 100, 1, 0.2, 0.05, kind=kind))


def test_zero_spot_call_ignores_irrelevant_discounts():
    assert float(black_scholes(0, 100, 1, 1e308, -1e308, dividend_yield=-1e308)) == 0
    assert float(black_scholes(0, 100, 1, 0, -1e308, dividend_yield=-1e308)) == 0


def test_zero_spot_put_uses_only_discounted_strike():
    assert float(
        black_scholes(
            0,
            100,
            1,
            1e308,
            0.03,
            dividend_yield=-1e308,
            kind="put",
        )
    ) == pytest.approx(100 * math.exp(-0.03), rel=2e-15, abs=0)
    with pytest.raises(ValueError, match="unrepresentable"):
        black_scholes(0, 100, 1, 0.2, -1e308, kind="put")


def test_active_unrepresentable_price_still_rejected_in_mixed_array():
    with pytest.raises(ValueError, match="unrepresentable"):
        black_scholes(
            [110, 110], 100, [0, 1], 0.2, [1e308, -1e308], dividend_yield=[-1e308, 0]
        )
