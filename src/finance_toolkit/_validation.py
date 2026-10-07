"""Shared validation for numeric model inputs."""

from numbers import Integral, Real

import numpy as np
from numpy.typing import ArrayLike, NDArray


def finite_array(value: ArrayLike, name: str) -> NDArray[np.float64]:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (ValueError, TypeError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if result.size == 0 or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be nonempty and finite")
    return result


def finite_float(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)
