"""Tests for the Scorecard view — layout, data computation, and table structure."""

import json

import pytest

from app.filters import DEFAULT_FILTER_STATE
from app.views.scorecard import (
    _compute_scorecard_data,
    _prior_quarter,
    layout,
)


# ── Shared fixture — compute scorecard data once, reuse across tests ──

_CACHED_DATA = None


def _get_scorecard_data():
    """Return scorecard data, computing it only once per test session."""
    global _CACHED_DATA
    if _CACHED_DATA is None:
        _CACHED_DATA = _compute_scorecard_data(DEFAULT_FILTER_STATE)
    return _CACHED_DATA


# ── Layout rendering ──

class TestScorecardLayout:
    def test_layout_renders_without_error(self):
        """The layout function should return a Dash component tree."""
        result = layout()
        assert result is not None

    def test_layout_has_hero_metric(self):
        """The layout should contain the hero percentage element."""
        result = layout()
        found = _find_component_by_id(result, 'sc-hero-pct')
        assert found, "Hero metric with id='sc-hero-pct' not found in layout"

    def test_layout_has_retailer_table_container(self):
        """The layout should contain the retailer table container."""
        result = layout()
        found = _find_component_by_id(result, 'sc-retailer-table')
        assert found, "Retailer table with id='sc-retailer-table' not found in layout"

    def test_layout_has_product_line_table_container(self):
        """The layout should contain the product line table container."""
        result = layout()
        found = _find_component_by_id(result, 'sc-product-line-table')
        assert found, "Product line table with id='sc-product-line-table' not found"

    def test_layout_has_exceptions_list(self):
        """The layout should contain the exceptions list container."""
        result = layout()
        found = _find_component_by_id(result, 'sc-exceptions-list')
        assert found, "Exceptions list with id='sc-exceptions-list' not found"

    def test_layout_has_download_button(self):
        """The layout should contain the PDF download button."""
        result = layout()
        found = _find_component_by_id(result, 'sc-download-btn')
        assert found, "Download button with id='sc-download-btn' not found"

    def test_layout_has_pdf_download(self):
        """The layout should contain the dcc.Download component."""
        result = layout()
        found = _find_component_by_id(result, 'sc-pdf-download')
        assert found, "dcc.Download with id='sc-pdf-download' not found"


# ── Data computation ──

class TestScorecardData:
    def test_compute_returns_all_keys(self):
        """_compute_scorecard_data returns a dict with all required keys."""
        data = _get_scorecard_data()
        expected_keys = {
            'hero_pct', 'hero_delta', 'retailer_rows', 'product_line_rows',
            'top_exceptions', 'quarter_label', 'generation_date',
        }
        assert set(data.keys()) == expected_keys

    def test_hero_metric_valid_percentage(self):
        """Hero metric is a valid percentage between 0 and 1."""
        data = _get_scorecard_data()
        assert 0.0 <= data['hero_pct'] <= 1.0, (
            f"Hero percentage {data['hero_pct']} out of [0, 1] range"
        )

    def test_retailer_table_has_six_rows(self):
        """Retailer table should have 6 rows (one per retailer)."""
        data = _get_scorecard_data()
        assert len(data['retailer_rows']) == 6

    def test_retailer_rows_have_required_keys(self):
        """Each retailer row has the expected key set."""
        data = _get_scorecard_data()
        expected = {'name', 'carrying', 'addressable', 'penetration',
                    'acv_pct', 'tdp', 'delta'}
        for row in data['retailer_rows']:
            assert set(row.keys()) == expected, (
                f"Row for {row.get('name', '?')} missing keys: "
                f"{expected - set(row.keys())}"
            )

    def test_product_line_table_has_five_rows(self):
        """Product line table should have 5 rows (one per product line)."""
        data = _get_scorecard_data()
        assert len(data['product_line_rows']) == 5

    def test_product_line_rows_have_required_keys(self):
        """Each product line row has the expected key set."""
        data = _get_scorecard_data()
        expected = {'name', 'carrying', 'addressable', 'penetration',
                    'acv_pct', 'delta'}
        for row in data['product_line_rows']:
            assert set(row.keys()) == expected, (
                f"Row for {row.get('name', '?')} missing keys: "
                f"{expected - set(row.keys())}"
            )

    def test_top_exceptions_max_count(self):
        """Top exceptions list has at most 10 items."""
        data = _get_scorecard_data()
        assert len(data['top_exceptions']) <= 10

    def test_top_exceptions_have_required_keys(self):
        """Each exception row has sku_id, item_name, retailer, weeks_silent."""
        data = _get_scorecard_data()
        expected = {'sku_id', 'item_name', 'retailer', 'weeks_silent'}
        for exc in data['top_exceptions']:
            assert set(exc.keys()) == expected

    def test_quarter_label_matches_filter(self):
        """Quarter label should match the end quarter from filters."""
        data = _get_scorecard_data()
        assert data['quarter_label'] == DEFAULT_FILTER_STATE['end_quarter']

    def test_generation_date_is_string(self):
        """Generation date should be a formatted date string."""
        data = _get_scorecard_data()
        assert isinstance(data['generation_date'], str)
        assert len(data['generation_date']) == 10  # YYYY-MM-DD

    def test_filter_restricts_retailers(self):
        """Filtering to a single retailer should produce 1 retailer row."""
        filters = {
            **DEFAULT_FILTER_STATE,
            'retailers': ['RET-WALMART'],
        }
        data = _compute_scorecard_data(filters)
        assert len(data['retailer_rows']) == 1
        assert data['retailer_rows'][0]['name'] == 'Walmart'

    def test_filter_restricts_product_lines(self):
        """Filtering to one product line should produce 1 product line row."""
        filters = {
            **DEFAULT_FILTER_STATE,
            'product_lines': ['AS'],
        }
        data = _compute_scorecard_data(filters)
        assert len(data['product_line_rows']) == 1
        assert data['product_line_rows'][0]['name'] == 'Artisan Sauces'


# ── Quarter helper ──

class TestPriorQuarter:
    def test_q4_returns_q3(self):
        assert _prior_quarter('Q4 2025') == 'Q3 2025'

    def test_q1_2025_returns_q4_2024(self):
        assert _prior_quarter('Q1 2025') == 'Q4 2024'

    def test_q1_2024_returns_none(self):
        assert _prior_quarter('Q1 2024') is None

    def test_invalid_quarter_returns_none(self):
        assert _prior_quarter('Q1 2030') is None


# ── Helpers ──

def _find_component_by_id(component, target_id):
    """Walk the Dash component tree to find a component by id."""
    queue = [component]
    while queue:
        node = queue.pop(0)
        if hasattr(node, 'id') and getattr(node, 'id', None) == target_id:
            return True
        children = getattr(node, 'children', None)
        if children is not None:
            if isinstance(children, list):
                queue.extend(c for c in children if c is not None)
            elif children is not None:
                queue.append(children)
    return False
