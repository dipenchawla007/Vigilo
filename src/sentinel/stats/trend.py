from __future__ import annotations

import math
from typing import Sequence


def compute_trend(values: Sequence[float]) -> dict[str, float]:
    if len(values) < 2:
        return {"slope": 0.0, "p_value": 1.0, "yoy_change": 0.0, "r_value": 0.0}
    n = len(values)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(values) / n
    sxx = sum((xi - x_mean) ** 2 for xi in x)
    syy = sum((yi - y_mean) ** 2 for yi in values)
    sxy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
    slope = sxy / sxx if sxx else 0.0
    r_value = sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0
    first = values[0] if values[0] else 1.0
    yoy_change = (values[-1] - values[0]) / first
    p_value = max(0.0, min(1.0, 1.0 - abs(r_value))) if n > 2 else 1.0
    return {
        "slope": float(slope),
        "p_value": float(p_value),
        "yoy_change": float(yoy_change),
        "r_value": float(r_value),
    }
