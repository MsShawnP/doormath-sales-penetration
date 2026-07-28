"""Tests for the Exceptions view — data computation, layout, and summary stats."""

from app.views.exceptions import (
    SILENCE_THRESHOLD_WEEKS,
    compute_exceptions,
    compute_summary_stats,
    layout,
    sku_to_item_name,
    sku_to_product_line,
)

# ── Helper name tests ──


class TestSkuHelpers:
    def test_sku_to_item_name_artisan_sauce(self):
        assert sku_to_item_name("CHP-AS-001") == "Roasted Garlic Marinara"

    def test_sku_to_item_name_dried_goods(self):
        assert sku_to_item_name("CHP-DG-003") == "Spiced Lentil Soup Mix"

    def test_sku_to_item_name_snack_bites(self):
        assert sku_to_item_name("CHP-SB-010") == "Honey Chili Pistachios"

    def test_sku_to_product_line(self):
        assert sku_to_product_line("CHP-AS-001") == "Artisan Sauces"

    def test_sku_to_product_line_pantry(self):
        assert sku_to_product_line("CHP-PS-005") == "Pantry Staples"


# ── Layout rendering ──


class TestExceptionsLayout:
    def test_layout_renders_without_error(self):
        """The layout function should return a Dash component tree."""
        result = layout()
        assert result is not None

    def test_layout_has_grid(self):
        """The layout should contain the AG Grid component."""
        result = layout()
        # Walk the children tree to find the grid.
        # Use `is not None` because some Dash components (like dag.AgGrid)
        # evaluate as falsy even though they are valid child nodes.
        found_grid = False
        queue = [result]
        while queue:
            node = queue.pop(0)
            if hasattr(node, "id") and getattr(node, "id", None) == "ex-grid":
                found_grid = True
                break
            children = getattr(node, "children", None)
            if children is not None:
                if isinstance(children, list):
                    queue.extend(children)
                else:
                    queue.append(children)
        assert found_grid, "AG Grid with id='ex-grid' not found in layout"

    def test_layout_has_download_button(self):
        """The layout should contain the CSV download button."""
        result = layout()
        found_btn = False
        queue = [result]
        while queue:
            node = queue.pop(0)
            if hasattr(node, "id") and getattr(node, "id", None) == "ex-download-btn":
                found_btn = True
                break
            children = getattr(node, "children", None)
            if children is not None:
                if isinstance(children, list):
                    queue.extend(children)
                else:
                    queue.append(children)
        assert found_btn, "Download button with id='ex-download-btn' not found in layout"


# ── Exception computation ──


class TestComputeExceptions:
    def test_returns_tuple(self):
        """compute_exceptions should return (list, int)."""
        filters = {
            "retailers": ["RET-WALMART"],
            "product_lines": ["AS"],
            "sku": None,
            "start_quarter": "Q1 2025",
            "end_quarter": "Q4 2025",
        }
        rows, total = compute_exceptions(filters)
        assert isinstance(rows, list)
        assert isinstance(total, int)

    def test_correct_columns(self):
        """Exception rows should have the expected column set."""
        filters = {
            "retailers": ["RET-REGIONAL"],
            "product_lines": ["DG"],
            "sku": None,
            "start_quarter": "Q1 2025",
            "end_quarter": "Q4 2025",
        }
        rows, _ = compute_exceptions(filters)
        # Assert rows exist before checking their shape.  Wrapped in `if rows:`
        # this went silent on exactly the regression it guards against: an empty
        # exceptions list shipped an empty grid and an empty CSV with the whole
        # suite still green.
        assert rows, "expected exceptions for RET-REGIONAL / DG in Q1-Q4 2025"
        expected_cols = {
            "sku_id",
            "item_name",
            "product_line",
            "retailer_name",
            "store_id",
            "region",
            "authorized_date",
            "last_scan_date",
            "weeks_silent",
            "volume_tier",
        }
        assert set(rows[0].keys()) == expected_cols

    def test_all_exceptions_exceed_threshold(self):
        """Every exception row should have weeks_silent > SILENCE_THRESHOLD_WEEKS."""
        filters = {
            "retailers": [],
            "product_lines": [],
            "sku": None,
            "start_quarter": "Q1 2025",
            "end_quarter": "Q4 2025",
        }
        rows, _ = compute_exceptions(filters)
        # Without this the loop below passes vacuously on an empty list.
        assert rows, "expected exceptions across all retailers in Q1-Q4 2025"
        for row in rows:
            assert row["weeks_silent"] > SILENCE_THRESHOLD_WEEKS, (
                f"Row {row['sku_id']}@{row['store_id']} has weeks_silent="
                f"{row['weeks_silent']} which is <= {SILENCE_THRESHOLD_WEEKS}"
            )

    def test_empty_retailers_filter_returns_all(self):
        """Empty retailer list should not restrict — returns all retailers."""
        filters = {
            "retailers": [],
            "product_lines": [],
            "sku": None,
            "start_quarter": "Q1 2025",
            "end_quarter": "Q4 2025",
        }
        rows, total = compute_exceptions(filters)
        # With empty filters, should get exceptions across all data
        assert total > 0

    def test_single_sku_filter(self):
        """Filtering to a single SKU should restrict results."""
        filters_all = {
            "retailers": [],
            "product_lines": ["AS"],
            "sku": None,
            "start_quarter": "Q1 2025",
            "end_quarter": "Q4 2025",
        }
        filters_one = {
            "retailers": [],
            "product_lines": ["AS"],
            "sku": "CHP-AS-001",
            "start_quarter": "Q1 2025",
            "end_quarter": "Q4 2025",
        }
        rows_all, _ = compute_exceptions(filters_all)
        rows_one, _ = compute_exceptions(filters_one)
        # Single SKU should return equal or fewer rows
        assert len(rows_one) <= len(rows_all)
        # And every row for single SKU filter should match that SKU
        for row in rows_one:
            assert row["sku_id"] == "CHP-AS-001"


# ── Summary stats ──


class TestSummaryStats:
    def test_empty_data(self):
        """Empty exception list produces zero stats."""
        stats = compute_summary_stats([], 100)
        assert stats["total_exceptions"] == 0
        assert stats["unique_stores"] == 0
        assert stats["avg_weeks_silent"] == 0
        assert stats["top_retailers"] == []
        assert stats["exception_pct"] == 0.0

    def test_stats_computed_correctly(self):
        """Summary stats should reflect the input data."""
        rows = [
            {
                "sku_id": "CHP-AS-001",
                "store_id": "S1",
                "retailer_name": "Walmart",
                "weeks_silent": 10,
                "item_name": "Artisan Sauce #1",
                "product_line": "AS",
                "region": "West",
                "authorized_date": "2024-W01",
                "last_scan_date": "2025-W42",
                "volume_tier": "A",
            },
            {
                "sku_id": "CHP-AS-002",
                "store_id": "S2",
                "retailer_name": "Walmart",
                "weeks_silent": 20,
                "item_name": "Artisan Sauce #2",
                "product_line": "AS",
                "region": "East",
                "authorized_date": "2024-W01",
                "last_scan_date": "2025-W32",
                "volume_tier": "B",
            },
            {
                "sku_id": "CHP-DG-001",
                "store_id": "S3",
                "retailer_name": "Kroger",
                "weeks_silent": 15,
                "item_name": "Dried Good #1",
                "product_line": "DG",
                "region": "Midwest",
                "authorized_date": "2024-W05",
                "last_scan_date": "2025-W37",
                "volume_tier": "A",
            },
        ]
        stats = compute_summary_stats(rows, 100)
        assert stats["total_exceptions"] == 3
        assert stats["unique_stores"] == 3
        assert stats["avg_weeks_silent"] == 15.0
        assert len(stats["top_retailers"]) == 2
        # Walmart has 2 exceptions, Kroger has 1
        assert stats["top_retailers"][0] == ("Walmart", 2)
        assert stats["top_retailers"][1] == ("Kroger", 1)

    def test_annotation_threshold(self):
        """Exception percentage > 10% should be correctly computed."""
        rows = [
            {
                "sku_id": f"CHP-AS-{i:03d}",
                "store_id": f"S{i}",
                "retailer_name": "R",
                "weeks_silent": 10,
                "item_name": f"Item #{i}",
                "product_line": "AS",
                "region": "W",
                "authorized_date": "2024-W01",
                "last_scan_date": "2025-W42",
                "volume_tier": "A",
            }
            for i in range(1, 12)
        ]
        # 11 exceptions out of 100 authorized = 11%
        stats = compute_summary_stats(rows, 100)
        assert stats["exception_pct"] > 0.10

        # 5 exceptions out of 100 = 5%
        stats_low = compute_summary_stats(rows[:5], 100)
        assert stats_low["exception_pct"] <= 0.10
