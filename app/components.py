"""Shared reusable Dash HTML components — dark callout cards, annotations, error banners."""

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
