"""Tests for the centralized calculations module."""

import pytest

from app.calculations import (
    calc_acv_pct,
    calc_penetration_rate,
    calc_period_delta,
    calc_tdp,
    quarter_to_weeks,
    quarters_in_range,
)

# -- quarter_to_weeks --


def test_quarter_to_weeks_q1_returns_13_weeks():
    """Q1 2024 produces 13 weeks from W01 through W13."""
    weeks = quarter_to_weeks("Q1 2024")
    assert len(weeks) == 13
    assert weeks[0] == "2024-W01"
    assert weeks[-1] == "2024-W13"


def test_quarter_to_weeks_q4_returns_w40_to_w52():
    """Q4 2025 produces weeks W40 through W52."""
    weeks = quarter_to_weeks("Q4 2025")
    assert len(weeks) == 13
    assert weeks[0] == "2025-W40"
    assert weeks[-1] == "2025-W52"
    # Verify no overlap with Q3
    assert "2025-W39" not in weeks


def test_quarter_to_weeks_q2_boundaries():
    """Q2 starts at W14 and ends at W26."""
    weeks = quarter_to_weeks("Q2 2025")
    assert len(weeks) == 13
    assert weeks[0] == "2025-W14"
    assert weeks[-1] == "2025-W26"


def test_quarter_to_weeks_q3_boundaries():
    """Q3 starts at W27 and ends at W39."""
    weeks = quarter_to_weeks("Q3 2024")
    assert len(weeks) == 13
    assert weeks[0] == "2024-W27"
    assert weeks[-1] == "2024-W39"


# -- quarters_in_range --


def test_quarters_in_range_full_year():
    """Q1 2025 to Q4 2025 returns exactly 4 quarters."""
    result = quarters_in_range("Q1 2025", "Q4 2025")
    assert len(result) == 4
    assert result == ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]


def test_quarters_in_range_cross_year():
    """Range spanning 2024 and 2025 works correctly."""
    result = quarters_in_range("Q3 2024", "Q2 2025")
    assert len(result) == 4
    assert result[0] == "Q3 2024"
    assert result[-1] == "Q2 2025"


def test_quarters_in_range_single_quarter():
    """Same start and end returns a single-element list."""
    result = quarters_in_range("Q2 2025", "Q2 2025")
    assert result == ["Q2 2025"]


def test_quarters_in_range_invalid_returns_empty():
    """Invalid quarter string returns empty list."""
    result = quarters_in_range("Q1 2030", "Q4 2030")
    assert result == []


def test_quarters_in_range_all_eight():
    """Full 2024-2025 range returns all 8 quarters."""
    result = quarters_in_range("Q1 2024", "Q4 2025")
    assert len(result) == 8


# -- calc_penetration_rate --


def test_penetration_rate_in_range():
    """Penetration rate is between 0 and 1 under default parameters."""
    rate = calc_penetration_rate("Q4 2025")
    assert 0.0 <= rate <= 1.0


def test_penetration_rate_with_retailer_filter():
    """Penetration rate works with a retailer filter applied."""
    rate = calc_penetration_rate("Q4 2025", retailers=["RET-WALMART"])
    assert 0.0 <= rate <= 1.0


def test_penetration_rate_empty_auth_returns_zero():
    """If no authorized items match, penetration is 0."""
    rate = calc_penetration_rate("Q4 2025", retailers=["NONEXISTENT-RETAILER"])
    assert rate == 0.0


def test_penetration_rate_consistent():
    """Calling twice with same params returns same result (deterministic data)."""
    rate1 = calc_penetration_rate("Q4 2025")
    rate2 = calc_penetration_rate("Q4 2025")
    assert rate1 == rate2


# -- calc_acv_pct --


def test_acv_pct_in_range():
    """ACV% is between 0 and 1 under default parameters."""
    acv = calc_acv_pct("Q4 2025")
    assert 0.0 <= acv <= 1.0


def test_acv_pct_with_product_line_filter():
    """ACV% works when filtered to a single product line."""
    acv = calc_acv_pct("Q4 2025", product_lines=["AS"])
    assert 0.0 <= acv <= 1.0


def test_acv_pct_empty_auth_returns_zero():
    """ACV% is 0 when no authorized items match."""
    acv = calc_acv_pct("Q4 2025", retailers=["NONEXISTENT"])
    assert acv == 0.0


# -- calc_tdp --


def test_tdp_positive_value():
    """TDP returns a positive value under default parameters."""
    tdp = calc_tdp("Q4 2025")
    assert tdp > 0.0


def test_tdp_with_single_retailer():
    """TDP works when filtered to a single retailer."""
    tdp = calc_tdp("Q4 2025", retailers=["RET-WALMART"])
    assert tdp > 0.0


def test_tdp_with_product_line_filter():
    """TDP works with product line filter."""
    tdp = calc_tdp("Q4 2025", product_lines=["AS"])
    assert tdp > 0.0


# -- calc_period_delta --


def test_period_delta_positive():
    """Positive delta when current > prior."""
    assert calc_period_delta(0.85, 0.75) == pytest.approx(0.10)


def test_period_delta_negative():
    """Negative delta when current < prior."""
    assert calc_period_delta(0.65, 0.80) == pytest.approx(-0.15)


def test_period_delta_zero():
    """Zero delta when values are equal."""
    assert calc_period_delta(0.5, 0.5) == 0.0


def test_period_delta_none_prior():
    """Returns 0 when prior is None."""
    assert calc_period_delta(0.5, None) == 0.0


def test_period_delta_none_current():
    """Returns 0 when current is None."""
    assert calc_period_delta(None, 0.5) == 0.0


# -- DEMO_AS_OF_DATE consistency --


def test_calculations_use_demo_as_of_date():
    """The data layer uses DEMO_AS_OF_DATE, not wall-clock time."""
    import pandas as pd
    from cinderhaven_store_universe.constants import DEMO_AS_OF_DATE as canonical_date

    assert canonical_date == pd.Timestamp("2025-12-29")


def test_no_wall_clock_time_in_app_source():
    """No app module may read the wall clock for a time-relative computation.

    The synthetic data ends in 2025 while the real clock is past it, so any
    datetime.now()/date.today() silently shifts every silence figure. The test
    above only re-checks a constant inside the data package — it imports nothing
    from app/, so the rule it is named for could be broken without it failing.
    """
    import pathlib
    import re

    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    banned = re.compile(r"\b(?:datetime\.now|date\.today|Timestamp\.now|time\.time)\s*\(")

    offenders = []
    for path in sorted(app_dir.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if banned.search(line):
                offenders.append(f"{path.relative_to(app_dir.parent)}:{lineno}: {line.strip()}")

    assert not offenders, "wall-clock time in app source; use DEMO_AS_OF_DATE:\n" + "\n".join(
        offenders
    )


def test_scorecard_generation_date_is_pinned():
    """The scorecard stamps the demo date, not today's date."""
    from app.filters import DEFAULT_FILTER_STATE
    from app.views.scorecard import _compute_scorecard_data

    data = _compute_scorecard_data(dict(DEFAULT_FILTER_STATE))
    assert data["generation_date"] == "2025-12-29"
