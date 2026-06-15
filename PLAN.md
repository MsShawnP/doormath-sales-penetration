# Door Math — Plan

**Tier:** Medium
**Status:** Scaffolded — ready for implementation

## Tasks

### Phase 1 — Data model
- [ ] Build synthetic store universe (600 doors, 3 banners, volume tiers)
- [ ] Build authorization matrix (item x door, with deliberate gaps)
- [ ] Build POS scan data generator (weekly, with slow-leak story)
- [ ] Wire data into app (load on startup or via caching)

### Phase 2 — Dashboard pages
- [ ] Door Count page — penetration by item, banner, region with AG Grid + bar charts
- [ ] Trends page — ACV% and TDP trend lines over time
- [ ] Exceptions page — authorized-but-not-scanning list with filters
- [ ] Scorecard page — one-page buyer meeting summary

### Phase 3 — Polish & deploy
- [ ] Apply Lailara design system (fonts, colors, chart styling)
- [ ] Click-to-pin interactions on charts
- [ ] Print stylesheet for scorecard
- [ ] Deploy to Fly.io
- [ ] README finalize with live URL
