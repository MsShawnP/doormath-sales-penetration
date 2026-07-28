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


class TestFontFilesAreTheWeightTheyClaim:
    """Guard against shipping a font file whose outlines are the wrong weight.

    This has bitten twice. c60a37b found the bold face was a byte-copy of the
    regular. Then source-sans-3-latin.woff2 and -latin-ext.woff2 turned out to
    be ExtraLight (usWeightClass 200) while declared font-weight: 400 — so all
    body text, in the PDF and on screen and on every site using this frame,
    rendered a weight too light. Nothing declared it; both files looked fine by
    name.

    Runs everywhere: needs fontTools, not WeasyPrint.
    """

    @staticmethod
    def _face(relpath):
        from fontTools.ttLib import TTFont

        return TTFont(ASSETS / relpath, fontNumber=0)

    @pytest.mark.parametrize("_family,weight,relpath", EXPECTED_FACES)
    def test_file_weight_matches_the_declaration(self, _family, weight, relpath):
        actual = self._face(relpath)["OS/2"].usWeightClass
        assert actual == int(weight), (
            f"{relpath} declares font-weight {weight} but its usWeightClass is "
            f"{actual} — the outlines are the wrong weight"
        )

    def test_weights_within_a_family_are_distinct_files(self):
        """A heavier face that is a copy of the lighter one renders identically."""
        import hashlib

        outlines = {}
        for _family, weight, relpath in EXPECTED_FACES:
            font = self._face(relpath)
            tag = "glyf" if "glyf" in font else "CFF "
            digest = hashlib.sha1(font.reader[tag]).hexdigest()
            outlines.setdefault(digest, []).append(f"{relpath} ({weight})")

        dupes = {d: files for d, files in outlines.items() if len(files) > 1}
        assert not dupes, f"font files share identical outlines: {list(dupes.values())}"

    def test_heavier_weights_are_actually_wider(self):
        """Cheap sanity check that the cuts differ in the right direction."""

        def adv_h(relpath):
            font = self._face(relpath)
            glyph = font.getBestCmap().get(ord("H"))
            return font["hmtx"][glyph][0] if glyph else None

        sans_400 = adv_h("fonts/source-sans-3-latin.woff2")
        sans_600 = adv_h("fonts/source-sans-3-latin-600.woff2")
        serif_400 = adv_h("fonts/playfair-display-latin.woff2")
        serif_700 = adv_h("fonts/playfair-display-latin-700.woff2")

        assert sans_400 < sans_600, (
            f"Source Sans 400 ({sans_400}) not lighter than 600 ({sans_600})"
        )
        assert serif_400 < serif_700, (
            f"Playfair 400 ({serif_400}) not lighter than 700 ({serif_700})"
        )


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
    """pdffonts-style check on the produced PDF.

    Must parse the PDF, not grep it: WeasyPrint writes objects into compressed
    /ObjStm streams, so /BaseFont appears zero times in the raw bytes. An earlier
    version of these tests regexed the bytes, which made the positive assertion
    fail unconditionally and the negative one pass vacuously against an empty
    string — it would have certified a PDF with no brand fonts at all.
    """

    @staticmethod
    def _pdf_bytes():
        pytest.importorskip("weasyprint")
        from app.filters import DEFAULT_FILTER_STATE
        from app.pdf import generate_scorecard_pdf
        from app.views.door_count import _fmt_usd_compact, _revenue_at_risk
        from app.views.scorecard import _compute_scorecard_data

        data = _compute_scorecard_data(dict(DEFAULT_FILTER_STATE))
        data["revenue_rate"] = 15
        data["revenue_at_risk"] = _fmt_usd_compact(_revenue_at_risk(data["gap_pairs"], 15))
        return generate_scorecard_pdf(data)

    @staticmethod
    def _fonts(pdf_bytes):
        """{BaseFont name: glyph count} for every font the PDF actually uses."""
        import io

        pypdf = pytest.importorskip("pypdf")

        out = {}
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            res = page.get("/Resources")
            if not res:
                continue
            fonts = res.get_object().get("/Font")
            if not fonts:
                continue
            for ref in fonts.get_object().values():
                font = ref.get_object()
                for f in [font, *(k.get_object() for k in font.get("/DescendantFonts") or [])]:
                    base = f.get("/BaseFont")
                    if not base:
                        continue
                    name = str(base).lstrip("/")
                    # max, not setdefault: a Type0 parent carries the same
                    # /BaseFont as its descendant but none of the glyph data, and
                    # it is visited first — setdefault would pin every count to 0.
                    out[name] = max(out.get(name, 0), _glyph_count(f))
        return out

    def test_embeds_playfair_and_source_sans(self):
        fonts = self._fonts(self._pdf_bytes())
        assert fonts, "no fonts found — the PDF parse failed, not the fix"
        assert any("Playfair" in n for n in fonts), f"Playfair Display missing; got {list(fonts)}"
        assert any("Source" in n for n in fonts), f"Source Sans 3 missing; got {list(fonts)}"

    def test_body_and_heading_type_are_brand_fonts(self):
        """The brand faces must carry the bulk of the text, not a handful of glyphs."""
        fonts = self._fonts(self._pdf_bytes())
        brand = {n: c for n, c in fonts.items() if "Playfair" in n or "Source" in n}
        assert brand, f"no brand fonts embedded; got {fonts}"
        assert max(brand.values()) > 30, (
            f"brand fonts carry too few glyphs to be doing the body text: {brand}"
        )

    def test_no_wholesale_fallback_to_system_fonts(self):
        """Liberation Sans is allowed for the few glyphs the subsets lack.

        The PDF uses Δ, ≈ and → , none of which fall in the unicode-ranges the
        brand woff2 subsets declare, so Pango substitutes for those glyphs alone.
        That is correct behaviour. What must never happen is a system font
        picking up the body text because a font-family was invalid or a woff2
        failed to resolve.
        """
        fonts = self._fonts(self._pdf_bytes())

        for banned in ("DejaVu", "Nimbus", "FreeSerif", "Liberation-Serif", "Liberation-Mono"):
            offenders = [n for n in fonts if banned.replace("-", "") in n.replace("-", "")]
            assert not offenders, f"{banned} embedded — brand type did not resolve: {offenders}"

        substitutes = {n: c for n, c in fonts.items() if "Liberation" in n}
        for name, count in substitutes.items():
            assert count < 10, (
                f"{name} carries {count} glyphs — that is body text, not symbol "
                f"substitution. All fonts: {fonts}"
            )


def _glyph_count(font_obj):
    """How many distinct characters this font actually renders in the document.

    Reads the width arrays, which list only the CIDs present in the subset. Not
    the embedded font programme: fontTools' getGlyphOrder() reports maxp
    numGlyphs, which a subset preserves, so every font came back as its full
    original glyph count (~2100) regardless of how little it was used.
    """
    w = font_obj.get("/W")
    if w is not None:
        # /W is [cid [w w w] cidFirst cidLast w ...]; count the individual widths.
        total = 0
        for entry in w.get_object():
            obj = entry.get_object() if hasattr(entry, "get_object") else entry
            if isinstance(obj, list):
                total += len(obj)
        if total:
            return total

    widths = font_obj.get("/Widths")
    if widths is not None:
        return len(widths.get_object())
    return 0
