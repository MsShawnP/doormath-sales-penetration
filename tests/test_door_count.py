"""Tests for the Door Count view, shared charts, and shared components."""


# ── charts.py tests ──


def test_economist_layout_returns_expected_keys():
    """economist_layout() returns a dict with all Economist-style layout keys."""
    from app.charts import economist_layout

    layout = economist_layout()
    assert "paper_bgcolor" in layout
    assert "plot_bgcolor" in layout
    assert "font" in layout
    assert "xaxis" in layout
    assert "yaxis" in layout
    assert "margin" in layout
    assert "hoverlabel" in layout
    assert layout["dragmode"] is False
    assert layout["showlegend"] is True


def test_economist_layout_accepts_overrides():
    """economist_layout() merges caller-supplied overrides."""
    from app.charts import economist_layout

    layout = economist_layout(showlegend=False, dragmode="zoom")
    assert layout["showlegend"] is False
    assert layout["dragmode"] == "zoom"


def test_chart_config_disables_mode_bar():
    """CHART_CONFIG disables the Plotly mode bar and enables responsive mode."""
    from app.charts import CHART_CONFIG

    assert CHART_CONFIG["displayModeBar"] is False
    assert CHART_CONFIG["responsive"] is True


# ── components.py tests ──


def test_dark_callout_card_renders():
    """dark_callout_card() returns a Div with the expected structure."""
    from app.components import dark_callout_card

    card = dark_callout_card(
        title="Test Retailer",
        subtitle="10 of 20 doors",
        rows=[
            {"label": "Penetration", "value": "50.0%"},
            {"label": "Items carried", "value": "8"},
        ],
    )
    assert card.className == "dark-callout"
    # Title is first child (h3)
    assert card.children[0].children == "Test Retailer"
    # Subtitle is second child
    assert "10 of 20 doors" in card.children[1].children
    # Two data rows after subtitle
    assert len(card.children) == 4  # title + subtitle + 2 rows


def test_dark_callout_card_minimal():
    """dark_callout_card() works with only a title."""
    from app.components import dark_callout_card

    card = dark_callout_card(title="Minimal")
    assert card.className == "dark-callout"
    assert len(card.children) == 1  # just the title


def test_annotation_callout_renders():
    """annotation_callout() returns a Div with insight-line class."""
    from app.components import annotation_callout

    callout = annotation_callout("Some insight text here.")
    assert callout.className == "insight-line"
    assert callout.children.children == "Some insight text here."


def test_error_banner_renders():
    """error_banner() returns a Div with error-banner class."""
    from app.components import error_banner

    banner = error_banner("Something went wrong")
    assert banner.className == "error-banner"
    assert "Something went wrong" in banner.children[0].children


def test_error_banner_with_retry():
    """error_banner() includes a retry button when retry_id is provided."""
    from app.components import error_banner

    banner = error_banner("Oops", retry_id="retry-btn")
    assert len(banner.children) == 2
    assert banner.children[1].id == "retry-btn"


# ── door_count.py tests ──


def test_door_count_layout_renders():
    """door_count.layout() returns a Div without error."""
    from app.views.door_count import layout

    result = layout()
    assert result is not None
    # Should have children (hero, chart, callout area, annotations, product line chart, store)
    assert len(result.children) >= 5


def test_hero_metric_valid_percentage():
    """Hero metric computes a valid penetration percentage between 0 and 100%."""
    from app.views.door_count import _compute_penetration, _filter_auth

    filters = {
        "retailers": [],
        "product_lines": [],
        "sku": None,
    }
    auth = _filter_auth(filters)
    pct, carrying, addressable = _compute_penetration(auth, ["Q4 2025"])

    assert 0.0 <= pct <= 1.0, f"Penetration {pct} out of [0, 1] range"
    assert carrying >= 0
    assert addressable > 0
    assert carrying <= addressable


def test_retailer_bar_chart_has_correct_groups():
    """Retailer bar chart data has one group per active retailer."""
    from app.calculations import quarters_in_range
    from app.views.door_count import _compute_retailer_bars, _filter_auth

    filters = {
        "retailers": [],
        "product_lines": [],
        "sku": None,
    }
    auth = _filter_auth(filters)
    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    bar_data = _compute_retailer_bars(auth, quarters)

    # Default filters include all 6 retailers
    assert len(bar_data) == 6
    for item in bar_data:
        assert "retailer_name" in item
        assert "authorized_doors" in item
        assert "carrying_doors" in item
        assert item["authorized_doors"] >= item["carrying_doors"]


def test_quarter_to_weeks():
    """Quarter-to-week mapping produces 13 weeks per quarter."""
    from app.calculations import quarter_to_weeks

    q1 = quarter_to_weeks("Q1 2025")
    assert len(q1) == 13
    assert "2025-W01" in q1
    assert "2025-W13" in q1
    assert "2025-W14" not in q1

    q4 = quarter_to_weeks("Q4 2025")
    assert len(q4) == 13
    assert "2025-W40" in q4
    assert "2025-W52" in q4


def test_prior_quarter():
    """_prior_quarter returns the correct preceding quarter."""
    from app.views.door_count import _prior_quarter

    assert _prior_quarter("Q4 2025") == "Q3 2025"
    assert _prior_quarter("Q1 2025") == "Q4 2024"
    assert _prior_quarter("Q1 2024") is None


def test_product_line_chart_data():
    """Product line chart data includes all 5 product lines under default filters."""
    from app.calculations import quarters_in_range
    from app.views.door_count import _compute_product_line_bars, _filter_auth

    filters = {
        "retailers": [],
        "product_lines": [],
        "sku": None,
    }
    auth = _filter_auth(filters)
    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    pl_data = _compute_product_line_bars(auth, quarters)

    # 5 product lines
    assert len(pl_data) == 5


def test_auth_gap_annotations_are_computed():
    """Auth gap annotations produce narrative insights under default filters."""
    from app.views.door_count import _compute_auth_gaps, _filter_auth

    filters = {
        "retailers": [],
        "product_lines": [],
        "sku": None,
    }
    auth = _filter_auth(filters)
    annotations = _compute_auth_gaps(auth, ["Q4 2025"])

    assert isinstance(annotations, list)
    assert len(annotations) >= 1
    for a in annotations:
        assert isinstance(a, str)
