"""Offline, reproducible example portfolios and CSV/JSON/optional PNG exports."""

import argparse
import csv
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike

from finance_toolkit.analytics import analyze_portfolio
from finance_toolkit.instruments.bonds import Bond
from finance_toolkit.portfolio import (
    EuropeanOption,
    PortfolioPaths,
    Stock,
    Trade,
    value_portfolio,
)
from finance_toolkit.simulation import simulate_gbm


def build_examples(
    *,
    seed: int = 42,
    paths: int = 1000,
    rate: float = 0.03,
    maturity: float = 2.0,
    coupon_rate: float = 0.04,
) -> dict[str, PortfolioPaths]:
    """Six portfolios on common seeded monthly GBM paths; initial cash 20,000.

    Stock: 100 shares. Protective put: shares plus one put; covered call:
    shares minus one call, both strike 100 and multiplier 100. Bonds: 100
    face-100 semiannual bonds with constant, rising (+2pp) or falling (-2pp)
    flat curves. Maturity is positive whole half-years; rates continuous annual
    decimals. No dividends, fees or cash reinvestment in these comparisons.
    Invalid inputs propagate model ValueErrors.
    """
    bond = Bond(face=100, coupon_rate=coupon_rate, maturity=maturity, frequency=2)
    market = simulate_gbm(
        100,
        drift=0.06,
        volatility=0.2,
        horizon=bond.maturity,
        steps=round(bond.maturity * 12),
        paths=paths,
        seed=seed,
    )
    stock = Stock()
    put = EuropeanOption(0, 100, bond.maturity, 0.2, kind="put")
    call = EuropeanOption(0, 100, bond.maturity, 0.2, kind="call")
    curves: dict[str, ArrayLike] = {
        "bonds": rate,
        "bonds_rising_rates": np.linspace(rate, rate + 0.02, market.times.size),
        "bonds_falling_rates": np.linspace(rate, rate - 0.02, market.times.size),
    }
    result = {
        "stock": value_portfolio(
            market, [Trade(0, stock, 100)], initial_cash=20_000, rate=rate
        ),
        "protective_put": value_portfolio(
            market,
            [Trade(0, stock, 100), Trade(0, put, 1)],
            initial_cash=20_000,
            rate=rate,
        ),
        "covered_call": value_portfolio(
            market,
            [Trade(0, stock, 100), Trade(0, call, -1)],
            initial_cash=20_000,
            rate=rate,
        ),
    }
    for name, curve in curves.items():
        result[name] = value_portfolio(
            market, [Trade(0, bond, 100)], initial_cash=20_000, rate=curve
        )
    return result


def write_examples(examples: dict[str, PortfolioPaths], output: Path) -> None:
    """Export aggregate wealth/flows, individual wealth paths and risk as CSV/JSON."""
    output.mkdir(parents=True, exist_ok=True)
    flow_names = ("trade", "fee", "coupon", "principal", "option", "financing")
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "scenario",
                "time_years",
                "mean_wealth",
                "median_wealth",
                "p05",
                "p95",
                "mean_cash",
                *(f"mean_{name}_cashflow" for name in flow_names),
            ]
        )
        for name, result in examples.items():
            wealth = result.wealth
            quantiles = np.quantile(wealth, [0.05, 0.5, 0.95], axis=0)
            flow_means = [
                getattr(result, f"{name}_cashflows").mean(axis=0) for name in flow_names
            ]
            for i, time in enumerate(result.times):
                writer.writerow(
                    [
                        name,
                        float(time),
                        float(wealth[:, i].mean()),
                        float(quantiles[1, i]),
                        float(quantiles[0, i]),
                        float(quantiles[2, i]),
                        float(result.cash[:, i].mean()),
                        *(float(flow[i]) for flow in flow_means),
                    ]
                )
            with (output / f"{name}_wealth.csv").open(
                "w", newline="", encoding="utf-8"
            ) as paths_stream:
                paths_writer = csv.writer(paths_stream)
                paths_writer.writerow(["path", *(float(t) for t in result.times)])
                for index, row in enumerate(wealth):
                    paths_writer.writerow([index, *(float(value) for value in row)])
    risks = {
        name: asdict(analyze_portfolio(result).risk)
        for name, result in examples.items()
    }
    (output / "risk.json").write_text(
        json.dumps(risks, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def plot_examples(examples: dict[str, PortfolioPaths], output: Path) -> None:
    """Optional headless Matplotlib adapter: wealth bands and rate comparison PNGs.

    Install the `plots` extra. Missing optional dependency raises RuntimeError.
    """
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
    except ImportError as error:
        raise RuntimeError(
            "Install charts with: uv sync --locked --extra plots"
        ) from error
    output.mkdir(parents=True, exist_ok=True)
    figure = Figure(figsize=(10, 6), layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.subplots(2, 2, sharey=True)
    for axis, name in zip(
        axes.flat, ["stock", "protective_put", "covered_call", "bonds"], strict=True
    ):
        result = examples[name]
        q = np.quantile(result.wealth, [0.05, 0.5, 0.95], axis=0)
        axis.fill_between(
            result.times, q[0], q[2], alpha=0.2, label="5–95% simulated paths"
        )
        axis.plot(result.times, q[1], label="Median wealth")
        axis.set(
            title=name.replace("_", " ").title(),
            xlabel="Years",
            ylabel="Wealth (currency)",
        )
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    figure.savefig(output / "wealth.png", dpi=160)
    rates_figure = Figure(figsize=(9, 5), layout="constrained")
    FigureCanvasAgg(rates_figure)
    axis = rates_figure.subplots()
    for name in ("bonds", "bonds_rising_rates", "bonds_falling_rates"):
        result = examples[name]
        axis.plot(
            result.times, result.wealth.mean(axis=0), label=name.replace("_", " ")
        )
    axis.set(
        title="Bond wealth under rate scenarios",
        xlabel="Years",
        ylabel="Wealth (currency)",
    )
    axis.grid(alpha=0.25)
    axis.legend()
    rates_figure.savefig(output / "bond_rates.png", dpi=160)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline example CLI; returns zero on success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--paths", type=int, default=1000)
    parser.add_argument("--rate", type=float, default=0.03)
    parser.add_argument("--maturity", type=float, default=2.0)
    parser.add_argument("--coupon", type=float, default=0.04)
    parser.add_argument("--output", type=Path, default=Path("outputs/m1-demo"))
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args(argv)
    parameters = dict(
        seed=args.seed,
        paths=args.paths,
        rate=args.rate,
        maturity=args.maturity,
        coupon_rate=args.coupon,
    )
    examples = build_examples(**parameters)
    write_examples(examples, args.output)
    (args.output / "parameters.json").write_text(
        json.dumps(parameters, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    if args.plot:
        plot_examples(examples, args.output)
    print(f"Exported {len(examples)} portfolios to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
