from __future__ import annotations

from sentinel.stats.disproportionality import compute_ebgm, compute_prr, compute_ror
from sentinel.stats.contingency import build_contingency
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
    assert result["lower_ci"] <= result["estimate"] <= result["upper_ci"]


def test_trend_detects_increase() -> None:
    result = compute_trend([1, 2, 3, 5])
    assert result["slope"] > 0
    assert result["yoy_change"] > 0


def test_contingency_cells_follow_the_margins() -> None:
    table = build_contingency(event_term="NAUSEA", observed=40, n_drug=200, n_event=800, n_total=10000)
    assert table is not None
    assert (table.a, table.b, table.c, table.d) == (40, 160, 760, 9040)
    prr = compute_prr(table.a, table.b, table.c, table.d)
    assert prr["estimate"] == (40 / 200) / (760 / 9800)


def test_contingency_rejects_impossible_margins() -> None:
    assert build_contingency(event_term="NAUSEA", observed=50, n_drug=40, n_event=800, n_total=10000) is None

