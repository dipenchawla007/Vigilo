from __future__ import annotations

import shutil

from sentinel.stats.openebgm_check import check_posterior


def test_openebgm_check_reports_when_rscript_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    result = check_posterior([(10, 4.5)], (0.5, 0.5, 2.0, 2.0, 0.1))
    assert result["status"] == "unavailable"
    assert "Rscript" in str(result["detail"])
