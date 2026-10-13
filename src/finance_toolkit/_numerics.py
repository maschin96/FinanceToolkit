"""Explicit float64 result checks and overflow-safe cash/position aggregation."""

from collections.abc import Iterator
from contextlib import contextmanager
from fractions import Fraction

import numpy as np
from numpy.typing import ArrayLike, NDArray


@contextmanager
def numeric_errors(name: str) -> Iterator[None]:
    """Convert NumPy/Python arithmetic overflow to a named ValueError."""
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            yield
    except (FloatingPointError, OverflowError) as error:
        raise ValueError(f"unrepresentable {name}") from error


def finite_result(value: ArrayLike, name: str) -> NDArray[np.float64]:
    """Check calculated results (including empty arrays), without parameter limits."""
    result = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"unrepresentable {name}")
    return result


def net_wealth(
    cash: NDArray[np.float64], values: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Cash plus signed values on the last axis, in a common currency.

    Preserve ordinary sum rounding, including small cash beside offsetting
    positions. If the sum overflows, retry only those rows by summing the
    exact rational representations of their float64 terms and rounding once.
    Finite representable net values survive oversized gross sums; true final
    overflow/nonfinite inputs raise ValueError. No extended-precision dependency.
    """
    finite_result(cash, "wealth")
    finite_result(values, "wealth")
    # Ignore only the speculative sum overflow; all failed rows are retried
    # below and checked. This avoids changing rounding of unaffected rows.
    with np.errstate(over="ignore", invalid="ignore"):
        result = cash + values.sum(axis=-1)
    failed = ~np.isfinite(result)
    if np.any(failed):
        terms = np.concatenate((values[failed], cash[failed, None]), axis=-1)
        retried = np.empty(terms.shape[0], dtype=np.float64)
        with numeric_errors("wealth"):
            for i, row in enumerate(terms):
                total = sum((Fraction(float(term)) for term in row), Fraction())
                retried[i] = float(total)
        result[failed] = retried
    return finite_result(result, "wealth")
