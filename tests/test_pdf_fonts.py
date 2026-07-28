"""The exported PDF must carry the brand typefaces, not system fallbacks.

Split into two halves deliberately:

* The static checks run everywhere. They assert the template declares the faces
  and that app.pdf hands WeasyPrint a base_url the relative font paths can
  resolve against — the two things whose absence made the first Linux render
  embed DejaVu Serif and Liberation Sans instead of the brand fonts.
* The embedding check needs the real engine and so skips on Windows. Docker
  installs fonts-liberation, so a broken base_url falls back silently in
  production exactly as it did locally; nothing but reading the produced PDF
  catches that.
"""

import re
import sys
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE = Path(__file__).resolve().parent.parent / "app" / "templates" / "scorecard.html"

EXPECTED_FACES = [
    ("Playfair Display", "400", "fonts/playfair-display-latin.woff2"),
    ("Playfair Display", "700", "fonts/playfair-display-latin-700.woff2"),
    ("Playfair Display", "400", "fonts/playfair-display-latin-ext.woff2"),
    ("Playfair Display", "700", "fonts/playfair-display-latin-ext-700.woff2"),
    ("Source Sans 3", "400", "fonts/source-sans-3-latin.woff2"),
    ("Source Sans 3", "600", "fonts/source-sans-3-latin-600.woff2"),
    ("Source Sans 3", "400", "fonts/source-sans-3-latin-ext.woff2"),
    ("Source Sans 3", "600", "fonts/source-sans-3-latin-ext-600.woff2"),
]


class TestFontWiring:
    def test_template_declares_every_expected_face(self):
        css = TEMPLATE.read_text(encoding="utf-8")
        blocks = re.findall(r"@font-face\s*\{(.*?)\}", css, re.S)
        found = set()
        for b in blocks:
            fam = re.search(r"font-family:\s*'([^']+)'", b)
            wt = re.search(r"font-weight:\s*(\d+)", b)
            src = re.search(r"url\('([^']+)'\)", b)
            if fam and wt and src:
                found.add((fam.group(1), wt.group(1), src.group(1)))

        missing = [f for f in EXPECTED_FACES if f not in found]
        assert not missing, f"@font-face missing from the PDF template: {missing}"

    @pytest.mark.parametrize("_family,_weight,relpath", EXPECTED_FACES)
    def test_every_declared_font_file_exists(self, _family, _weight, relpath):
        """A declared face pointing at a missing file fails back to a system font."""
        assert (ASSETS / relpath).is_file(), f"{relpath} declared but not present in assets/"

    def test_base_url_points_at_assets_and_ends_in_a_slash(self):
        """Without the trailing slash urljoin drops the last path component."""
        from app.pdf import _assets_base_url

        url = _assets_base_url()
        assert url.startswith("file://")
        assert url.endswith("/")
        assert url.rstrip("/").endswith("assets")

    def test_a_declared_font_resolves_against_the_base_url(self):
        """Resolve a relative src the way WeasyPrint will, and open the result."""
        from urllib.parse import urljoin
        from urllib.request import url2pathname

        from app.pdf import _assets_base_url

        resolved = urljoin(_assets_base_url(), "fonts/playfair-display-latin-700.woff2")
        path = Path(url2pathname(resolved.replace("file:///", "/").replace("file://", "")))
        if not path.is_file():  # Windows drive-letter form
            path = Path(url2pathname(resolved[len("file:///") :]))
        assert path.is_file(), f"base_url does not resolve to a real font file: {resolved}"
        assert path.read_bytes()[:4] == b"wOF2", "not a woff2 file"

    def test_pdf_and_html_paths_share_one_context(self):
        """Both render paths must go through the same context builder.

        They each held a copy, so a value added to one left the other rendering
        an undefined variable — and only the HTML path is under test.
        """
        source = (Path(__file__).resolve().parent.parent / "app" / "pdf.py").read_text(
            encoding="utf-8"
        )
        assert source.count('"colors": {') == 1, "template context is duplicated again"
        # Call sites only — the `**` excludes the def line.
        assert source.count("**_template_context(data)") == 2


class TestFooterSeparator:
    def test_footer_does_not_use_a_bare_hex_escape(self):
        """A CSS hex escape swallows the space that terminates it.

        "Provisions \\2014 Distribution" rendered as "Provisions —Distribution".
        """
        css = TEMPLATE.read_text(encoding="utf-8")
        footer = re.search(r"@bottom-left\s*\{(.*?)\}", css, re.S).group(1)
        content = re.search(r'content:\s*"([^"]*)"', footer).group(1)
        assert "\\2014" not in content, "use a literal em dash; the escape eats the space"
        assert "—" in content
        assert "Provisions — Distribution" in content


class TestExceptionIdColumn:
    def test_identifier_and_count_columns_do_not_wrap(self):
        """SKU IDs broke at their hyphens into "CHP-" / "SB-003"."""
        html = TEMPLATE.read_text(encoding="utf-8")
        assert re.search(r"td\.nowrap\s*\{[^}]*white-space:\s*nowrap", html, re.S), (
            "no nowrap rule for identifier cells"
        )
        exceptions_table = html[html.find("<!-- Top Exceptions -->") :]
        assert '<td class="nowrap">{{ exc.sku_id }}</td>' in exceptions_table


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="WeasyPrint requires Linux system libraries (GTK, Pango, etc.)",
)
class TestRenderedPdfEmbedsBrandFonts:
    """pdffonts-style check: read the font names out of the produced PDF."""

    def _pdf_bytes(self):
        pytest.importorskip("weasyprint")
        from app.filters import DEFAULT_FILTER_STATE
        from app.pdf import generate_scorecard_pdf
        from app.views.door_count import _fmt_usd_compact, _revenue_at_risk
        from app.views.scorecard import _compute_scorecard_data

        data = _compute_scorecard_data(dict(DEFAULT_FILTER_STATE))
        data["revenue_rate"] = 15
        data["revenue_at_risk"] = _fmt_usd_compact(_revenue_at_risk(data["gap_pairs"], 15))
        return generate_scorecard_pdf(data)

    def test_embeds_playfair_and_source_sans(self):
        pdf = self._pdf_bytes()
        names = b"".join(re.findall(rb"/BaseFont\s*/([^\s/>\]]+)", pdf))
        assert b"Playfair" in names, f"Playfair Display not embedded; fonts were: {names!r}"
        assert b"SourceSans" in names or b"Source" in names, (
            f"Source Sans 3 not embedded; fonts were: {names!r}"
        )

    def test_does_not_fall_back_to_system_fonts(self):
        pdf = self._pdf_bytes()
        names = b"".join(re.findall(rb"/BaseFont\s*/([^\s/>\]]+)", pdf))
        for fallback in (b"DejaVu", b"Liberation", b"Nimbus"):
            assert fallback not in names, (
                f"{fallback.decode()} embedded — brand fonts did not resolve. Fonts: {names!r}"
            )
