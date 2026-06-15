"""Tests for PDF generation — template rendering, data dict structure, and color usage."""

import re
import sys

import pytest

from app.filters import DEFAULT_FILTER_STATE
from app.views.scorecard import _compute_scorecard_data


# ── Shared fixture — compute scorecard data once, reuse across tests ──

_CACHED_DATA = None


def _get_scorecard_data():
    """Return scorecard data, computing it only once per test session."""
    global _CACHED_DATA
    if _CACHED_DATA is None:
        _CACHED_DATA = _compute_scorecard_data(DEFAULT_FILTER_STATE)
    return _CACHED_DATA


# ── Data dict construction ──

class TestPdfDataDict:
    def test_data_has_all_required_keys(self):
        """PDF data dict must have every key the template expects."""
        data = _get_scorecard_data()
        required = {
            'hero_pct', 'hero_delta', 'retailer_rows', 'product_line_rows',
            'top_exceptions', 'quarter_label', 'generation_date',
        }
        assert required.issubset(set(data.keys()))

    def test_hero_pct_is_float(self):
        data = _get_scorecard_data()
        assert isinstance(data['hero_pct'], float)

    def test_hero_delta_is_float(self):
        data = _get_scorecard_data()
        assert isinstance(data['hero_delta'], float)

    def test_retailer_rows_is_list_of_dicts(self):
        data = _get_scorecard_data()
        assert isinstance(data['retailer_rows'], list)
        for row in data['retailer_rows']:
            assert isinstance(row, dict)

    def test_product_line_rows_is_list_of_dicts(self):
        data = _get_scorecard_data()
        assert isinstance(data['product_line_rows'], list)
        for row in data['product_line_rows']:
            assert isinstance(row, dict)

    def test_top_exceptions_is_list_of_dicts(self):
        data = _get_scorecard_data()
        assert isinstance(data['top_exceptions'], list)
        for exc in data['top_exceptions']:
            assert isinstance(exc, dict)


# ── Template rendering ──

class TestTemplateRendering:
    def test_template_renders_to_valid_html(self):
        """Jinja2 template renders without error and produces HTML."""
        from app.pdf import render_scorecard_html

        data = _get_scorecard_data()
        html = render_scorecard_html(data)
        assert isinstance(html, str)
        assert len(html) > 0
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html

    def test_template_contains_quarter_label(self):
        """Rendered HTML should include the quarter label."""
        from app.pdf import render_scorecard_html

        data = _get_scorecard_data()
        html = render_scorecard_html(data)
        assert data['quarter_label'] in html

    def test_template_contains_generation_date(self):
        """Rendered HTML should include the generation date."""
        from app.pdf import render_scorecard_html

        data = _get_scorecard_data()
        html = render_scorecard_html(data)
        assert data['generation_date'] in html

    def test_template_contains_retailer_names(self):
        """Rendered HTML should include all retailer names from the data."""
        from app.pdf import render_scorecard_html

        data = _get_scorecard_data()
        html = render_scorecard_html(data)
        for row in data['retailer_rows']:
            assert row['name'] in html, (
                f"Retailer '{row['name']}' not found in rendered HTML"
            )

    def test_template_contains_product_line_names(self):
        """Rendered HTML should include all product line names from the data."""
        from app.pdf import render_scorecard_html

        data = _get_scorecard_data()
        html = render_scorecard_html(data)
        for row in data['product_line_rows']:
            assert row['name'] in html, (
                f"Product line '{row['name']}' not found in rendered HTML"
            )

    def test_template_contains_section_headings(self):
        """Rendered HTML should include all three section headings."""
        from app.pdf import render_scorecard_html

        data = _get_scorecard_data()
        html = render_scorecard_html(data)
        assert 'Retailer Summary' in html
        assert 'Product Line Summary' in html
        assert 'Top Exceptions' in html

    def test_template_contains_cinderhaven_branding(self):
        """Rendered HTML should include brand name."""
        from app.pdf import render_scorecard_html

        data = _get_scorecard_data()
        html = render_scorecard_html(data)
        assert 'Cinderhaven Provisions' in html


# ── Color variable usage ──

class TestTemplateColors:
    """Verify the template uses Jinja2 color variables, not hardcoded hex."""

    def test_no_hardcoded_hex_in_template(self):
        """The template body should use {{ colors.xxx }}, not raw hex values.

        We check the *template source* (not rendered output) for common
        design-system hex values that should come from the colors dict.
        """
        import os

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'app', 'templates', 'scorecard.html',
        )
        with open(template_path, encoding='utf-8') as f:
            source = f.read()

        # These are design-system hex values that must NOT appear as literals
        # in the template — they should be referenced via {{ colors.xxx }}.
        forbidden_literals = [
            '#0d0d0d',   # INK
            '#333333',   # TEXT_PRIMARY
            '#1f2e7a',   # CHICAGO_20
            '#158f75',   # HK_35
            '#b82d4a',   # TOKYO_40
        ]

        # Remove all Jinja2 {{ ... }} expressions before checking
        stripped = re.sub(r'\{\{.*?\}\}', '', source)

        for hex_val in forbidden_literals:
            occurrences = [
                m for m in re.finditer(re.escape(hex_val), stripped, re.IGNORECASE)
            ]
            assert len(occurrences) == 0, (
                f"Hardcoded hex {hex_val} found in template (should use "
                f"{{{{ colors.xxx }}}})"
            )


# ── WeasyPrint import check ──

class TestWeasyPrint:
    @pytest.mark.skipif(
        sys.platform == 'win32',
        reason='WeasyPrint requires Linux system libraries (GTK, Pango, etc.)',
    )
    def test_weasyprint_importable(self):
        """WeasyPrint should be importable on Linux/macOS environments."""
        wp = pytest.importorskip('weasyprint')
        assert hasattr(wp, 'HTML')

    @pytest.mark.skipif(
        sys.platform == 'win32',
        reason='WeasyPrint requires Linux system libraries',
    )
    def test_pdf_generation_produces_bytes(self):
        """Full PDF generation should produce bytes output."""
        pytest.importorskip('weasyprint')
        from app.pdf import generate_scorecard_pdf

        data = _get_scorecard_data()
        pdf_bytes = generate_scorecard_pdf(data)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:5] == b'%PDF-'

    def test_missing_weasyprint_raises_runtime_error(self):
        """If WeasyPrint is not usable, generate_scorecard_pdf raises RuntimeError.

        WeasyPrint can fail with ImportError (not installed) or OSError
        (installed but system libraries like GTK/Pango are missing, which
        is common on Windows).  Both should produce a clean RuntimeError.
        """
        # Check if WeasyPrint is fully functional (not just pip-installed)
        try:
            from weasyprint import HTML  # noqa: F401
            pytest.skip('WeasyPrint is fully functional; cannot test missing-import path')
        except (ImportError, OSError):
            pass

        from app.pdf import generate_scorecard_pdf

        data = _get_scorecard_data()
        with pytest.raises(RuntimeError, match='WeasyPrint is not available'):
            generate_scorecard_pdf(data)
