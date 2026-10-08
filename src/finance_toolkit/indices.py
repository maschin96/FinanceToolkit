"""Pure numerical fixed-universe price/total-return index calculation."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import ArrayLike, NDArray

from finance_toolkit._validation import finite_array, finite_float


@dataclass(frozen=True)
class IndexPaths:
    """(dates,assets) holdings/weights/contributions; levels/returns (dates,).

    Prices must already be consistently split-adjusted or total-return adjusted
    in one common major currency. Never apply corporate actions again here.
    Synthetic shares of the selected adjusted series, not raw broker holdings.
    """

    dates: tuple[str, ...]
    tickers: tuple[str, ...]
    levels: NDArray[np.float64]
    returns: NDArray[np.float64]
    holdings: NDArray[np.float64]
    weights: NDArray[np.float64]
    contributions: NDArray[np.float64]
    rebalance_executions: tuple[str, ...]


def calculate_index(
    dates: Sequence[str],
    prices: ArrayLike,
    *,
    tickers: Sequence[str],
    base_date: str,
    weights: ArrayLike | None = None,
    base_value: float = 100.0,
    rebalance_dates: Sequence[str] = (),
) -> IndexPaths:
    """Buy-and-hold or fixed weights signalled on dates, effective next session.

    Nonnegative finite weights sum 1 within 1e-12 arithmetic tolerance, then
    normalized; default equal. Sorted distinct ISO sessions; no missing fill.
    Base date must exist. Explicit signal dates within horizon must exist;
    future dates are allowed but never read. Opening index exactly base_value.
    Returns/contributions use beginning shares; rebalance is self financing,
    no costs/FX/taxes, and does not change level at execution.
    """
    labels = tuple(date.fromisoformat(x).isoformat() for x in dates)
    symbols = tuple(x.strip().upper() for x in tickers)
    values = finite_array(prices, "prices").copy()
    base_value = finite_float(base_value, "base_value")
    if (
        not labels
        or any(a >= b for a, b in zip(labels, labels[1:], strict=False))
        or not symbols
        or any(not x for x in symbols)
        or len(set(symbols)) != len(symbols)
        or values.shape != (len(labels), len(symbols))
        or np.any(values <= 0)
        or base_value <= 0
    ):
        raise ValueError(
            "sorted distinct sessions/symbols, positive prices and base required"
        )
    if base_date not in labels:
        raise ValueError("base date must exist in data")
    weights_array = (
        np.full(len(symbols), 1 / len(symbols))
        if weights is None
        else finite_array(weights, "weights").copy()
    )
    if (
        weights_array.shape != (len(symbols),)
        or np.any(weights_array < 0)
        or abs(float(weights_array.sum()) - 1) > 1e-12
    ):
        raise ValueError("nonnegative asset weights must sum to one")
    weights_array /= weights_array.sum()
    signals = tuple(date.fromisoformat(x).isoformat() for x in rebalance_dates)
    if len(set(signals)) != len(signals) or any(
        x < base_date or (x <= labels[-1] and x not in labels) for x in signals
    ):
        raise ValueError("distinct signal dates must match sessions within horizon")
    start = labels.index(base_date)
    labels = labels[start:]
    values = values[start:]
    holdings = np.zeros(values.shape)
    actual_weights = np.zeros(values.shape)
    contributions = np.zeros(values.shape)
    levels = np.zeros(len(labels))
    returns = np.zeros(len(labels))
    executed = []
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            shares = base_value * weights_array / values[0]
            for t, label in enumerate(labels):
                level = float(np.dot(shares, values[t]))
                if t == 0:
                    level = base_value
                else:
                    contributions[t] = (
                        shares * (values[t] - values[t - 1]) / levels[t - 1]
                    )
                    returns[t] = level / levels[t - 1] - 1
                    if labels[t - 1] in signals:
                        shares = level * weights_array / values[t]
                        executed.append(label)
                levels[t] = level
                holdings[t] = shares
                actual_weights[t] = shares * values[t] / level
    except FloatingPointError as error:
        raise ValueError("unrepresentable index calculation") from error
    if not all(
        np.all(np.isfinite(x))
        for x in (levels, returns, holdings, actual_weights, contributions)
    ):
        raise ValueError("unrepresentable index calculation")
    return IndexPaths(
        labels,
        symbols,
        levels,
        returns,
        holdings,
        actual_weights,
        contributions,
        tuple(executed),
    )
