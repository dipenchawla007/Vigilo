from __future__ import annotations

import math


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def log_ci(estimate: float, se: float, z: float = 1.96) -> tuple[float, float]:
    if estimate <= 0:
        return 0.0, 0.0
    lower = math.exp(math.log(estimate) - z * se)
    upper = math.exp(math.log(estimate) + z * se)
    return lower, upper

