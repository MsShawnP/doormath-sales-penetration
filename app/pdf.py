"""WeasyPrint PDF generation for the distribution scorecard."""

import os

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


def _get_template_env():
    """Get Jinja2 template environment."""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    return Environment(loader=FileSystemLoader(template_dir), autoescape=True)


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

    # Pass color constants to template
    context = {
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

    html_content = template.render(**context)

    try:
        from weasyprint import HTML

        return HTML(string=html_content).write_pdf()
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

    context = {
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

    return template.render(**context)
