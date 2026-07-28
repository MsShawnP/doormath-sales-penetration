"""Revenue at risk — a stated assumption, not a measurement.

The store universe carries no price or velocity field and deliberately gains
none, so this figure is driven entirely by a rate the user sets on screen. These
tests pin the arithmetic and, more importantly, the failure modes: a free-text
number input can hand the callback anything.
"""

import pytest

from app.views.door_count import (
    DEFAULT_RATE_PER_ITEM_STORE_WEEK,
    WEEKS_PER_YEAR,
    _compute_retailer_gaps,
    _filter_auth_from_dict,
    _fmt_usd_compact,
    _revenue_at_risk,
)


class TestRevenueArithmetic:
    def test_is_pairs_times_rate_times_weeks(self):
        assert _revenue_at_risk(1000, 10) == 1000 * 10 * WEEKS_PER_YEAR

    def test_scales_linearly_with_the_rate(self):
        assert _revenue_at_risk(500, 20) == 2 * _revenue_at_risk(500, 10)

    def test_scales_linearly_with_the_gap(self):
        assert _revenue_at_risk(1000, 15) == 2 * _revenue_at_risk(500, 15)

    def test_default_rate_is_a_positive_number(self):
        assert DEFAULT_RATE_PER_ITEM_STORE_WEEK > 0

    def test_a_year_is_52_weeks(self):
        assert WEEKS_PER_YEAR == 52


class TestRevenueEdgeCases:
    """The rate arrives from a user-editable input, so it can be anything."""

    @pytest.mark.parametrize("bad", [None, "", "abc", "12abc", [], {}])
    def test_unusable_rate_yields_zero_not_an_exception(self, bad):
        assert _revenue_at_risk(1000, bad) == 0.0

    def test_negative_rate_yields_zero_never_negative_revenue(self):
        assert _revenue_at_risk(1000, -50) == 0.0

    def test_zero_gap_yields_zero(self):
        assert _revenue_at_risk(0, 15) == 0.0

    def test_numeric_string_is_accepted(self):
        assert _revenue_at_risk(100, "10") == 100 * 10 * WEEKS_PER_YEAR


class TestCompactCurrencyFormat:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, "$0"),
            (950, "$950"),
            (1_000, "$1K"),
            (842_660, "$843K"),
            (1_685_320, "$1.7M"),
            (2_527_980, "$2.5M"),
            (4_213_300, "$4.2M"),
        ],
    )
    def test_formats(self, value, expected):
        assert _fmt_usd_compact(value) == expected


class TestRevenueAgainstRealGap:
    def test_matches_the_gap_the_cards_report(self):
        """The figure must be built from the same gap total shown on screen."""
        from app.filters import DEFAULT_FILTER_STATE

        auth = _filter_auth_from_dict(dict(DEFAULT_FILTER_STATE))
        cards = _compute_retailer_gaps(auth, ["Q4 2025"])
        gap = sum(c["gap_raw"] for c in cards)

        assert gap == 3241, "gap total changed; update this pin deliberately"
        assert _revenue_at_risk(gap, 15) == pytest.approx(2_527_980.0)
        assert _fmt_usd_compact(_revenue_at_risk(gap, 15)) == "$2.5M"

    def test_narrowing_the_filter_lowers_the_figure(self):
        from app.filters import DEFAULT_FILTER_STATE

        all_f = dict(DEFAULT_FILTER_STATE)
        one_f = dict(DEFAULT_FILTER_STATE)
        one_f["retailers"] = ["RET-KROGER"]

        gap_all = sum(
            c["gap_raw"] for c in _compute_retailer_gaps(_filter_auth_from_dict(all_f), ["Q4 2025"])
        )
        gap_one = sum(
            c["gap_raw"] for c in _compute_retailer_gaps(_filter_auth_from_dict(one_f), ["Q4 2025"])
        )

        assert gap_one < gap_all
        assert _revenue_at_risk(gap_one, 15) < _revenue_at_risk(gap_all, 15)


class TestAssumptionIsDisclosed:
    def test_the_layout_says_the_figure_is_not_measured(self):
        """The disclosure is the point of this feature — assert it is present."""
        from app.views.door_count import layout

        def walk(node):
            yield node
            children = getattr(node, "children", None)
            if isinstance(children, list):
                for c in children:
                    yield from walk(c)
            elif children is not None:
                yield from walk(children)

        text = " ".join(str(n) for n in walk(layout()) if isinstance(n, str))
        assert "not measured" in text
        assert "assumption" in text.lower()

    def test_the_rate_input_exists_with_the_default(self):
        from app.views.door_count import layout

        found = []
        queue = [layout()]
        while queue:
            node = queue.pop(0)
            if getattr(node, "id", None) == "dc-rev-rate":
                found.append(node)
            children = getattr(node, "children", None)
            if isinstance(children, list):
                queue.extend(children)
            elif children is not None:
                queue.append(children)

        assert found, "rate input dc-rev-rate not found in the layout"
        assert found[0].value == DEFAULT_RATE_PER_ITEM_STORE_WEEK
        assert found[0].min == 0


class TestRevenueInThePdf:
    """The exported scorecard must carry the figure and its assumption together.

    These assert on the rendered HTML rather than the PDF bytes: WeasyPrint
    cannot run on Windows and there is no CI, so the real engine is exercised
    only by the two tests that skip here. See HANDOFF Known-but-unfixed.
    """

    def _data(self, rate=15, **over):
        from app.filters import DEFAULT_FILTER_STATE
        from app.views.scorecard import _compute_scorecard_data

        d = _compute_scorecard_data(dict(DEFAULT_FILTER_STATE))
        d["revenue_rate"] = rate
        d["revenue_at_risk"] = _fmt_usd_compact(_revenue_at_risk(d["gap_pairs"], rate))
        d.update(over)
        return d

    def _html(self, data):
        from app.pdf import render_scorecard_html

        return render_scorecard_html(data)

    def test_scorecard_gap_matches_the_door_count_gap(self):
        """Both surfaces must report the same gap or the app contradicts itself."""
        from app.filters import DEFAULT_FILTER_STATE

        auth = _filter_auth_from_dict(dict(DEFAULT_FILTER_STATE))
        door_count_gap = sum(c["gap_raw"] for c in _compute_retailer_gaps(auth, ["Q4 2025"]))
        assert self._data()["gap_pairs"] == door_count_gap

    def test_figure_and_assumption_appear_together(self):
        html = self._html(self._data(rate=15))
        assert "$2.5M/yr" in html
        assert "$15/item/store/week" in html
        assert "Not measured" in html

    def test_the_rate_reaches_the_pdf(self):
        assert "$40/item/store/week" in self._html(self._data(rate=40))
        assert "$7.5/item/store/week" in self._html(self._data(rate=7.5))

    def test_it_is_not_the_hero_number(self):
        """It must sit below the distribution metrics, outside the hero block."""
        html = self._html(self._data())
        body = html[html.find("</style>") :]
        hero = body[body.find('<div class="hero">') : body.find("Retailer Summary")]
        assert "revenue-note" not in hero

        i_tables = body.find("Product Line Summary")
        i_note = body.find('class="revenue-note"')
        i_exceptions = body.find("Top Exceptions")
        assert i_tables < i_note < i_exceptions

    def test_omitted_when_there_is_no_gap(self):
        assert 'class="revenue-note"' not in self._html(
            self._data(gap_pairs=0, revenue_at_risk="$0")
        )

    def test_omitted_when_no_rate_was_ever_set(self):
        assert 'class="revenue-note"' not in self._html(
            self._data(revenue_rate=None, revenue_at_risk=None)
        )

    def test_screen_scorecard_data_renders_without_the_revenue_keys(self):
        """_compute_scorecard_data alone must still render — the keys are added
        by the download callback, not the computation."""
        from app.filters import DEFAULT_FILTER_STATE
        from app.views.scorecard import _compute_scorecard_data

        html = self._html(_compute_scorecard_data(dict(DEFAULT_FILTER_STATE)))
        assert 'class="revenue-note"' not in html
        assert "Distribution Scorecard" in html
