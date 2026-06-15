"""Tests for the app shell, layout, and filter bar."""

import json


def test_app_imports():
    """App module imports without error."""
    from app.app import app, server  # noqa: F401

    assert app is not None
    assert server is not None


def test_constants_imports():
    """Constants module imports and exposes palette values."""
    from app.constants import (  # noqa: F401
        CANVAS,
        CHICAGO_20,
        DEMO_AS_OF_DATE,
        FONT_SANS,
        FONT_SERIF,
        HK_35,
        TEAL_SEQUENTIAL,
    )

    assert CANVAS == "#f5f3ee"
    assert len(TEAL_SEQUENTIAL) == 8


def test_health_endpoint():
    """Health endpoint returns 200 with {"status": "ok"}."""
    from wsgi import server  # noqa: F811

    client = server.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == {"status": "ok"}


def test_layout_has_four_tabs():
    """Layout renders all 4 tab labels."""
    from app.app import app
    from app.layout import TAB_LABELS, register_layout

    # register_layout is idempotent if already called via wsgi import
    if app.layout is None:
        register_layout()

    assert len(TAB_LABELS) == 4
    assert TAB_LABELS == ["Door Count", "Trends", "Exceptions", "Scorecard"]

    # Verify the tabs component exists in the layout tree
    layout = app.layout
    _found_tabs = _find_component(layout, "Tabs", "main-tabs")
    assert _found_tabs is not None, "dcc.Tabs with id='main-tabs' not found in layout"


def test_filter_bar_controls():
    """Filter bar has the correct number of filter groups."""
    from app.filters import (
        PRODUCT_LINE_OPTIONS,
        QUARTER_OPTIONS,
        RETAILER_OPTIONS,
        build_filter_bar,
    )

    bar = build_filter_bar()
    # The filter bar has 5 filter groups: retailer, product line, sku, start quarter, end quarter
    filter_groups = [
        child
        for child in bar.children
        if hasattr(child, "className") and "filter-group" in (child.className or "")
    ]
    assert len(filter_groups) == 5

    # Verify option counts
    assert len(RETAILER_OPTIONS) == 6
    assert len(PRODUCT_LINE_OPTIONS) == 5
    assert len(QUARTER_OPTIONS) == 8


def test_default_filter_state():
    """Default filter state has all retailers and product lines selected."""
    from app.filters import ALL_PRODUCT_LINE_PREFIXES, ALL_RETAILER_IDS, DEFAULT_FILTER_STATE

    assert DEFAULT_FILTER_STATE["retailers"] == ALL_RETAILER_IDS
    assert DEFAULT_FILTER_STATE["product_lines"] == ALL_PRODUCT_LINE_PREFIXES
    assert len(DEFAULT_FILTER_STATE["retailers"]) == 6
    assert len(DEFAULT_FILTER_STATE["product_lines"]) == 5
    assert DEFAULT_FILTER_STATE["sku"] is None
    assert DEFAULT_FILTER_STATE["start_quarter"] == "Q1 2025"
    assert DEFAULT_FILTER_STATE["end_quarter"] == "Q4 2025"


def test_format_helpers():
    """Format helpers produce correct output."""
    from app.constants import fmt_delta, fmt_number, fmt_pct

    assert fmt_pct(0.856) == "85.6%"
    assert fmt_pct(0.856, 0) == "86%"
    assert fmt_delta(0.05) == "↑ 5.0 pp"
    assert fmt_delta(-0.03) == "↓ 3.0 pp"
    assert fmt_delta(0) == "→ 0.0 pp"
    assert fmt_number(1234567) == "1,234,567"


# ── Helpers ──


def _find_component(component, type_name, component_id):
    """Recursively search a Dash component tree for a component by type and id."""
    comp_type = type(component).__name__
    if comp_type == type_name and getattr(component, "id", None) == component_id:
        return component

    children = getattr(component, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]

    for child in children:
        if child is None:
            continue
        if hasattr(child, "children") or hasattr(child, "id"):
            found = _find_component(child, type_name, component_id)
            if found:
                return found
    return None
