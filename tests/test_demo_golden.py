"""Demo golden lock + audit-fix regression lock — Door Math.

Door Math's demo renders from the seeded ``cinderhaven_store_universe`` package,
so its demo output is deterministic and pinned here directly. Two audit fixes
(07-31) are regression-locked so they cannot silently return:

1. **ISO-week anchor off-by-one.** DEMO_AS_OF_DATE is 2025-12-29, which ISO-8601
   places in 2026-W01; anchoring there overstated every "weeks silent" by one.
   The anchor is the last completed scan week — 2025-12-22 → 2025-W52. Pinned:
   ``_demo_as_of_week_index() == 202552`` (NOT 202601).
2. **104-week sentinel.** Never-scanned pairs once displayed a flat "104 weeks
   silent"; they now carry weeks-since-authorization (a spread of real values,
   like Void Finder). Pinned: never-scanned weeks_silent is not a constant and
   no row equals the old 104 sentinel.

If any assertion fails, STOP: a demo golden moved. Do not re-baseline without a
logged approval — see the engagement-ready house rules.
"""
from __future__ import annotations

from app.calculations import calc_penetration_rate
from app.views.exceptions import SILENCE_THRESHOLD_WEEKS, _demo_as_of_week_index, compute_exceptions


# ── audit-fix regression locks ──────────────────────────────────────────────

def test_anchor_week_is_2025_W52_not_2026_W01():
    # The off-by-one fix: anchor on the last completed scan week (2025-W52),
    # not the ISO week of DEMO_AS_OF_DATE (2026-W01).
    assert _demo_as_of_week_index() == 202552


def test_never_scanned_use_weeks_since_auth_not_a_flat_sentinel():
    rows, _ = compute_exceptions({})
    never = [r["weeks_silent"] for r in rows if r["last_scan_date"] == "Never"]
    assert never, "expected some never-scanned exception rows"
    # weeks-since-authorization -> a spread of real values, never a flat 104.
    assert len(set(never)) > 1
    assert all(w != 104 for w in never)
    assert max(w for _, w in [(r, r) for r in never]) <= 103


# ── demo golden (deterministic seeded data) ─────────────────────────────────

def test_demo_exception_counts_are_pinned():
    rows, total_authorized = compute_exceptions({})
    assert total_authorized == 21195
    assert len(rows) == 3253
    ws = [r["weeks_silent"] for r in rows]
    assert min(ws) > SILENCE_THRESHOLD_WEEKS   # every exception clears the threshold
    assert max(ws) == 103


def test_demo_penetration_rates_are_pinned():
    assert round(calc_penetration_rate("Q4 2025"), 6) == 0.847087
    assert round(calc_penetration_rate("Q3 2025"), 6) == 0.855532
