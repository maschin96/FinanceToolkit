"""Reproducible #65 profiling; call counts/hashes, never a timing test gate."""

import argparse
import cProfile
import hashlib
import json
import platform
import pstats
import sys
import tempfile
from dataclasses import fields
from pathlib import Path

import numpy as np

from finance_toolkit import __version__
from finance_toolkit.attribution import attribute_book
from finance_toolkit.hedge_lab import ComparisonCase, compare_hedges, export_comparison
from finance_toolkit.options_book import Order, simulate_book
from finance_toolkit.portfolio import Stock
from finance_toolkit.simulation import simulate_gbm


def profile(function, *args):
    profiler = cProfile.Profile()
    value = profiler.runcall(function, *args)
    stats = pstats.Stats(profiler)
    counts = {}
    for filename, name in (
        ("options_book.py", "wealth"),
        ("attribution.py", "reconciled"),
        ("_numerics.py", "net_wealth"),
    ):
        counts[name] = sum(
            entry[1]
            for (path, _line, function_name), entry in stats.stats.items()
            if Path(path).name == filename and function_name == name
        )
    return value, dict(seconds=stats.total_tt, calls=counts)


def attribution_hash(result):
    payload = {
        field.name: getattr(result, field.name).tolist()
        if isinstance(getattr(result, field.name), np.ndarray)
        else getattr(result, field.name)
        for field in fields(result)
    }
    payload["reconciled"] = result.reconciled.tolist()
    payload["approximation"] = result.approximation.tolist()
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = dict(
        python=sys.version.split()[0],
        platform=platform.platform(),
        numpy=np.__version__,
        toolkit=__version__,
        steps=16,
        seed=314,
        cases=[],
    )
    for paths in (20, 100, 200):
        market = simulate_gbm(
            100, drift=0.02, volatility=0.2, horizon=1, steps=16, paths=paths, seed=314
        )
        book = simulate_book(
            market, (Stock(),), initial_cash=1000, initial_orders=(Order(0, 1),)
        )
        attribution, stock_profile = profile(attribute_book, book)
        comparison = compare_hedges(
            market, (ComparisonCase("unhedged"),), initial_cash=1000
        )
        with tempfile.TemporaryDirectory(prefix="finance-profile-") as temporary:
            directory = Path(temporary)
            _, export_profile = profile(export_comparison, comparison, directory)
            hashes = {
                file.relative_to(directory).as_posix(): hashlib.sha256(
                    file.read_bytes()
                ).hexdigest()
                for file in sorted(directory.rglob("*"))
                if file.is_file()
            }
        case = dict(
            paths=paths,
            attribution=stock_profile,
            attribution_sha256=attribution_hash(attribution),
            comparison_export=export_profile,
            export_sha256=hashes,
        )
        report["cases"].append(case)
        print(
            json.dumps(
                {
                    "paths": paths,
                    "attribution": stock_profile,
                    "comparison_export": export_profile,
                }
            ),
            flush=True,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
