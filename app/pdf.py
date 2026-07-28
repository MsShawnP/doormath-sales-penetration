"""WeasyPrint PDF generation for the distribution scorecard."""

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.constants import (
    CANVAS,
    CHICAGO_20,
    FAIL_BG,
    FAIL_TEXT,
    FONT_SANS,
    FONT_SERIF,
    GRIDLINE,
    HK_35,
    INK,
    PASS_BG,
    PASS_TEXT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TOKYO_40,
    WARN_BG,
    WARN_TEXT,
    WHITE,
    fmt_number,
    fmt_pct,
)

_PDF_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_PDF_TIMEOUT_SECONDS = 30

# The template's @font-face rules use paths relative to assets/, so WeasyPrint
# needs a base_url to resolve them.  Without it the woff2 files cannot be found
# and the PDF silently falls back to whatever the system provides — DejaVu Serif
# and Liberation Sans, neither of which is a brand font.  Resolved from this
# file so it holds in the container too: /app/app/pdf.py -> /app/assets.
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def _assets_base_url():
    """file:// URL for assets/, with the trailing slash urljoin needs."""
    return _ASSETS_DIR.as_uri() + "/"


def _get_template_env():
    """Get Jinja2 template environment."""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    return Environment(loader=FileSystemLoader(template_dir), autoescape=True)


def _template_context(data):
    """Build the render context.

    Single definition on purpose: this was duplicated between the PDF path and
    the HTML path, so a value added to one silently left the other rendering an
    undefined variable — and only the HTML path is under test.
    """
    return {
        **data,
        "colors": {
            "canvas": CANVAS,
            "ink": INK,
            "text_primary": TEXT_PRIMARY,
            "text_secondary": TEXT_SECONDARY,
            "gridline": GRIDLINE,
            "navy": CHICAGO_20,
            "teal": HK_35,
            "risk": TOKYO_40,
            "pass_bg": PASS_BG,
            "pass_text": PASS_TEXT,
            "warn_bg": WARN_BG,
            "warn_text": WARN_TEXT,
            "fail_bg": FAIL_BG,
            "fail_text": FAIL_TEXT,
            "white": WHITE,
        },
        "fonts": {
            "serif": FONT_SERIF,
            "sans": FONT_SANS,
        },
        "fmt_pct": fmt_pct,
        "fmt_number": fmt_number,
    }


def generate_scorecard_pdf(data):
    """Generate a PDF scorecard from the given data dict.

    Args:
        data: dict with keys:
            - hero_pct: float (0-1), the hero metric percentage
            - hero_delta: float, pp change from prior quarter
            - retailer_rows: list of dicts with retailer summary data
            - product_line_rows: list of dicts with product line summary data
            - top_exceptions: list of dicts (top 10 exceptions)
            - quarter_label: str, e.g. "Q4 2025"
            - generation_date: str

    Returns:
        bytes: PDF content
    """
    env = _get_template_env()
    template = env.get_template("scorecard.html")
    html_content = template.render(**_template_context(data))

    try:
        from weasyprint import HTML

        future = _PDF_EXECUTOR.submit(
            HTML(string=html_content, base_url=_assets_base_url()).write_pdf
        )
        return future.result(timeout=_PDF_TIMEOUT_SECONDS)
    except FuturesTimeout:
        raise RuntimeError(f"PDF generation timed out after {_PDF_TIMEOUT_SECONDS} seconds.")
    except (ImportError, OSError):
        raise RuntimeError(
            "WeasyPrint is not available. On Windows, WeasyPrint requires "
            "GTK and Pango system libraries. On Linux/macOS, install with: "
            "pip install 'doormath-sales-penetration[pdf]'"
        )


def render_scorecard_html(data):
    """Render the scorecard template to an HTML string (for testing).

    Same interface as ``generate_scorecard_pdf`` but returns HTML instead of
    PDF bytes.  Useful for verifying template rendering without WeasyPrint.
    """
    env = _get_template_env()
    template = env.get_template("scorecard.html")
    return template.render(**_template_context(data))
