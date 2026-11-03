"""FAERS report counts arranged as a drug-event contingency table.

Case definition
---------------
Counts are openFDA FAERS report totals, not patient totals. A report is counted
for the drug only when the search matches the drug's generic name and the
suspect drug role. The event is one MedDRA preferred term. The window is the
report received date over the requested number of years.

Cells
-----
a = suspect-drug reports that also contain the event
n_drug = suspect-drug reports
n_event = all reports that contain the event
N = all reports in the window
b = n_drug - a
c = n_event - a
d = N - n_drug - n_event + a

The expected count under independence is n_drug * n_event / N. That expected
count is the E used for the relative reporting ratio and for EBGM. PRR and ROR
use the four cells directly.

openFDA can match nested drug fields on different drug objects in the same
report, so the suspect role and the drug name are not guaranteed to describe
the same drug entry. Reports are not deduplicated beyond the openFDA index.
Age, sex, and year are not used as strata. A report can contribute to more
than one event term; within one term the count is still a report count.
"""

from __future__ import annotations

from dataclasses import dataclass


CASE_DEFINITION = __doc__.strip()


@dataclass(frozen=True)
class ContingencyTable:
    event_term: str
    a: int
    b: int
    c: int
    d: int
    n_drug: int
    n_event: int
    n_total: int
    expected: float

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "event_term": self.event_term,
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "d": self.d,
            "n_drug": self.n_drug,
            "n_event": self.n_event,
            "n_total": self.n_total,
            "expected": self.expected,
        }


def build_contingency(
    *,
    event_term: str,
    observed: int,
    n_drug: int,
    n_event: int,
    n_total: int,
) -> ContingencyTable | None:
    """Return the four cells, or None when the margins cannot form a table."""
    if min(observed, n_drug, n_event, n_total) < 0:
        return None
    if observed > n_drug or observed > n_event:
        return None
    if n_drug > n_total or n_event > n_total:
        return None
    b = n_drug - observed
    c = n_event - observed
    d = n_total - n_drug - n_event + observed
    if d < 0:
        return None
    expected = (n_drug * n_event) / n_total if n_total else 0.0
    return ContingencyTable(
        event_term=event_term,
        a=observed,
        b=b,
        c=c,
        d=d,
        n_drug=n_drug,
        n_event=n_event,
        n_total=n_total,
        expected=expected,
    )
