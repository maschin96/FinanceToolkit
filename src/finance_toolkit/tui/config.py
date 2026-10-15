"""Version-1 input snapshots. Rates are decimals, time is in years.

Only JSON primitives, strict fields and tagged instruments cross the boundary.
No code, filesystem access, network access or calculation occurs while decoding.
Tuples and frozen dataclasses prevent edits to an active job's inputs.
"""

from __future__ import annotations

import math
import types
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Literal, TypeVar, Union, get_args, get_origin, get_type_hints

import numpy as np

from finance_toolkit.instruments.bonds import Bond
from finance_toolkit.option_strategies import StrategyName
from finance_toolkit.portfolio import EuropeanOption, Instrument, Stock, Trade


def percent_to_decimal(value: str) -> float:
    """Convert an explicitly percent-labelled field once; reject NaN/Inf."""
    try:
        result = float(value) / 100
    except ValueError as error:
        raise ValueError("percent must be a finite number") from error
    if not math.isfinite(result):
        raise ValueError("percent must be a finite number")
    return result


@dataclass(frozen=True)
class SimulationConfig:
    """Asset vectors in declared order; GBM output (paths, times, assets)."""

    spots: tuple[float, ...] = (100.0,)
    drifts: tuple[float, ...] = (0.06,)
    volatilities: tuple[float, ...] = (0.2,)
    horizon: float = 1.0
    steps: int = 12
    paths: int = 100
    seed: int = 42
    correlation: tuple[tuple[float, ...], ...] | None = None

    def __post_init__(self) -> None:
        assets = len(self.spots)
        if not assets or len(self.drifts) != assets or len(self.volatilities) != assets:
            raise ValueError("spots/drifts/volatilities need one value per asset")
        if min(self.spots) <= 0 or min(self.volatilities) < 0 or self.horizon <= 0:
            raise ValueError(
                "positive spots/horizon and nonnegative volatilities required"
            )
        if self.steps <= 0 or self.paths <= 0 or self.seed < 0:
            raise ValueError("positive steps/paths and nonnegative seed required")
        if self.paths * (self.steps + 1) * assets > 5_000_000:
            raise ValueError("TUI limit: 5,000,000 price cells per run")
        if self.correlation is not None:
            matrix = np.asarray(self.correlation)
            if (
                matrix.shape != (assets, assets)
                or not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12)
                or not np.allclose(np.diag(matrix), 1, rtol=0, atol=1e-12)
                or np.linalg.eigvalsh(matrix).min() < -1e-12
            ):
                raise ValueError("correlation must be symmetric PSD with unit diagonal")


@dataclass(frozen=True)
class InstrumentConfig:
    """Tagged instrument; asset index follows SimulationConfig vector order."""

    kind: Literal["stock", "call", "put", "bond"] = "stock"
    asset: int = 0
    strike: float = 100.0
    maturity: float = 1.0
    volatility: float = 0.2
    multiplier: float = 100.0
    dividend_yield: float = 0.0
    face: float = 1000.0
    coupon_rate: float = 0.03
    frequency: int = 1

    def build(self) -> Instrument:
        """Construct a public core instrument; preserve all pricing conventions."""
        if self.kind == "stock":
            return Stock(self.asset)
        if self.kind == "bond":
            return Bond(self.face, self.coupon_rate, self.maturity, self.frequency)
        return EuropeanOption(
            self.asset,
            self.strike,
            self.maturity,
            self.volatility,
            kind=self.kind,
            multiplier=self.multiplier,
            dividend_yield=self.dividend_yield,
        )

    def __post_init__(self) -> None:
        self.build()


@dataclass(frozen=True)
class TradeConfig:
    """Signed quantity, absolute fee, optional quote per underlying/bond/share."""

    instrument: InstrumentConfig = InstrumentConfig()
    time: float = 0.0
    quantity: float = 1.0
    price: float | None = None
    fee: float = 0.0

    def build(self) -> Trade:
        """Construct a public Trade without rounding times or quantities."""
        return Trade(
            self.time, self.instrument.build(), self.quantity, self.price, self.fee
        )

    def __post_init__(self) -> None:
        self.build()


@dataclass(frozen=True)
class PortfolioConfig:
    """Static portfolio permits shorts/credit as the core API does, no margin."""

    initial_cash: float = 20000.0
    rate: float = 0.03
    lending_rate: float = 0.0
    borrowing_rate: float = 0.0
    trades: tuple[TradeConfig, ...] = (TradeConfig(quantity=100.0),)


@dataclass(frozen=True)
class ScenarioConfig:
    """Named hypothetical relative spot and absolute volatility/rate shocks."""

    name: str = "scenario"
    spot_shocks: float | tuple[float, ...] = 0.0
    volatility_shocks: float | tuple[float, ...] = 0.0
    rate_shock: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("scenario name must not be empty")


@dataclass(frozen=True)
class RiskConfig:
    """One selected post-event snapshot and explicitly hypothetical shocks."""

    path: int = 0
    time_index: int = 0
    confidence: float = 0.95
    spot_shocks: tuple[float, ...] = (-0.2, 0.0, 0.2)
    rate_shocks: tuple[float, ...] = (-0.01, 0.0, 0.01)
    volatility_shock: float = 0.0
    grid_volatility_shocks: tuple[float, ...] = (0.0, 0.05)
    scenarios: tuple[ScenarioConfig, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.spot_shocks
            or not self.grid_volatility_shocks
            or not self.rate_shocks
        ):
            raise ValueError("stress grid axes must be nonempty")
        if len(self.spot_shocks) * len(self.grid_volatility_shocks) > 10000:
            raise ValueError("TUI stress grid limit: 10,000 cells")
        if (
            len(self.scenarios) > 100
            or len(self.spot_shocks) * len(self.rate_shocks) > 100
        ):
            raise ValueError("TUI scenario limit: 100")
        if len({scenario.name for scenario in self.scenarios}) != len(self.scenarios):
            raise ValueError("distinct scenario names required")


@dataclass(frozen=True)
class StrategyConfig:
    """Built-in rebalancing and option strategy inputs; no executable callbacks."""

    weights: tuple[float, ...] = (0.6,)
    calendar: tuple[float, ...] | None = None
    threshold: float | None = None
    fixed_fee: float = 0.0
    proportional_fee: float = 0.0
    option_strategy: StrategyName = "protective_put"
    asset: int = 0
    maturity: float = 1.0
    volatility: float = 0.2
    multiplier: float = 100.0
    dividend_yield: float = 0.0
    strike: float = 100.0
    upper_strike: float = 110.0
    quantity: float = 1.0
    allow_short: bool = False
    allow_borrowing: bool = False
    orders: tuple[TradeConfig, ...] = ()


@dataclass(frozen=True)
class HedgeConfig:
    """Fine/coarse base-grid cases with explicit execution and funding rules."""

    option: InstrumentConfig = InstrumentConfig(kind="call", multiplier=1.0)
    option_quantity: float = -1.0
    strides: tuple[int, ...] = (1, 2)
    calendar_every: int | None = None
    threshold: float | None = None
    fixed_fee: float = 0.0
    proportional_fee: float = 0.0
    stock_borrow_rate: float = 0.0
    allow_short: bool = False
    allow_borrowing: bool = False


@dataclass(frozen=True)
class IndexConfig:
    """Synthetic, cache-only replay or explicitly requested Yahoo input."""

    source: Literal["demo", "replay", "yahoo"] = "demo"
    tickers: tuple[str, ...] = ("A", "B")
    start: str = "2026-01-01"
    end: str = "2026-02-01"
    base_date: str = "2026-01-01"
    base_value: float = 100.0
    weights: tuple[float, ...] | None = None
    calendar_policy: Literal["strict", "intersection"] = "strict"
    rebalance_dates: tuple[str, ...] = ()
    monthly: bool = False
    cache: str = "outputs/yahoo-cache"
    repair: bool = False
    timeout: float = 10.0
    retries: int = 2


@dataclass(frozen=True)
class Workspace:
    """One immutable versioned input snapshot; never persists results implicitly."""

    schema_version: int = 1
    currency: str = "EUR"
    simulation: SimulationConfig = SimulationConfig()
    portfolio: PortfolioConfig = PortfolioConfig()
    risk: RiskConfig = RiskConfig()
    strategy: StrategyConfig = StrategyConfig()
    hedge: HedgeConfig = HedgeConfig()
    index: IndexConfig = IndexConfig()

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or len(self.currency) != 3
            or not self.currency.isupper()
        ):
            raise ValueError(
                "schema_version 1 and three uppercase currency letters required"
            )
        if not self.currency.isalpha():
            raise ValueError("currency must contain letters")
        if not 0 < self.risk.confidence < 1:
            raise ValueError("confidence must be in (0,1)")
        if not 0 <= self.risk.path < self.simulation.paths:
            raise ValueError("risk path outside simulated paths")
        if not 0 <= self.risk.time_index <= self.simulation.steps:
            raise ValueError("risk time_index outside time grid")
        for trade in self.portfolio.trades:
            if trade.instrument.kind != "bond" and trade.instrument.asset >= len(
                self.simulation.spots
            ):
                raise ValueError("trade asset outside simulation assets")


T = TypeVar("T")


def _decode(cls: type[T], value: object, location: str) -> T:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{location} must be an object")
    hints = get_type_hints(cls)
    unknown = value.keys() - hints.keys()
    if unknown:
        raise ValueError(f"{location}: unknown fields {sorted(unknown)}")
    arguments = {k: _convert(hints[k], v, f"{location}.{k}") for k, v in value.items()}
    try:
        return cls(**arguments)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{location}: {error}") from error


def _convert(annotation: Any, value: object, location: str) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        for candidate in args:
            try:
                return _convert(candidate, value, location)
            except ValueError:
                pass
        raise ValueError(f"{location}: invalid type/value")
    if annotation is type(None):
        if value is None:
            return None
    elif origin is Literal:
        if value in args and any(type(value) is type(x) for x in args):
            return value
    elif origin is tuple:
        if isinstance(value, list | tuple):
            return tuple(_convert(args[0], item, location) for item in value)
    elif isinstance(annotation, type) and is_dataclass(annotation):
        return _decode(annotation, value, location)
    elif annotation is float:
        if isinstance(value, int | float) and not isinstance(value, bool):
            try:
                converted = float(value)
            except OverflowError as error:
                raise ValueError(f"{location}: unrepresentable number") from error
            if math.isfinite(converted):
                return converted
    elif annotation in (int, str, bool):
        if type(value) is annotation:
            return value
    raise ValueError(f"{location}: invalid type/value")


def decode_workspace(value: object) -> Workspace:
    """Reject unknown versions/fields/types before replacing a workspace."""
    return _decode(Workspace, value, "workspace")


def encode_workspace(workspace: Workspace) -> dict[str, Any]:
    """Return owned JSON-compatible primitives; roundtrip validates direct inputs."""
    import json

    payload: dict[str, Any] = json.loads(json.dumps(asdict(workspace), allow_nan=False))
    decode_workspace(payload)
    return payload
