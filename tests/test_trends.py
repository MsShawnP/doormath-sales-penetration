"""Tests for the Trends view -- ACV% and TDP line charts."""

from cinderhaven_store_universe.constants import RETAILERS

from app.filters import DEFAULT_FILTER_STATE

# -- Layout --


def test_trends_layout_renders():
    """trends.layout() returns a Div without error."""
    from app.views.trends import layout

    result = layout()
    assert result is not None
    # Should have children: chart row, callout area, annotations, 2 stores
    assert len(result.children) >= 4


def test_trends_layout_has_chart_ids():
    """Layout contains the ACV and TDP chart graph components."""
    from app.views.trends import layout

    result = layout()
    all_text = str(result)
    assert "tr-acv-chart" in all_text
    assert "tr-tdp-chart" in all_text


def test_trends_layout_has_aria_labels():
    """Chart containers have aria-label attributes for accessibility."""
    from app.views.trends import layout

    result = layout()
    all_text = str(result)
    assert "ACV" in all_text
    assert "TDP" in all_text


# -- ACV chart traces --


def test_acv_chart_has_correct_trace_count():
    """ACV% chart has one trace per retailer plus a median reference line."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_acv_chart, _compute_acv_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    acv_data = _compute_acv_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_acv_chart(acv_data, quarters)

    # 6 retailers + 1 median = 7 traces
    n_retailers = len(DEFAULT_FILTER_STATE["retailers"])
    expected_traces = n_retailers + 1  # +1 for median
    assert len(fig.data) == expected_traces


def test_acv_chart_median_is_dashed():
    """The median reference line uses a dashed style."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_acv_chart, _compute_acv_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    acv_data = _compute_acv_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_acv_chart(acv_data, quarters)

    # First trace is the median
    median_trace = fig.data[0]
    assert median_trace.name == "Median"
    assert median_trace.line.dash == "dash"


def test_acv_chart_values_are_percentages():
    """ACV% chart y-values are in percentage scale (0-100 range)."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_acv_chart, _compute_acv_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    acv_data = _compute_acv_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_acv_chart(acv_data, quarters)

    # Check non-median traces have values in 0-100 range
    for trace in fig.data[1:]:
        for y_val in trace.y:
            assert 0 <= y_val <= 100, f"ACV% value {y_val} outside 0-100 range"


# -- TDP chart traces --


def test_tdp_chart_has_correct_trace_count():
    """TDP chart has one trace per retailer plus a median reference line."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_tdp_chart, _compute_tdp_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    tdp_data = _compute_tdp_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_tdp_chart(tdp_data, quarters)

    n_retailers = len(DEFAULT_FILTER_STATE["retailers"])
    expected_traces = n_retailers + 1  # +1 for median
    assert len(fig.data) == expected_traces


def test_tdp_chart_values_are_positive():
    """TDP chart y-values are non-negative."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_tdp_chart, _compute_tdp_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    tdp_data = _compute_tdp_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_tdp_chart(tdp_data, quarters)

    for trace in fig.data[1:]:
        for y_val in trace.y:
            assert y_val >= 0, f"TDP value {y_val} should not be negative"


# -- Per-point text labels --


def test_acv_chart_every_point_has_a_text_label():
    """Every trace on the ACV% chart (median + each retailer) labels every point,
    not just the endpoint."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_acv_chart, _compute_acv_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    acv_data = _compute_acv_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_acv_chart(acv_data, quarters)

    for trace in fig.data:
        assert "text" in trace.mode, f"{trace.name} mode {trace.mode} does not render text"
        assert trace.text is not None
        assert len(trace.text) == len(quarters)
        assert all(t for t in trace.text), f"{trace.name} has an empty label somewhere"


def test_tdp_chart_every_point_has_a_text_label():
    """Every trace on the TDP chart (median + each retailer) labels every point,
    not just the endpoint."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_tdp_chart, _compute_tdp_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    tdp_data = _compute_tdp_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_tdp_chart(tdp_data, quarters)

    for trace in fig.data:
        assert "text" in trace.mode, f"{trace.name} mode {trace.mode} does not render text"
        assert trace.text is not None
        assert len(trace.text) == len(quarters)
        assert all(t for t in trace.text), f"{trace.name} has an empty label somewhere"


# -- Y-axis range --


def test_acv_chart_y_axis_starts_at_zero():
    """ACV% chart y-axis range always starts at 0, regardless of data range."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_acv_chart, _compute_acv_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    acv_data = _compute_acv_by_retailer(DEFAULT_FILTER_STATE, quarters)
    fig = _build_acv_chart(acv_data, quarters)

    assert fig.layout.yaxis.range[0] == 0


# -- Footnotes --


def test_trends_layout_has_chart_footnotes():
    """Trends layout includes a source/methodology footnote below each chart."""
    from app.views.trends import layout

    result = layout()
    all_text = str(result)
    assert "chart-footnote" in all_text
    assert all_text.count("Source: Cinderhaven") == 2


# -- Filter changes --


def test_single_retailer_filter_produces_two_traces():
    """Filtering to one retailer produces 2 traces (1 retailer + 1 median)."""
    from app.calculations import quarters_in_range
    from app.views.trends import _build_acv_chart, _compute_acv_by_retailer

    filters = {
        "retailers": ["RET-WALMART"],
        "product_lines": ["AS", "PS", "SC", "DG", "SB"],
        "sku": None,
        "start_quarter": "Q1 2025",
        "end_quarter": "Q4 2025",
    }
    quarters = quarters_in_range("Q1 2025", "Q4 2025")
    acv_data = _compute_acv_by_retailer(filters, quarters)
    fig = _build_acv_chart(acv_data, quarters)

    assert len(fig.data) == 2  # 1 retailer + 1 median


def test_product_line_filter_changes_tdp():
    """Filtering to fewer product lines reduces TDP since TDP sums per-SKU ACV%."""
    from app.calculations import quarters_in_range
    from app.views.trends import _compute_tdp_by_retailer

    quarters = quarters_in_range("Q1 2025", "Q4 2025")

    all_pl = _compute_tdp_by_retailer(DEFAULT_FILTER_STATE, quarters)

    single_pl_filters = {
        **DEFAULT_FILTER_STATE,
        "product_lines": ["AS"],
    }
    single_pl = _compute_tdp_by_retailer(single_pl_filters, quarters)

    # With fewer product lines (1 of 5), TDP should be lower for at least some retailers
    # since TDP sums ACV% across fewer SKUs
    any_lower = False
    for ret_id in all_pl:
        if ret_id in single_pl:
            for q in quarters:
                if all_pl[ret_id][q] > single_pl[ret_id][q] + 0.01:
                    any_lower = True
                    break
    assert any_lower, "Filtering to one product line should reduce TDP"


# -- Slow-leak annotations --


def test_slow_leak_annotations_with_full_range():
    """Slow-leak annotations detect CHP-DG-003 decline across the full quarter range."""
    from app.calculations import quarters_in_range
    from app.views.trends import _compute_slow_leak_annotations

    # Use full 2024-2025 range to capture the leak story
    quarters = quarters_in_range("Q1 2024", "Q4 2025")

    filters = {
        "retailers": list(RETAILERS.keys()),
        "product_lines": ["AS", "PS", "SC", "DG", "SB"],
        "sku": None,
        "start_quarter": "Q1 2024",
        "end_quarter": "Q4 2025",
    }
    annotations = _compute_slow_leak_annotations(filters, quarters)
    assert isinstance(annotations, list)

    # Slow-leak SKUs should produce structured stat card data
    assert len(annotations) >= 1
    for c in annotations:
        assert isinstance(c, dict)
        assert "value" in c
        assert "label" in c
        assert "doors lost" in c["label"]


def test_slow_leak_filtered_out_by_product_line():
    """Slow-leak annotations are suppressed when the product line is filtered out."""
    from app.calculations import quarters_in_range
    from app.views.trends import _compute_slow_leak_annotations

    quarters = quarters_in_range("Q1 2024", "Q4 2025")

    # Filter to only Artisan Sauces -- should not see DG or SC leak annotations
    filters = {
        "retailers": list(RETAILERS.keys()),
        "product_lines": ["AS"],
        "sku": None,
        "start_quarter": "Q1 2024",
        "end_quarter": "Q4 2025",
    }
    annotations = _compute_slow_leak_annotations(filters, quarters)
    for c in annotations:
        label = c.get("label", "")
        assert "CHP-DG-003" not in label, "DG leak should be filtered out"
        assert "CHP-SC-007" not in label, "SC leak should be filtered out"


# -- Retailer color assignment --


def test_retailer_colors_are_unique():
    """Each retailer gets a unique teal color."""
    from app.views.trends import RETAILER_COLORS

    colors = list(RETAILER_COLORS.values())
    assert len(colors) == len(set(colors)), "Retailer colors should be unique"


def test_retailer_colors_from_design_system():
    """All retailer colors come from the categorical paired palette."""
    from app.constants import CATEGORICAL_6
    from app.views.trends import RETAILER_COLORS

    allowed = set(CATEGORICAL_6)
    for color in RETAILER_COLORS.values():
        assert color in allowed, f"Color {color} not in categorical palette"
