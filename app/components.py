"""Shared reusable Dash HTML components — dark callout cards, annotations, error banners,
and click-to-expand term definitions."""

from dash import html

from app.constants import (
    CARD_BG,
    CARD_BORDER,
    CARD_ITEM,
    CARD_MUTED,
    CARD_SUBTITLE,
    CARD_TEXT,
    FAIL_BG,
    FONT_SANS,
    FONT_SERIF,
    GRIDLINE,
    INK,
    RED_42,
    TEXT_SECONDARY,
    WHITE,
)

TERM_DEFINITIONS = {
    "penetration": (
        "Sales / distribution penetration",
        "Of all the stores that could carry an item, the share that actually do. "
        "It’s the foundation metric: before velocity, household penetration, or "
        "repeat rate mean anything, the product first has to exist on the shelf.",
    ),
    "authorized": (
        "Authorized (authorized pairs)",
        "An item-store pair the retailer has approved to carry. “Authorized” = the "
        "retailer said yes, this SKU is cleared for this store’s shelf. It’s "
        "permission, not proof the product is there.",
    ),
    "scanning": (
        "Scanning (scanning pairs)",
        "An item-store pair that is actually ringing up at the register (recorded "
        "POS scans). “Currently scanning” means it sold in the most recent quarter. "
        "This is the shelf saying yes, as opposed to the contract saying yes.",
    ),
    "gap": (
        "Authorization-to-scan gap (“the gap”)",
        "Item-store pairs that are authorized but not currently scanning. The "
        "retailer said yes, but nothing is selling — the product isn’t on the "
        "shelf, or isn’t moving. This delta is where authorized distribution "
        "quietly leaks revenue.",
    ),
    "door_count": (
        "% of addressable doors carrying (door count)",
        "Of all the store doors that could carry the item, how many actually "
        "carry it — as a count and a percentage.",
    ),
    "acv": (
        "ACV% (weighted distribution)",
        "All-Commodity Volume–weighted distribution: the percentage of total retail "
        "sales volume flowing through the stores that carry your item. It weights "
        "stores by size, so being in 30% of the largest stores is worth far more "
        "reach than 30% of small ones. Unlike a raw store count, ACV% reflects "
        "the commercial value of where you’re distributed.",
    ),
    "tdp": (
        "TDP (Total Distribution Points)",
        "The sum of ACV% across all your items in a category. It captures both "
        "breadth (how many doors) and depth (how many of your items per door) in "
        "a single number — a compact measure of total shelf presence.",
    ),
    "unweighted": (
        "Unweighted distribution",
        "The raw percentage of stores carrying the item, treating every store "
        "equally regardless of size. The plain-count companion to ACV%.",
    ),
    "slow_leak": (
        "Slow leak (slow-leak detection)",
        "An item quietly losing doors quarter after quarter, each drop small "
        "enough that no single period looks alarming — so the erosion goes "
        "unnoticed until the cumulative loss is large. The tool surfaces these "
        "before they become obvious.",
    ),
    "exceptions": (
        "Exceptions (authorized-but-not-scanning)",
        "The concrete list behind the gap: each authorized item-store pair that "
        "isn’t scanning, so a team can chase specific voids. Ranked by weeks silent.",
    ),
    "weeks_silent": (
        "Weeks silent",
        "The number of consecutive weeks an authorized pair has recorded no "
        "scans. Longer = more entrenched a void.",
    ),
}


def term_disclosure(term_key, inline=False):
    """Click-to-expand caret disclosure for a term definition.

    Uses native <details>/<summary> — no JS needed.
    The caret ▸/▾ is rendered via CSS ::before.
    """
    title, definition = TERM_DEFINITIONS[term_key]
    cls = "term-disclosure-inline" if inline else "term-disclosure"
    return html.Details(
        [
            html.Summary(title, className="term-toggle"),
            html.P(definition, className="term-body"),
        ],
        className=cls,
    )


def glossary_block():
    """Collapsible glossary containing all term definitions."""
    items = [term_disclosure(key) for key in TERM_DEFINITIONS]
    return html.Details(
        [
            html.Summary("What these terms mean", className="glossary-toggle"),
            html.Div(items, className="glossary-content"),
        ],
        className="glossary-block",
    )


def dark_callout_card(title, subtitle=None, rows=None):
    """Dark callout card for click-to-pin detail displays.

    Args:
        title: Primary heading text (e.g. retailer name).
        subtitle: Optional secondary line below the title.
        rows: List of dicts with 'label' and 'value' keys.

    Returns:
        html.Div with className='dark-callout'.
    """
    children = [
        html.H3(
            title,
            style={
                "color": CARD_TEXT,
                "fontFamily": "var(--ll-serif)",
                "fontSize": "20px",
                "fontWeight": "700",
                "margin": "0 0 4px 0",
            },
        ),
    ]

    if subtitle:
        children.append(
            html.P(
                subtitle,
                style={
                    "color": CARD_SUBTITLE,
                    "fontFamily": "var(--ll-sans)",
                    "fontSize": "14px",
                    "margin": "0 0 12px 0",
                },
            )
        )

    if rows:
        for row in rows:
            children.append(
                html.Div(
                    [
                        html.Span(
                            row["label"],
                            style={
                                "color": CARD_MUTED,
                                "fontFamily": "var(--ll-sans)",
                                "fontSize": "13px",
                            },
                        ),
                        html.Span(
                            row["value"],
                            style={
                                "color": CARD_ITEM,
                                "fontFamily": "var(--ll-sans)",
                                "fontSize": "14px",
                                "fontWeight": "600",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "padding": "6px 0",
                        "borderBottom": f"1px solid {CARD_BORDER}",
                    },
                )
            )

    return html.Div(
        children,
        className="dark-callout",
        style={
            "backgroundColor": CARD_BG,
            "padding": "20px 24px",
            "borderRadius": "2px",
            "marginTop": "16px",
        },
    )


def stat_card(value, label):
    """Big-number stat card — large metric with context label beneath."""
    return html.Div(
        [
            html.Div(
                value,
                style={
                    "fontFamily": FONT_SERIF,
                    "fontSize": "36px",
                    "fontWeight": "700",
                    "color": INK,
                    "letterSpacing": "-0.02em",
                    "lineHeight": "1",
                },
            ),
            html.P(
                label,
                style={
                    "fontFamily": FONT_SANS,
                    "fontSize": "14px",
                    "color": TEXT_SECONDARY,
                    "marginTop": "8px",
                    "lineHeight": "1.4",
                    "margin": "8px 0 0 0",
                },
            ),
        ],
        className="stat-card",
        style={
            "flex": "1",
            "minWidth": "180px",
            "padding": "20px 24px",
            "borderLeft": f"3px solid {GRIDLINE}",
        },
    )


def stat_card_row(cards):
    """Horizontal row of stat cards, wrapping on narrow viewports."""
    return html.Div(
        cards,
        className="stat-card-row",
        style={
            "display": "flex",
            "gap": "16px",
            "flexWrap": "wrap",
            "marginTop": "16px",
            "marginBottom": "24px",
        },
    )


def annotation_callout(text):
    """Insight-line annotation callout — left-border accent.

    Returns:
        html.Div with className='insight-line'.
    """
    return html.Div(
        html.P(
            text,
            style={
                "margin": "0",
                "fontFamily": "var(--ll-sans)",
                "fontSize": "15px",
                "lineHeight": "1.5",
                "color": TEXT_SECONDARY,
            },
        ),
        className="insight-line",
        style={
            "borderLeft": f"3px solid {GRIDLINE}",
            "paddingLeft": "16px",
            "marginTop": "12px",
            "marginBottom": "12px",
        },
    )


def th_style(align="left"):
    """Inline style dict for table header cells."""
    return {
        "textAlign": align,
        "padding": "8px 12px",
        "borderBottom": f"2px solid {INK}",
        "fontFamily": FONT_SANS,
        "fontSize": "13px",
        "fontWeight": "600",
        "color": INK,
        "whiteSpace": "nowrap",
    }


def td_style(bg=WHITE, align="left", color=None):
    """Inline style dict for table data cells."""
    return {
        "textAlign": align,
        "padding": "6px 12px",
        "borderBottom": f"1px solid {GRIDLINE}",
        "fontFamily": FONT_SANS,
        "fontSize": "14px",
        "color": color or INK,
        "backgroundColor": bg,
    }


def chart_footnote(text):
    """Muted italic footnote for below a chart — source/methodology note.

    Per the Lailara chart system: every chart gets a footnote (source,
    exclusions, methodology). Not optional.

    Returns:
        html.P styled per the design system footnote spec
        (Source Sans 3, 11px, italic, London-35).
    """
    return html.P(
        text,
        className="chart-footnote",
        style={
            "fontFamily": FONT_SANS,
            "fontSize": "11px",
            "fontStyle": "italic",
            "color": TEXT_SECONDARY,
            "margin": "8px 0 0 0",
            "lineHeight": "1.4",
        },
    )


def unfiltered_data_callout(filters):
    """Return a callout when empty filter lists silently default to all data."""
    retailers = filters.get("retailers")
    product_lines = filters.get("product_lines")
    if retailers and product_lines:
        return None
    parts = []
    if not retailers:
        parts.append("retailers")
    if not product_lines:
        parts.append("product lines")
    return annotation_callout(
        f"No {' or '.join(parts)} selected — showing all data. "
        f"Use the filter bar to narrow results."
    )


def error_banner(message, retry_id=None):
    """Error banner with optional retry button.

    Args:
        message: Error description text.
        retry_id: Optional component id for a retry button.

    Returns:
        html.Div with className='error-banner'.
    """
    children = [
        html.Span(
            message,
            style={
                "fontFamily": "var(--ll-sans)",
                "fontSize": "14px",
                "color": RED_42,
            },
        ),
    ]

    if retry_id:
        children.append(
            html.Button(
                "Retry",
                id=retry_id,
                n_clicks=0,
                style={
                    "marginLeft": "12px",
                    "cursor": "pointer",
                },
            )
        )

    return html.Div(
        children,
        className="error-banner",
        style={
            "display": "flex",
            "alignItems": "center",
            "padding": "12px 16px",
            "backgroundColor": FAIL_BG,
            "borderRadius": "2px",
            "marginBottom": "16px",
        },
    )
