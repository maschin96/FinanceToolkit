"""Bond values from independently enumerated cashflows."""

import math

import numpy as np
import pytest

from finance_toolkit.instruments.bonds import Bond


def test_zero_coupon_value_and_maturity() -> None:
    bond = Bond(face=1000, coupon_rate=0, maturity=3, frequency=1)
    assert float(bond.price(0, rate=0.04)) == pytest.approx(
        1000 * math.exp(-0.12), abs=1e-10
    )
    assert float(bond.price(1, rate=-0.02)) == pytest.approx(
        1000 * math.exp(0.04), abs=1e-10
    )
    assert float(bond.price(3, rate=0.04)) == 0
    assert float(bond.price(4, rate=0.04)) == 0


def test_coupon_cashflows_and_present_value() -> None:
    bond = Bond(face=100, coupon_rate=0.06, maturity=2, frequency=2)
    flows = bond.cashflows()
    np.testing.assert_array_equal(flows.times, [0.5, 1, 1.5, 2])
    np.testing.assert_array_equal(flows.coupons, [3, 3, 3, 3])
    np.testing.assert_array_equal(flows.principal, [0, 0, 0, 100])
    expected = sum(
        c * math.exp(-0.04 * t) for t, c in [(0.5, 3), (1, 3), (1.5, 3), (2, 103)]
    )
    assert float(bond.price(0, rate=0.04)) == pytest.approx(expected, abs=1e-11)
    assert float(bond.price(0, rate=0)) == 112


def test_clean_dirty_accrual_and_coupon_boundary() -> None:
    bond = Bond(face=100, coupon_rate=0.08, maturity=2, frequency=2)
    assert bond.accrued_interest(0.25) == 2
    assert bond.accrued_interest(0.5) == 0
    assert bond.accrued_interest(2) == 0
    dirty = bond.price(0.25, rate=0.03)
    assert float(dirty - bond.price(0.25, rate=0.03, clean=True)) == pytest.approx(2)
    expected_ex_coupon = (
        4 * math.exp(-0.03 * 0.5) + 4 * math.exp(-0.03) + 104 * math.exp(-0.03 * 1.5)
    )
    assert float(bond.price(0.5, rate=0.03)) == pytest.approx(
        expected_ex_coupon, abs=1e-11
    )
    before = float(bond.price(0.5 - 1e-6, rate=0.03))
    assert before > float(bond.price(0.5, rate=0.03)) + 3.99


def test_yield_scenarios_and_cashflow_conservation() -> None:
    bond = Bond(face=100, coupon_rate=0.05, maturity=3, frequency=1)
    values = bond.price(0, rate=[-0.02, 0, 0.05, 0.1])
    assert values.shape == (4,)
    assert np.all(np.diff(values) < 0)
    flows = bond.cashflows()
    assert float(flows.coupons.sum() + flows.principal.sum()) == 115
    # Coupon rate is nominal, discount rate continuous: equivalent par rate.
    assert float(bond.price(0, rate=math.log1p(0.05))) == pytest.approx(100, abs=1e-11)


@pytest.mark.parametrize(
    "overrides",
    [
        {"face": 0},
        {"face": np.nan},
        {"coupon_rate": -0.1},
        {"coupon_rate": np.inf},
        {"maturity": 0},
        {"maturity": 1.2},
        {"maturity": np.inf},
        {"frequency": 0},
        {"frequency": 1.5},
        {"frequency": True},
    ],
)
def test_invalid_bond_parameters(overrides: dict) -> None:
    args = dict(face=100, coupon_rate=0.05, maturity=2, frequency=2)
    args.update(overrides)
    with pytest.raises(ValueError):
        Bond(**args)


@pytest.mark.parametrize(
    "time,rate", [(-1, 0.03), (np.nan, 0.03), (0, np.inf), (0, -1e308)]
)
def test_invalid_valuation(time: float, rate: float) -> None:
    with pytest.raises(ValueError):
        Bond(face=100, coupon_rate=0.05, maturity=2).price(time, rate=rate)
