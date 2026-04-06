from __future__ import annotations

from sentinel.stats.disproportionality import compute_ebgm, compute_prr, compute_ror
from sentinel.stats.trend import compute_trend


def test_prr_returns_positive_estimate() -> None:
    result = compute_prr(12, 88, 10, 190)
    assert result["estimate"] > 1
    assert 0 <= result["p_value"] <= 1


def test_ror_returns_confidence_interval() -> None:
    result = compute_ror(8, 12, 4, 20)
    assert result["lower_ci"] <= result["estimate"] <= result["upper_ci"]


def test_ebgm_returns_nonnegative_values() -> None:
    result = compute_ebgm(10, expected=4.5)
    assert result["estimate"] > 0
    assert result["lower_ci"] >= 0


def test_trend_detects_increase() -> None:
    result = compute_trend([1, 2, 3, 5])
    assert result["slope"] > 0
    assert result["yoy_change"] > 0

