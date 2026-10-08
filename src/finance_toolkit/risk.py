"""Snapshot sensitivities and full repricing, distinct from pathwise accounting."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_array, finite_float
from finance_toolkit.instruments.bonds import TIME_TOLERANCE, Bond
from finance_toolkit.instruments.options import black_scholes, option_greeks
from finance_toolkit.portfolio import EuropeanOption, Instrument, Stock


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Post-event state in one currency; spots (assets,), quantities (positions,).

    Signed quantities with option contract multipliers. Time absolute years;
    rate a continuous flat annual decimal rate. Cash already includes payments.
    Arrays are owned copies; invalid data/instrument indices raise ValueError.
    """

    time: float
    instruments: tuple[Instrument, ...]
    quantities: ArrayLike
    spots: ArrayLike
    rate: float
    cash: float

    def __post_init__(self) -> None:
        for name in ("time", "rate", "cash"):
            object.__setattr__(self, name, finite_float(getattr(self, name), name))
        spots = finite_array(self.spots, "spots").copy()
        quantities = np.asarray(self.quantities, dtype=np.float64).copy()
        if (
            self.time < 0
            or spots.ndim != 1
            or np.any(spots < 0)
            or quantities.shape != (len(self.instruments),)
            or not np.all(np.isfinite(quantities))
        ):
            raise ValueError("invalid snapshot time, spots or quantities")
        for instrument in self.instruments:
            if not isinstance(instrument, Stock | EuropeanOption | Bond):
                raise ValueError("unsupported snapshot instrument")
            if (
                isinstance(instrument, Stock | EuropeanOption)
                and instrument.asset >= spots.size
            ):
                raise ValueError("instrument asset outside snapshot spots")
        spots.setflags(write=False)
        quantities.setflags(write=False)
        object.__setattr__(self, "spots", spots)
        object.__setattr__(self, "quantities", quantities)
        object.__setattr__(self, "instruments", tuple(self.instruments))


@dataclass(frozen=True)
class BondSensitivity:
    """Rho=dP/dr; DV01=-rho*1e-4; convexity=P''/dirty price (years²).

    Shapes match rates; matured instruments have all sensitivities zero.
    """

    rho: NDArray[np.float64]
    dv01: NDArray[np.float64]
    second_derivative: NDArray[np.float64]
    convexity: NDArray[np.float64]


def bond_sensitivity(bond: Bond, time: float, *, rate: ArrayLike) -> BondSensitivity:
    """Differentiate discounted remaining cashflows; same event convention as Bond.

    Finite nonnegative time and finite broadcast rate required. Floating-point
    errors or a zero active price from underflow raise ValueError.
    """
    time = finite_float(time, "time")
    rates = finite_array(rate, "rate")
    if time < 0:
        raise ValueError("time must be nonnegative")
    flows = bond.cashflows()
    mask = flows.times > time + TIME_TOLERANCE
    delays = flows.times[mask] - time
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            pv = np.exp(-rates[..., None] * delays) * (
                flows.coupons[mask] + flows.principal[mask]
            )
            rho = -np.sum(pv * delays, axis=-1)
            second = np.sum(pv * delays**2, axis=-1)
            price = pv.sum(axis=-1)
            convexity = second / price if np.any(mask) else np.zeros_like(price)
    except FloatingPointError as error:
        raise ValueError("unrepresentable bond sensitivities") from error
    values = tuple(
        np.asarray(x, dtype=np.float64) for x in (rho, -rho * 1e-4, second, convexity)
    )
    if not all(np.all(np.isfinite(x)) for x in values):
        raise ValueError("unrepresentable bond sensitivities")
    return BondSensitivity(*values)


@dataclass(frozen=True)
class PortfolioExposures:
    """Signed monetary derivatives, position order as snapshot instruments.

    Asset delta/gamma indexed by snapshot asset, never summed across assets.
    Vega is for a common absolute option-volatility shock, rho for a parallel
    continuous-rate shock. Cash is unchanged by instantaneous repricing.
    Bond convexity is per bond, unsigned; DV01 includes signed position size.
    """

    position_delta: NDArray[np.float64]
    position_gamma: NDArray[np.float64]
    position_vega: NDArray[np.float64]
    position_theta: NDArray[np.float64]
    position_rho: NDArray[np.float64]
    position_dv01: NDArray[np.float64]
    bond_convexity: NDArray[np.float64]
    asset_delta: NDArray[np.float64]
    asset_gamma: NDArray[np.float64]
    vega: float
    rho: float
    cash: float


def portfolio_exposures(snapshot: PortfolioSnapshot) -> PortfolioExposures:
    """Aggregate position Greeks; active nonsmooth options raise ValueError.

    Expired/zero-sized instruments have zero sensitivity; remaining bond rho
    uses ex-payment cashflows. Numeric overflow raises ValueError.
    """
    spots = np.asarray(snapshot.spots)
    quantities = np.asarray(snapshot.quantities)
    count = len(snapshot.instruments)
    delta, gamma, vega, theta, rho, dv01, convexity = np.zeros((7, count))
    asset_delta, asset_gamma = np.zeros((2, spots.size))
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            for i, instrument in enumerate(snapshot.instruments):
                qty = quantities[i]
                if qty == 0:
                    continue
                if isinstance(instrument, Stock):
                    delta[i] = qty
                elif snapshot.time >= instrument.maturity - TIME_TOLERANCE:
                    continue
                elif isinstance(instrument, EuropeanOption):
                    g = option_greeks(
                        spots[instrument.asset],
                        instrument.strike,
                        instrument.maturity - snapshot.time,
                        instrument.volatility,
                        snapshot.rate,
                        dividend_yield=instrument.dividend_yield,
                        kind=instrument.kind,
                    )
                    scale = qty * instrument.multiplier
                    delta[i], gamma[i], vega[i], theta[i], rho[i] = (
                        float(x) * scale
                        for x in (g.delta, g.gamma, g.vega, g.theta, g.rho)
                    )
                else:
                    b = bond_sensitivity(instrument, snapshot.time, rate=snapshot.rate)
                    rho[i] = float(b.rho) * qty
                    dv01[i] = float(b.dv01) * qty
                    convexity[i] = float(b.convexity)
                if isinstance(instrument, Stock | EuropeanOption):
                    asset_delta[instrument.asset] += delta[i]
                    asset_gamma[instrument.asset] += gamma[i]
            total_vega, total_rho = float(vega.sum()), float(rho.sum())
    except FloatingPointError as error:
        raise ValueError("unrepresentable portfolio exposures") from error
    if not all(
        np.all(np.isfinite(x))
        for x in (
            delta,
            gamma,
            vega,
            theta,
            rho,
            dv01,
            convexity,
            asset_delta,
            asset_gamma,
            total_vega,
            total_rho,
        )
    ):
        raise ValueError("unrepresentable portfolio exposures")
    return PortfolioExposures(
        delta,
        gamma,
        vega,
        theta,
        rho,
        dv01,
        convexity,
        asset_delta,
        asset_gamma,
        total_vega,
        total_rho,
        snapshot.cash,
    )


@dataclass(frozen=True)
class StressScenario:
    """Named hypothetical shocks; validated when applied to a snapshot.

    spot_shocks: scalar or (assets,), relative; volatility_shocks: scalar or
    (positions,), absolute decimal change, must be zero on non-option positions.
    rate_shock: absolute decimal continuous-rate change. No probabilities.
    """

    name: str
    spot_shocks: ArrayLike = 0.0
    volatility_shocks: ArrayLike = 0.0
    rate_shock: float = 0.0


@dataclass(frozen=True)
class StressResult:
    """Currency values, same position order; cash unchanged, P&L stress minus base."""

    name: str
    base_positions: NDArray[np.float64]
    stressed_positions: NDArray[np.float64]
    position_pnl: NDArray[np.float64]
    base_value: float
    stressed_value: float
    total_pnl: float
    cash: float


def _snapshot_values(
    snapshot: PortfolioSnapshot,
    spots: NDArray[np.float64],
    rate: float,
    vol_shocks: NDArray[np.float64],
) -> NDArray[np.float64]:
    values = np.zeros(len(snapshot.instruments))
    quantities = np.asarray(snapshot.quantities)
    for i, instrument in enumerate(snapshot.instruments):
        if quantities[i] == 0:
            continue
        if isinstance(instrument, Stock):
            quote = float(spots[instrument.asset])
        elif snapshot.time >= instrument.maturity - TIME_TOLERANCE:
            continue
        elif isinstance(instrument, Bond):
            quote = float(instrument.price(snapshot.time, rate=rate))
        else:
            quote = (
                float(
                    black_scholes(
                        spots[instrument.asset],
                        instrument.strike,
                        instrument.maturity - snapshot.time,
                        instrument.volatility + vol_shocks[i],
                        rate,
                        dividend_yield=instrument.dividend_yield,
                        kind=instrument.kind,
                    )
                )
                * instrument.multiplier
            )
        values[i] = quote * quantities[i]
    return values


def stress_portfolio(
    snapshot: PortfolioSnapshot, scenario: StressScenario
) -> StressResult:
    """Fully reprice at unchanged time/holdings/cash; invalid shocks raise ValueError.

    Negative stressed spots/volatility rejected, zero allowed for price APIs.
    Expired instruments remain zero, with payments already in snapshot cash.
    Scalar volatility shocks apply only to options; vector shocks require zero
    entries on other positions. Numeric overflow is rejected.
    """
    if not isinstance(scenario.name, str) or not scenario.name.strip():
        raise ValueError("scenario needs a nonempty name")
    spots = np.asarray(snapshot.spots)
    ds = np.broadcast_to(finite_array(scenario.spot_shocks, "spot_shocks"), spots.shape)
    raw_vol = finite_array(scenario.volatility_shocks, "volatility_shocks")
    dv = np.broadcast_to(raw_vol, (len(snapshot.instruments),)).copy()
    dr = finite_float(scenario.rate_shock, "rate_shock")
    for i, instrument in enumerate(snapshot.instruments):
        if isinstance(instrument, EuropeanOption):
            if instrument.volatility + dv[i] < 0:
                raise ValueError("stressed volatility must be nonnegative")
        elif raw_vol.ndim == 0:
            dv[i] = 0
        elif dv[i] != 0:
            raise ValueError("volatility shock on non-option position")
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            stressed_spots = spots * (1 + ds)
            if np.any(ds < -1) or np.any(stressed_spots < 0):
                raise ValueError("stressed spots must be nonnegative")
            stressed_rate = finite_float(snapshot.rate + dr, "stressed_rate")
            base = _snapshot_values(snapshot, spots, snapshot.rate, np.zeros(dv.shape))
            stressed = _snapshot_values(snapshot, stressed_spots, stressed_rate, dv)
            pnl = stressed - base
            base_value = float(base.sum() + snapshot.cash)
            stressed_value = float(stressed.sum() + snapshot.cash)
            total_pnl = float(pnl.sum())
    except (FloatingPointError, OverflowError) as error:
        raise ValueError("unrepresentable stress values") from error
    if not all(
        np.all(np.isfinite(x))
        for x in (base, stressed, pnl, base_value, stressed_value, total_pnl)
    ):
        raise ValueError("unrepresentable stress values")
    return StressResult(
        scenario.name,
        base,
        stressed,
        pnl,
        base_value,
        stressed_value,
        total_pnl,
        snapshot.cash,
    )


def stress_grid(
    snapshot: PortfolioSnapshot, spot_shocks: ArrayLike, volatility_shocks: ArrayLike
) -> NDArray[np.float64]:
    """P&L grid (volatility shocks, spot shocks), common shocks across options/assets.

    Both axes must be nonempty finite 1D vectors. Uses stress_portfolio unchanged,
    suitable for optional heatmap adapters; no implicit probability interpretation.
    """
    ds = finite_array(spot_shocks, "spot_shocks")
    dv = finite_array(volatility_shocks, "volatility_shocks")
    if ds.ndim != 1 or dv.ndim != 1:
        raise ValueError("grid axes must be one-dimensional")
    return np.asarray(
        [
            [
                stress_portfolio(snapshot, StressScenario("grid", s, v)).total_pnl
                for s in ds
            ]
            for v in dv
        ],
        dtype=np.float64,
    )
