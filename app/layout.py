"""Layout assembly — brand frame, tab navigation, filter bar, and content area."""

import json

from dash import Input, Output, callback, dcc, html

from app import lailara_frame
from app.app import app
from app.components import glossary_block
from app.constants import CHICAGO_20
from app.filters import (
    DEFAULT_FILTER_STATE,
    build_empty_state,
    build_filter_bar,
    register_filter_callbacks,
)
from app.views import door_count, exceptions, scorecard, trends

TAB_LABELS = ["Door Count", "Trends", "Exceptions", "Scorecard"]
TAB_IDS = ["door-count", "trends", "exceptions", "scorecard"]


def _build_intro():
    """Brief orientation for cold visitors above the tab bar."""
    return html.Div(
        [
            html.H1("Distribution Penetration Tracker"),
            html.P(
                "Which stores should carry your product but don't — "
                "and where is that gap widening?"
            ),
            glossary_block(),
        ],
        className="tool-intro",
    )


def _build_tabs():
    """Build the dcc.Tabs component with 4 tabs."""
    return dcc.Tabs(
        id="main-tabs",
        value="door-count",
        children=[
            dcc.Tab(
                label=label,
                value=value,
                className="custom-tab",
                selected_className="custom-tab--selected",
            )
            for label, value in zip(TAB_LABELS, TAB_IDS)
        ],
        className="custom-tabs",
    )


def _build_content_area():
    """Build the loading-wrapped content area."""
    return dcc.Loading(
        id="tab-content-loading",
        type="default",
        color=CHICAGO_20,
        children=html.Div(id="tab-content"),
    )


def register_layout():
    """Set app.layout and register all callbacks."""
    inner_layout = html.Div(
        [
            dcc.Store(
                id="filter-state", storage_type="session", data=json.dumps(DEFAULT_FILTER_STATE)
            ),
            html.Div(
                [
                    _build_intro(),
                    _build_tabs(),
                    build_filter_bar(),
                    build_empty_state(),
                    _build_content_area(),
                ],
                className="lailara-container",
            ),
        ]
    )

    app.layout = lailara_frame.wrap(
        inner_layout,
        tool_name="Door Math",
        footer_note="Distribution penetration tracker for CPG brands. Data: Cinderhaven Provisions, a synthetic demonstration dataset (not a client).",
        no_container=True,
    )

    # Register filter callbacks
    register_filter_callbacks()

    # Register tab-switching callback
    @callback(
        Output("tab-content", "children"),
        Input("main-tabs", "value"),
    )
    def _render_tab(tab_value):
        """Render the selected view's layout."""
        if tab_value == "door-count":
            return door_count.layout()
        elif tab_value == "trends":
            return trends.layout()
        elif tab_value == "exceptions":
            return exceptions.layout()
        elif tab_value == "scorecard":
            return scorecard.layout()
        return html.Div("Unknown tab.")
