from __future__ import annotations

import math

from sentinel.stats.utils import log_ci, safe_divide


def _chi_square_p_value(chi_square: float) -> float:
    # Survival function for chi-square with 1 degree of freedom.
    return math.erfc(math.sqrt(max(chi_square, 0.0) / 2.0))


def _chi2_2x2(a: int, b: int, c: int, d: int) -> float:
    total = a + b + c + d
    numerator = total * (a * d - b * c) ** 2
    denominator = max((a + b) * (c + d) * (a + c) * (b + d), 1)
    return numerator / denominator


def compute_prr(a: int, b: int, c: int, d: int) -> dict[str, float]:
    prr = safe_divide(a / max(a + b, 1), c / max(c + d, 1))
    chi2 = _chi2_2x2(a, b, c, d)
    p_value = _chi_square_p_value(chi2)
    se = math.sqrt(max(0.0, (1 / max(a, 1)) - (1 / max(a + b, 1)) + (1 / max(c, 1)) - (1 / max(c + d, 1))))
    lower, upper = log_ci(prr, se)
    return {"estimate": prr, "lower_ci": lower, "upper_ci": upper, "p_value": p_value, "chi_square": chi2}


def compute_ror(a: int, b: int, c: int, d: int) -> dict[str, float]:
    ror = safe_divide(a * d, max(b * c, 1))
    se = math.sqrt(sum(1 / max(x, 1) for x in [a, b, c, d]))
    lower, upper = log_ci(ror, se)
    p_value = _chi_square_p_value(_chi2_2x2(a, b, c, d))
    return {"estimate": ror, "lower_ci": lower, "upper_ci": upper, "p_value": p_value}


def compute_ebgm(observed: int, expected: float, alpha: float = 1.0, beta: float = 1.0) -> dict[str, float]:
    posterior_mean = (observed + alpha) / max(expected + beta, 1e-9)
    variance = (observed + alpha) / max((expected + beta) ** 2, 1e-9)
    se = math.sqrt(variance)
    lower, upper = max(posterior_mean - 1.96 * se, 0.0), posterior_mean + 1.96 * se
    return {"estimate": posterior_mean, "lower_ci": lower, "upper_ci": upper}
