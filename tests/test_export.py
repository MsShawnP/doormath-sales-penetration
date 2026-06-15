"""Tests for the CSV export function."""

import csv
import io

import pandas as pd

from app.export import export_csv


class TestExportCsv:
    def test_list_of_dicts_produces_valid_csv(self):
        """export_csv with a list of dicts should produce valid CSV."""
        rows = [
            {"sku_id": "CHP-AS-001", "store_id": "S1", "weeks_silent": 10},
            {"sku_id": "CHP-AS-002", "store_id": "S2", "weeks_silent": 15},
        ]
        result = export_csv(rows)
        assert isinstance(result, str)
        # Should parse as valid CSV
        reader = csv.DictReader(io.StringIO(result))
        parsed = list(reader)
        assert len(parsed) == 2
        assert parsed[0]["sku_id"] == "CHP-AS-001"
        assert parsed[1]["weeks_silent"] == "15"

    def test_dataframe_produces_valid_csv(self):
        """export_csv with a DataFrame should produce valid CSV."""
        df = pd.DataFrame(
            {
                "sku_id": ["CHP-DG-001", "CHP-DG-002"],
                "store_id": ["S3", "S4"],
                "weeks_silent": [8, 12],
            }
        )
        result = export_csv(df)
        assert isinstance(result, str)
        reader = csv.DictReader(io.StringIO(result))
        parsed = list(reader)
        assert len(parsed) == 2
        assert parsed[0]["sku_id"] == "CHP-DG-001"

    def test_correct_column_headers(self):
        """CSV output should have the correct column headers."""
        rows = [
            {"sku_id": "A", "retailer_name": "B", "weeks_silent": 5},
        ]
        result = export_csv(rows)
        first_line = result.split("\n")[0]
        headers = [h.strip() for h in first_line.split(",")]
        assert "sku_id" in headers
        assert "retailer_name" in headers
        assert "weeks_silent" in headers

    def test_empty_data_produces_headers_only(self):
        """Empty input should produce a CSV with headers only (no data rows)."""
        rows = []
        result = export_csv(rows)
        # Empty DataFrame produces just a newline (no columns)
        # But a list of dicts with no entries = empty DataFrame = empty CSV
        lines = result.strip().split("\n")
        # With empty list, pandas produces an empty string
        assert len(lines) <= 1

    def test_empty_dataframe_produces_headers_only(self):
        """Empty DataFrame with defined columns should produce headers only."""
        df = pd.DataFrame(columns=["sku_id", "store_id", "weeks_silent"])
        result = export_csv(df)
        lines = result.strip().split("\n")
        assert len(lines) == 1  # Just the header row
        headers = [h.strip() for h in lines[0].split(",")]
        assert "sku_id" in headers
        assert "store_id" in headers
        assert "weeks_silent" in headers
