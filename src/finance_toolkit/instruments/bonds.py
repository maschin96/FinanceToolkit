"""Default-free fixed-coupon bonds, issued at time zero, ex-payment valuation."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_array, finite_float, positive_integer

TIME_TOLERANCE = 1e-10  # years; used only for matching scheduled payment times


@dataclass(frozen=True)
class BondCashflows:
    """Scheduled times (years), coupons and principal in currency per bond."""

    times: NDArray[np.float64]
    coupons: NDArray[np.float64]
    principal: NDArray[np.float64]


@dataclass(frozen=True)
class Bond:
    """Fixed coupon bond issued at t=0; annual nominal coupon, regular payments.

    Face and maturity must be positive, coupon_rate nonnegative; all finite.
    Maturity * frequency must be a positive integer within 1e-10 periods.
    No calendars, default risk or market day-count conventions. ValueError for
    invalid parameters and unrepresentable prices/cashflows.
    """

    face: float
    coupon_rate: float
    maturity: float
    frequency: int = 1

    def __post_init__(self) -> None:
        for name in ("face", "coupon_rate", "maturity"):
            object.__setattr__(self, name, finite_float(getattr(self, name), name))
        object.__setattr__(
            self, "frequency", positive_integer(self.frequency, "frequency")
        )
        if self.face <= 0 or self.coupon_rate < 0 or self.maturity <= 0:
            raise ValueError("face/maturity must be positive; coupon_rate nonnegative")
        periods = self.maturity * self.frequency
        if not np.isfinite(periods) or abs(periods - round(periods)) > TIME_TOLERANCE:
            raise ValueError("maturity must contain a whole number of coupon periods")
        if round(periods) < 1:
            raise ValueError("maturity must contain at least one coupon period")
        if not np.isfinite(self.face * self.coupon_rate / self.frequency):
            raise ValueError("coupon amount is unrepresentable")

    def cashflows(self) -> BondCashflows:
        """Return newly allocated arrays of separate coupon/principal payments."""
        periods = round(self.maturity * self.frequency)
        times = np.arange(1, periods + 1, dtype=np.float64) / self.frequency
        coupons = np.full(periods, self.face * self.coupon_rate / self.frequency)
        principal = np.zeros(periods, dtype=np.float64)
        principal[-1] = self.face
        return BondCashflows(times, coupons, principal)

    def accrued_interest(self, time: float) -> float:
        """Linear coupon accrual; zero at issuance, coupon dates and after maturity."""
        time = finite_float(time, "time")
        if time < 0:
            raise ValueError("time must be nonnegative")
        if time >= self.maturity - TIME_TOLERANCE:
            return 0.0
        periods = time * self.frequency
        if abs(periods - round(periods)) <= TIME_TOLERANCE * self.frequency:
            return 0.0
        fraction = periods - np.floor(periods)
        return float(self.face * self.coupon_rate / self.frequency * fraction)

    def price(
        self, time: float, *, rate: ArrayLike, clean: bool = False
    ) -> NDArray[np.float64]:
        """Discount future payments on a flat continuous annual rate curve.

        Time is absolute years since issuance. Rates broadcast to output shape
        (scalar yields 0D); negative rates allowed. Dirty is default; clean
        subtracts linear accrued interest. Payment at `time` is already booked,
        so price is ex-coupon and zero at/after maturity. Match tolerance 1e-10
        years. Invalid times/rates or numerical overflow raise ValueError.
        """
        time = finite_float(time, "time")
        rates = finite_array(rate, "rate")
        if time < 0:
            raise ValueError("time must be nonnegative")
        flows = self.cashflows()
        future = flows.times > time + TIME_TOLERANCE
        try:
            with np.errstate(over="raise", invalid="raise", under="ignore"):
                discounts = np.exp(-rates[..., None] * (flows.times[future] - time))
                result = np.sum(
                    discounts * (flows.coupons[future] + flows.principal[future]),
                    axis=-1,
                )
                if clean:
                    result = result - self.accrued_interest(time)
        except FloatingPointError as error:
            raise ValueError("rates produce unrepresentable bond values") from error
        if not np.all(np.isfinite(result)):
            raise ValueError("rates produce unrepresentable bond values")
        return np.asarray(result, dtype=np.float64)
