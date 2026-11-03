"""PRR, ROR, and the DuMouchel gamma-Poisson posterior.

EBGM here is the geometric mean of the two-gamma posterior in DuMouchel (1999),
equation 11. Hyperparameters are supplied by the caller. This module does not
copy the openEBGM package. An external check can pass the same hyperparameters
and the same (N, E) pairs to that package.
"""

from __future__ import annotations

import math

from scipy.optimize import minimize
from scipy.special import digamma
from scipy.stats import gamma, nbinom

from sentinel.stats.utils import log_ci, safe_divide


# Bounds used by openEBGM's public posterior functions. Staying inside them
# keeps a results check on the same parameter space.
THETA_MIN = (0.25, 0.25, 0.25, 0.25, 1e-5)
THETA_MAX = (10.0, 10.0, 10.0, 10.0, 0.99999)
SPECIFIED_THETA = (0.5, 0.5, 2.0, 2.0, 0.1)


def _chi_square_p_value(chi_square: float) -> float:
    return math.erfc(math.sqrt(max(chi_square, 0.0) / 2.0))


def _chi2_2x2(a: int, b: int, c: int, d: int) -> float:
    total = a + b + c + d
    numerator = total * (a * d - b * c) ** 2
    denominator = (a + b) * (c + d) * (a + c) * (b + d)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _log_se(terms: list[float]) -> float | None:
    if any(term <= 0 for term in terms):
        return None
    return math.sqrt(sum(1.0 / term for term in terms))


def compute_prr(a: int, b: int, c: int, d: int) -> dict[str, float]:
    drug_rate = a / (a + b) if (a + b) else 0.0
    background = c / (c + d) if (c + d) else 0.0
    prr = safe_divide(drug_rate, background)
    chi2 = _chi2_2x2(a, b, c, d)
    p_value = _chi_square_p_value(chi2)
    # SE(log PRR) = sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d)).
    if a <= 0 or (a + b) <= 0 or c <= 0 or (c + d) <= 0:
        lower, upper = prr, prr
    else:
        prr_se = math.sqrt(max(0.0, (1 / a) - (1 / (a + b)) + (1 / c) - (1 / (c + d))))
        lower, upper = log_ci(prr, prr_se)
    return {"estimate": prr, "lower_ci": lower, "upper_ci": upper, "p_value": p_value, "chi_square": chi2}


def compute_ror(a: int, b: int, c: int, d: int) -> dict[str, float]:
    ror = safe_divide(a * d, b * c)
    se = _log_se([a, b, c, d])
    if se is None:
        lower, upper = ror, ror
    else:
        lower, upper = log_ci(ror, se)
    p_value = _chi_square_p_value(_chi2_2x2(a, b, c, d))
    return {"estimate": ror, "lower_ci": lower, "upper_ci": upper, "p_value": p_value}


def bound_theta(theta: tuple[float, float, float, float, float]) -> tuple[float, float, float, float, float]:
    bounded = tuple(min(max(float(value), low), high) for value, low, high in zip(theta, THETA_MIN, THETA_MAX))
    return bounded  # type: ignore[return-value]


def _component_logpmf(observed: int, expected: float, alpha: float, beta: float) -> float:
    prob = beta / (beta + expected) if (beta + expected) else 1.0
    prob = min(max(prob, 1e-10), 1.0 - 1e-10)
    return float(nbinom.logpmf(observed, alpha, prob))


def mixture_weight(
    observed: int,
    expected: float,
    theta: tuple[float, float, float, float, float],
) -> float:
    """Posterior probability that the pair came from the first gamma component."""
    alpha1, beta1, alpha2, beta2, mixture = bound_theta(theta)
    log_first = math.log(mixture) + _component_logpmf(observed, expected, alpha1, beta1)
    log_second = math.log(1.0 - mixture) + _component_logpmf(observed, expected, alpha2, beta2)
    peak = max(log_first, log_second)
    first = math.exp(log_first - peak)
    second = math.exp(log_second - peak)
    total = first + second
    if total <= 0:
        return mixture
    return first / total


def posterior_quantile(
    observed: int,
    expected: float,
    theta: tuple[float, float, float, float, float],
    probability: float,
) -> float:
    alpha1, beta1, alpha2, beta2, _ = bound_theta(theta)
    weight = mixture_weight(observed, expected, theta)

    def cdf(value: float) -> float:
        first = gamma.cdf(value, a=alpha1 + observed, scale=1.0 / (beta1 + expected))
        second = gamma.cdf(value, a=alpha2 + observed, scale=1.0 / (beta2 + expected))
        return weight * float(first) + (1.0 - weight) * float(second)

    low = 0.0
    high = 1.0
    while cdf(high) < probability and high < 1_000_000:
        high *= 2.0
    for _ in range(80):
        mid = (low + high) / 2.0
        if cdf(mid) < probability:
            low = mid
        else:
            high = mid
    return high


def compute_ebgm(
    observed: int,
    expected: float,
    alpha: float | None = None,
    beta: float | None = None,
    theta: tuple[float, float, float, float, float] | None = None,
) -> dict[str, float]:
    """Geometric mean of the posterior, with the 5th and 95th percentiles.

    ``alpha`` and ``beta`` are accepted so older callers still run. They select
    a one-component prior only when ``theta`` is omitted and both are passed.
    The investigation path passes a five-parameter theta.
    """
    if theta is None and alpha is not None and beta is not None:
        theta = (alpha, beta, alpha, beta, 0.99999)
    chosen = bound_theta(theta or SPECIFIED_THETA)
    if expected < 0:
        expected = 0.0
    weight = mixture_weight(observed, expected, chosen)
    alpha1, beta1, alpha2, beta2, _ = chosen
    log_mean = weight * (digamma(alpha1 + observed) - math.log(beta1 + expected))
    log_mean += (1.0 - weight) * (digamma(alpha2 + observed) - math.log(beta2 + expected))
    estimate = math.exp(log_mean)
    lower = posterior_quantile(observed, expected, chosen, 0.05)
    upper = posterior_quantile(observed, expected, chosen, 0.95)
    return {
        "estimate": float(estimate),
        "lower_ci": float(lower),
        "upper_ci": float(upper),
        "qn": float(weight),
    }


def _negative_log_likelihood(
    theta: tuple[float, float, float, float, float],
    pairs: list[tuple[int, float]],
) -> float:
    alpha1, beta1, alpha2, beta2, mixture = bound_theta(tuple(theta))  # type: ignore[arg-type]
    total = 0.0
    for observed, expected in pairs:
        log_first = math.log(mixture) + _component_logpmf(observed, expected, alpha1, beta1)
        log_second = math.log(1.0 - mixture) + _component_logpmf(observed, expected, alpha2, beta2)
        peak = max(log_first, log_second)
        total -= peak + math.log(math.exp(log_first - peak) + math.exp(log_second - peak))
    return total


def fit_hyperparameters(pairs: list[tuple[int, float]]) -> dict[str, object]:
    """Fit the two-gamma prior on the supplied pairs.

    The pairs are the counts retrieved for one product. This is not a fit on
    the full FAERS database.
    """
    usable = [(int(observed), float(expected)) for observed, expected in pairs if observed > 0 and expected > 0]
    note = (
        "Hyperparameters were fit by maximum likelihood on this product's counted "
        "suspect-drug event pairs in the retrieval window. They are not an estimate "
        "from the full FAERS database. Age, sex, and year were not used as strata."
    )
    if len(usable) < 5:
        return {
            "status": "not_estimated",
            "theta": None,
            "pair_count": len(usable),
            "note": "Fewer than five event pairs were available, so EBGM was not estimated.",
        }
    starts = [SPECIFIED_THETA, (1.0, 1.0, 3.0, 3.0, 0.2), (0.25, 0.5, 4.0, 2.0, 0.3)]
    best: tuple[float, tuple[float, float, float, float, float]] | None = None
    for start in starts:
        fitted = minimize(
            _negative_log_likelihood,
            x0=start,
            args=(usable,),
            method="L-BFGS-B",
            bounds=list(zip(THETA_MIN, THETA_MAX)),
        )
        if not fitted.success:
            continue
        theta = bound_theta(tuple(float(value) for value in fitted.x))  # type: ignore[arg-type]
        score = float(fitted.fun)
        if best is None or score < best[0]:
            best = (score, theta)
    if best is None:
        return {
            "status": "not_estimated",
            "theta": None,
            "pair_count": len(usable),
            "note": "The prior did not converge, so EBGM was not estimated.",
        }
    return {
        "status": "fit",
        "theta": list(best[1]),
        "pair_count": len(usable),
        "negative_log_likelihood": best[0],
        "note": note,
    }
