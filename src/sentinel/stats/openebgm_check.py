"""Compare a Python EBGM posterior with the installed openEBGM package.

openEBGM is GPL-2 or GPL-3. This module never copies it. When R and the
package are installed, it runs them in a separate process and compares the
returned scores with the Python posterior for the same hyperparameters and
the same counts.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from sentinel.stats.disproportionality import bound_theta, compute_ebgm


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_openebgm.R"


def check_posterior(
    pairs: list[tuple[int, float]],
    theta: tuple[float, float, float, float, float] | list[float] | None,
    *,
    timeout: int = 60,
) -> dict[str, object]:
    if not pairs or theta is None:
        return {"status": "not_run", "detail": "EBGM was not estimated, so openEBGM was not called."}
    if shutil.which("Rscript") is None:
        return {
            "status": "unavailable",
            "detail": "Rscript is not installed. The Python EBGM posterior was not checked against openEBGM.",
        }
    if not SCRIPT.exists():
        return {"status": "unavailable", "detail": "The openEBGM check script is missing."}

    bounded = bound_theta(tuple(float(value) for value in theta))  # type: ignore[arg-type]
    with tempfile.TemporaryDirectory() as directory:
        payload = Path(directory) / "pairs.txt"
        lines = [" ".join(str(value) for value in bounded)]
        lines.extend(f"{int(observed)} {float(expected)}" for observed, expected in pairs)
        payload.write_text("\n".join(lines) + "\n")
        try:
            completed = subprocess.run(
                ["Rscript", str(SCRIPT), str(payload)],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "unavailable", "detail": f"The openEBGM check could not be run: {exc}"}
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "openEBGM check failed.").strip()
        return {"status": "unavailable", "detail": detail}

    reference: list[tuple[float, float, float, float]] = []
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        reference.append(tuple(float(part) for part in parts))  # type: ignore[misc]
    if len(reference) != len(pairs):
        return {"status": "unavailable", "detail": "openEBGM returned a different number of scores than the input pairs."}

    mismatches: list[str] = []
    for (observed, expected), (ebgm, _qn, eb05, eb95) in zip(pairs, reference):
        python_score = compute_ebgm(observed, expected, theta=bounded)
        if abs(python_score["estimate"] - ebgm) > 5e-4:
            mismatches.append(f"EBGM N={observed} E={expected}")
        if abs(python_score["lower_ci"] - eb05) > 5e-3 or abs(python_score["upper_ci"] - eb95) > 5e-3:
            mismatches.append(f"posterior interval N={observed} E={expected}")
    if mismatches:
        return {
            "status": "mismatch",
            "detail": "Python and openEBGM disagreed for: " + ", ".join(mismatches),
            "compared_pairs": len(pairs),
        }
    return {
        "status": "match",
        "detail": "Python EBGM, EB05, and EB95 matched openEBGM for the same hyperparameters and counts.",
        "compared_pairs": len(pairs),
    }
