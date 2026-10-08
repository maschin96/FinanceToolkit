"""Reproducible offline M2 Risk Lab; CSV/JSON and optional PNG adapters."""

import argparse
import csv
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from finance_toolkit import __version__
from finance_toolkit.analytics import drawdown, tail_risk
from finance_toolkit.portfolio import (
    EuropeanOption,
    PortfolioPaths,
    Stock,
    Trade,
    value_portfolio,
)
from finance_toolkit.risk import (
    PortfolioExposures,
    PortfolioSnapshot,
    StressResult,
    StressScenario,
    portfolio_exposures,
    stress_grid,
    stress_portfolio,
)
from finance_toolkit.simulation import GBMPaths, simulate_gbm
from finance_toolkit.strategies import StrategyPaths, simulate_rebalancing


@dataclass(frozen=True)
class RiskLab:
    """Computed model results and their full reproducibility configuration."""

    configuration: dict[str, object]
    market: GBMPaths
    strategies: dict[str, StrategyPaths]
    option_portfolios: dict[str, PortfolioPaths]
    metrics: dict[str, dict[str, float | None]]
    snapshots: dict[str, PortfolioSnapshot]
    exposures: dict[str, PortfolioExposures]
    stresses: dict[str, tuple[StressResult, ...]]


def _metrics(
    wealth: NDArray[np.float64], initial_cash: float
) -> dict[str, float | None]:
    risk = tail_risk(initial_cash - wealth[:, -1])
    return {
        "mean_terminal_pnl": float(np.mean(wealth[:, -1] - initial_cash)),
        "mean_terminal_return": float(np.mean(wealth[:, -1] / initial_cash - 1)),
        "value_at_risk": risk.value_at_risk,
        "expected_shortfall": risk.expected_shortfall,
        "mean_maximum_drawdown": float(drawdown(wealth).max(axis=1).mean())
        if np.all(wealth > 0)
        else None,
    }


def build_risk_lab(*, seed: int = 42, paths: int = 1000, steps: int = 12) -> RiskLab:
    """Two-asset GBM demo over one year; shared paths/capital per comparison.

    Rebalancing weights 40%/40%, cash 20%, fixed fee 1 EUR and notional fee 0.1%,
    cash lending 3% continuous. Calendar every third grid point (signal times,
    execution next point), threshold 5pp including cash. Protective put uses
    100 shares of asset 0 plus one strike-100, 100-multiplier one-year put,
    BSM volatility 20%, rate 3%; both option portfolios have zero execution fees
    and cash lending 3%. All opening capitals EUR 20,000. Synthetic scenarios,
    no empirical data. Invalid seed/path/grid parameters propagate ValueError.
    """
    market = simulate_gbm(
        [100, 80],
        drift=[0.06, 0.04],
        volatility=[0.2, 0.15],
        horizon=1,
        steps=steps,
        paths=paths,
        correlation=[[1, 0.4], [0.4, 1]],
        seed=seed,
    )
    dates = market.times[3:-1:3]
    common = dict(
        initial_cash=20000.0, fixed_fee=1.0, proportional_fee=0.001, lending_rate=0.03
    )
    strategies = {
        "buy_and_hold": simulate_rebalancing(market, [0.4, 0.4], **common),
        "calendar": simulate_rebalancing(market, [0.4, 0.4], calendar=dates, **common),
        "threshold": simulate_rebalancing(market, [0.4, 0.4], threshold=0.05, **common),
    }
    stock = Stock(0)
    put = EuropeanOption(0, 100, 1, 0.2, kind="put", multiplier=100)
    option_portfolios = {
        "stock": value_portfolio(
            market,
            [Trade(0, stock, 100)],
            initial_cash=20000,
            rate=0.03,
            lending_rate=0.03,
        ),
        "protective_put": value_portfolio(
            market,
            [Trade(0, stock, 100), Trade(0, put, 1)],
            initial_cash=20000,
            rate=0.03,
            lending_rate=0.03,
        ),
    }
    metrics = {
        name: _metrics(r.wealth, r.initial_cash) for name, r in strategies.items()
    }
    for name, result in strategies.items():
        metrics[name]["mean_turnover"] = float(result.turnover.sum(axis=(1, 2)).mean())
        metrics[name]["mean_cost"] = float(result.fees.sum(axis=(1, 2)).mean())
    metrics.update(
        {
            name: _metrics(r.wealth, r.initial_cash)
            for name, r in option_portfolios.items()
        }
    )
    # These examples only have opening buys, so absolute opening trade cashflow
    # is their executed notional turnover (not a generic netted-trade measure).
    for name, option_result in option_portfolios.items():
        metrics[name]["mean_cost"] = float(
            -option_result.fee_cashflows.sum(axis=1).mean()
        )
        metrics[name]["mean_turnover"] = float(
            np.abs(option_result.trade_cashflows[:, 0]).mean()
        )
    snapshots = {
        name: PortfolioSnapshot(
            0,
            (Stock(0), Stock(1)),
            r.quantities[0, 0],
            market.prices[0, 0],
            0.03,
            float(r.cash[0, 0]),
        )
        for name, r in strategies.items()
    }
    snapshots.update(
        {
            name: PortfolioSnapshot(
                0,
                r.instruments,
                r.quantities[0],
                market.prices[0, 0],
                0.03,
                float(r.cash[0, 0]),
            )
            for name, r in option_portfolios.items()
        }
    )
    scenarios = (
        StressScenario("base"),
        StressScenario("crash", -0.2, 0.1, 0.01),
        StressScenario("rates", rate_shock=0.01),
    )
    exposures = {name: portfolio_exposures(snap) for name, snap in snapshots.items()}
    stresses = {
        name: tuple(stress_portfolio(snap, s) for s in scenarios)
        for name, snap in snapshots.items()
    }
    configuration: dict[str, object] = {
        "seed": seed,
        "paths": paths,
        "steps": steps,
        "version": __version__,
        "units": {
            "currency": "EUR",
            "time": "years",
            "rates": "annual decimal continuous",
            "volatility": "annual decimal",
            "threshold": "fraction of wealth",
        },
        "market": {
            "spots": [100, 80],
            "drift": [0.06, 0.04],
            "volatility": [0.2, 0.15],
            "correlation": [[1, 0.4], [0.4, 1]],
            "horizon": 1,
        },
        "strategies": {
            "initial_cash": 20000,
            "weights": [0.4, 0.4],
            "fixed_fee": 1,
            "proportional_fee": 0.001,
            "lending_rate": 0.03,
            "calendar": dates.tolist(),
            "threshold": 0.05,
            "execution": "next grid point; sell then buy in asset order",
        },
        "options": {
            "initial_cash": 20000,
            "stock_shares": 100,
            "put_contracts": 1,
            "strike": 100,
            "maturity": 1,
            "volatility": 0.2,
            "rate": 0.03,
            "dividend_yield": 0,
            "multiplier": 100,
            "lending_rate": 0.03,
            "fees": 0,
        },
        "risk": {
            "confidence": 0.95,
            "loss": "initial capital minus terminal wealth",
            "horizon": 1,
        },
        "snapshot_time": 0,
        "scenarios": [
            {
                "name": s.name,
                "spot_shock": s.spot_shocks,
                "volatility_shock": s.volatility_shocks,
                "rate_shock": s.rate_shock,
            }
            for s in scenarios
        ],
        "stress_grid": {
            "spot_shocks": [-0.3, -0.15, 0, 0.15, 0.3],
            "volatility_shocks": [0, 0.05, 0.1],
        },
        "limitations": (
            "Synthetic GBM/BSM comparisons; numerically verified, "
            "not empirically validated."
        ),
    }
    return RiskLab(
        configuration,
        market,
        strategies,
        option_portfolios,
        metrics,
        snapshots,
        exposures,
        stresses,
    )


def _csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def write_risk_lab(report: RiskLab, output: Path) -> None:
    """Write traceable monetary/relative paths, ledger, exposures and stress values.

    No optional plot imports. Overwrites known files in output, creates directory.
    Summary JSON contains the configuration, units and portfolio risk metrics.
    """
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(
            {"configuration": report.configuration, "metrics": report.metrics},
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    portfolios: dict[str, StrategyPaths | PortfolioPaths] = {}
    portfolios.update(report.strategies)
    portfolios.update(report.option_portfolios)

    def wealth_rows() -> Iterable[Sequence[object]]:
        for name, result in portfolios.items():
            wealth = result.wealth
            dd = drawdown(wealth) if np.all(wealth > 0) else None
            for path in range(wealth.shape[0]):
                for index, time in enumerate(result.times):
                    yield [
                        name,
                        path,
                        float(time),
                        float(wealth[path, index]),
                        float(wealth[path, index] - result.initial_cash),
                        float(wealth[path, index] / result.initial_cash - 1),
                        float(dd[path, index]) if dd is not None else None,
                        float(result.cash[path, index]),
                        float(
                            result.financing[path, index]
                            if isinstance(result, StrategyPaths)
                            else result.financing_cashflows[path, index]
                        ),
                    ]

    _csv(
        output / "wealth.csv",
        [
            "portfolio",
            "path",
            "time_years",
            "wealth",
            "pnl",
            "return",
            "drawdown",
            "cash",
            "financing",
        ],
        wealth_rows(),
    )
    # Profiling 100 paths found 7,800 repeated full-array weight calculations.
    weights_by_name = {name: r.weights for name, r in report.strategies.items()}
    _csv(
        output / "strategy_ledger.csv",
        [
            "portfolio",
            "path",
            "time_years",
            "asset",
            "price",
            "quantity",
            "trade_quantity",
            "fee",
            "turnover",
            "weight",
        ],
        (
            [
                name,
                path,
                float(time),
                asset,
                float(r.prices[path, i, asset]),
                float(r.quantities[path, i, asset]),
                float(r.trades[path, i, asset]),
                float(r.fees[path, i, asset]),
                float(r.turnover[path, i, asset]),
                float(weights_by_name[name][path, i, asset]),
            ]
            for name, r in report.strategies.items()
            for path in range(r.prices.shape[0])
            for i, time in enumerate(r.times)
            for asset in range(r.prices.shape[2])
        ),
    )

    def exposure_rows() -> Iterable[Sequence[object]]:
        for name, e in report.exposures.items():
            snap = report.snapshots[name]
            for i, instrument in enumerate(snap.instruments):
                yield [
                    name,
                    i,
                    str(instrument),
                    float(np.asarray(snap.quantities)[i]),
                    *(
                        float(x[i])
                        for x in (
                            e.position_delta,
                            e.position_gamma,
                            e.position_vega,
                            e.position_theta,
                            e.position_rho,
                            e.position_dv01,
                            e.bond_convexity,
                        )
                    ),
                ]

    _csv(
        output / "exposures.csv",
        [
            "portfolio",
            "position",
            "instrument",
            "quantity",
            "delta",
            "gamma",
            "vega",
            "theta",
            "rho",
            "dv01",
            "bond_convexity",
        ],
        exposure_rows(),
    )
    _csv(
        output / "asset_exposures.csv",
        ["portfolio", "asset", "delta", "gamma"],
        (
            [name, i, float(d), float(e.asset_gamma[i])]
            for name, e in report.exposures.items()
            for i, d in enumerate(e.asset_delta)
        ),
    )
    _csv(
        output / "common_exposures.csv",
        ["portfolio", "common_vol_vega", "parallel_rate_rho", "cash"],
        ([name, e.vega, e.rho, e.cash] for name, e in report.exposures.items()),
    )

    def stress_rows() -> Iterable[Sequence[object]]:
        for name, results in report.stresses.items():
            for r in results:
                for i in range(r.position_pnl.size):
                    yield [
                        name,
                        r.name,
                        i,
                        float(r.base_positions[i]),
                        float(r.stressed_positions[i]),
                        float(r.position_pnl[i]),
                    ]
                yield [name, r.name, "cash", r.cash, r.cash, 0]
                yield [
                    name,
                    r.name,
                    "total",
                    r.base_value,
                    r.stressed_value,
                    r.total_pnl,
                ]

    _csv(
        output / "stress.csv",
        ["portfolio", "scenario", "position", "base_value", "stressed_value", "pnl"],
        stress_rows(),
    )
    ds, dv = [-0.3, -0.15, 0, 0.15, 0.3], [0, 0.05, 0.1]
    grid = stress_grid(report.snapshots["protective_put"], ds, dv)
    _csv(
        output / "stress_grid.csv",
        ["spot_shock", "volatility_shock", "pnl"],
        ([s, v, float(grid[j, i])] for j, v in enumerate(dv) for i, s in enumerate(ds)),
    )


def plot_risk_lab(report: RiskLab, output: Path) -> None:
    """Optional PNG comparisons and Protective Put stress heatmap."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from finance_toolkit.risk_plots import plot_stress_heatmap

    output.mkdir(parents=True, exist_ok=True)
    for filename, portfolios in (
        ("strategies.png", report.strategies),
        ("protective_put.png", report.option_portfolios),
    ):
        figure = Figure(figsize=(9, 5), layout="constrained")
        FigureCanvasAgg(figure)
        axis = figure.subplots()
        for name, result in portfolios.items():
            axis.plot(
                result.times, result.wealth.mean(axis=0), label=name.replace("_", " ")
            )
        axis.set(
            xlabel="Years",
            ylabel="Mean wealth (EUR)",
            title="Synthetic model comparison",
        )
        axis.legend()
        axis.grid(alpha=0.25)
        figure.savefig(output / filename, dpi=150)
    plot_stress_heatmap(
        report.snapshots["protective_put"],
        [-0.3, -0.15, 0, 0.15, 0.3],
        [0, 0.05, 0.1],
        output / "stress.png",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run offline CLI; returns zero on success, no network or system-time input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--paths", type=int, default=1000)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--output", type=Path, default=Path("outputs/m2-demo"))
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args(argv)
    report = build_risk_lab(seed=args.seed, paths=args.paths, steps=args.steps)
    write_risk_lab(report, args.output)
    if args.plot:
        plot_risk_lab(report, args.output)
    print(f"Exported M2 Risk Lab to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
