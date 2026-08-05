"""Client-mode CLI for Door Math.

Computes distribution penetration and the weeks-silent exception work list on a
client's own POS data via the shared ``lailara_engagement`` POS-intake layer.

Why this is safe against the ISO-week bug family: weeks-silent here is plain
date arithmetic on the declared week grid — ``(as_of - last_scan_week).days //
7`` — not ISO-week-number subtraction. The layer's ``week_convention`` validates
that every ``week_ending`` falls on the declared weekday, so the grid can't be
mislabeled; there is no year-boundary week-number to be off-by-one on.

Three required inputs (weekly **scans**, the **authorization** log, the **store**
dimension). A missing required column blocks with a branded Data Readiness
Report; a clean run writes a draft-watermarked, provenance-footed
**Distribution Penetration & Weeks-Silent** deliverable (HTML) plus the ranked
exceptions (CSV) to ``client-output/`` only. Demo mode is untouched (additive).

Usage:
    python client_mode.py --config engagement.yml [--out client-output] [--final]
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import pandas as pd

from lailara_engagement import (
    build_provenance,
    load_config,
    pos,
    read_table,
    validation_status_label,
    write_report,
)
from lailara_engagement import palette as P
from lailara_engagement.provenance import Provenance

TOOL = "doormath"
TOOL_VERSION = "1.0"
DEFAULT_SILENCE_THRESHOLD_WEEKS = 4


def _resolve_inputs(config, args) -> dict[str, str | None]:
    cfg_inputs = config.raw.get("inputs") or {}
    return {
        "scans": args.scans or cfg_inputs.get("scans"),
        "authorizations": args.auth or cfg_inputs.get("authorizations") or cfg_inputs.get("auth"),
        "stores": args.stores or cfg_inputs.get("stores"),
    }


def compute_penetration(scans, auth, stores, as_of, threshold_weeks):
    """Return (summary_dict, exceptions_df) from the canonical POS frames.

    addressable = unique authorized (sku, store_id) pairs.
    carrying    = authorized pairs that scanned (units>0) at or before as_of.
    weeks_silent = whole weeks since the pair's last positive scan (never-scanned
                   -> weeks since authorization), by date arithmetic on the grid.
    """
    auth_pairs = auth[["sku", "store_id", "authorized_date"]].drop_duplicates(["sku", "store_id"])
    addressable = len(auth_pairs)

    pos_scans = scans[(scans["week_ending"] <= as_of) & (scans["units_sold"] > 0)]
    last_scan = (pos_scans.groupby(["sku", "store_id"], as_index=False)["week_ending"]
                 .max().rename(columns={"week_ending": "last_scan_week"}))
    carrying_pairs = last_scan.drop_duplicates(["sku", "store_id"])
    # carrying = authorized pairs present in the scan set
    carrying = auth_pairs.merge(carrying_pairs, on=["sku", "store_id"], how="inner")
    n_carrying = len(carrying)

    merged = auth_pairs.merge(last_scan, on=["sku", "store_id"], how="left")
    merged = merged.merge(
        stores[["store_id", "retailer_id", "chain_name", "region", "volume_tier"]],
        on="store_id", how="left")

    def weeks_between(a, b):  # whole weeks from a to b
        return ((b - a).dt.days // 7).clip(lower=0)

    scanned = merged["last_scan_week"].notna()
    ws = pd.Series(0, index=merged.index, dtype=int)
    ws[scanned] = weeks_between(merged.loc[scanned, "last_scan_week"], as_of).astype(int)
    ws[~scanned] = weeks_between(merged.loc[~scanned, "authorized_date"], as_of).astype(int)
    merged["weeks_silent"] = ws
    merged["last_scan_date"] = merged["last_scan_week"].dt.strftime("%Y-%m-%d").fillna("Never")

    exceptions = merged[merged["weeks_silent"] > threshold_weeks].copy()
    exceptions = exceptions.sort_values(["weeks_silent", "sku", "store_id"],
                                        ascending=[False, True, True]).reset_index(drop=True)

    summary = {
        "addressable_pairs": addressable,
        "carrying_pairs": n_carrying,
        "penetration": round(n_carrying / addressable, 4) if addressable else 0.0,
        "n_exceptions": len(exceptions),
        "n_never_scanned": int((~scanned).sum()),
        "threshold_weeks": threshold_weeks,
    }
    return summary, exceptions


def _fmt_pct(v):
    return "—" if v is None else f"{v * 100:.1f}%"


def _deliverable_html(config, summary, exceptions, window_label, week_conv,
                      limitations, provenance: Provenance, *, draft: bool) -> str:
    esc = html.escape
    draft_class = " ll-draft" if draft else ""
    top = exceptions.head(30)
    ex_rows = "".join(
        f"<tr><td>{esc(str(r['store_id']))}</td><td>{esc(str(r.get('chain_name','')))}</td>"
        f"<td>{esc(str(r['sku']))}</td><td>{esc(str(r.get('region','')))}</td>"
        f"<td>{esc(str(r['last_scan_date']))}</td>"
        f"<td class=num>{int(r['weeks_silent'])}</td></tr>"
        for _, r in top.iterrows()
    )
    lim_html = "".join(f"<li>{esc(x)}</li>" for x in limitations)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Distribution Penetration &amp; Weeks-Silent — {esc(config.client_name)}</title>
<style>{_css(draft)}</style></head>
<body class="{draft_class.strip()}"><main class=ll-page>
<header class=ll-header>
  <div class=ll-eyebrow>Lailara LLC · Door Math</div>
  <h1 class=ll-title>Distribution Penetration &amp; Weeks-Silent</h1>
  <div class=ll-client>
    <div><span class=ll-k>Client</span> {esc(config.client_name)}</div>
    <div><span class=ll-k>Engagement</span> {esc(config.engagement_id)}</div>
    <div><span class=ll-k>As of</span> {esc(config.as_of_date.isoformat())}</div>
    <div><span class=ll-k>Prepared by</span> {esc(config.prepared_by)}</div>
  </div>
</header>
<section class=ll-banner>
  <div class=ll-score>{_fmt_pct(summary['penetration'])} distribution penetration</div>
  <div>{summary['carrying_pairs']:,} carrying of {summary['addressable_pairs']:,} authorized
       item-store pairs · {summary['n_exceptions']:,} silent &gt; {summary['threshold_weeks']} weeks</div>
  <div class=ll-basis>Basis: carrying authorized pairs ÷ addressable authorized pairs
       · weeks-silent by date arithmetic on the declared week grid<br>
       Window: {esc(window_label)} · week convention: {esc(week_conv)}</div>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Weeks-silent exceptions (ranked)</h2>
  <table class=ll-table><thead><tr><th>Store</th><th>Banner</th><th>Item</th>
  <th>Region</th><th>Last scan</th><th>Weeks silent</th></tr></thead>
  <tbody>{ex_rows}</tbody></table>
  <p class=ll-note>Full ranked list exported to the accompanying CSV.</p>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Data limitations</h2>
  <ul class=ll-limitations>{lim_html}</ul>
</section>
{provenance.to_html()}
</main></body></html>"""


def _css(draft: bool) -> str:
    draft_css = (
        ".ll-draft::before{content:'DRAFT';position:fixed;top:50%;left:50%;"
        "transform:translate(-50%,-50%) rotate(-32deg);font-family:var(--s);"
        "font-size:22vw;font-weight:700;color:rgba(204,16,10,.06);z-index:0;"
        "pointer-events:none;white-space:nowrap}" if draft else ""
    )
    return f"""
:root{{--s:{P.LL_SERIF};--f:{P.LL_SANS}}}
*{{box-sizing:border-box}}
body{{margin:0;background:{P.LL_CANVAS};color:{P.LL_TEXT};font-family:var(--f);line-height:1.6}}
.ll-page{{position:relative;z-index:1;max-width:{P.LL_MAX_WIDTH};margin:0 auto;padding:48px 24px}}
.ll-header{{border-bottom:1px solid {P.LL_GRIDLINE};padding-bottom:24px;margin-bottom:24px}}
.ll-eyebrow{{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{P.LL_RED};font-weight:600}}
.ll-title{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:34px;margin:8px 0 16px}}
.ll-client{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 24px;font-size:14px}}
.ll-k{{display:block;color:{P.LL_TEXT_SEC};font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.ll-banner{{border-radius:2px;padding:16px 20px;margin-bottom:32px;background:{P.LL_CHICAGO_SURFACE};color:{P.LL_CHICAGO}}}
.ll-score{{font-family:var(--s);font-weight:700;font-size:22px}}
.ll-basis{{font-size:12px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-section{{margin:0 0 32px}}
.ll-h2{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:22px;
margin:0 0 12px;padding-bottom:6px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-note{{font-size:13px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ll-table th{{text-align:left;background:{P.LL_CHICAGO};color:#fff;padding:8px 12px}}
.ll-table td{{padding:8px 12px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-limitations{{margin:0;padding-left:20px}}.ll-limitations li{{margin-bottom:6px}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.ll-provenance{{margin-top:40px;background:{P.LL_CARD_BG};color:{P.LL_CARD_TEXT};
padding:20px 24px;border-radius:2px;font-size:13px}}
.ll-prov-title{{font-family:var(--s);font-weight:700;font-size:16px;margin-bottom:8px}}
.ll-provenance div{{margin-bottom:4px;color:{P.LL_CARD_SUBTITLE}}}
.ll-provenance strong{{color:{P.LL_CARD_TEXT}}}
.ll-prov-inputs{{width:100%;border-collapse:collapse;margin-top:8px}}
.ll-prov-inputs th{{text-align:left;border-bottom:1px solid rgba(255,255,255,.12);padding:4px 8px;color:{P.LL_CARD_MUTED}}}
.ll-prov-inputs td{{padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.08);color:{P.LL_CARD_SUBTITLE}}}
.ll-prov-brand{{margin-top:12px;font-family:var(--s);color:{P.LL_CARD_MUTED}}}
{draft_css}
@media print{{body{{background:#fff}}}}
"""


def run(config_path: str, out_dir: str, args, *, final: bool = False) -> dict:
    config = load_config(config_path)
    inputs = _resolve_inputs(config, args)
    week_conv_name, _wd = pos.resolve_week_convention(config)
    threshold = int((config.basis or {}).get("silence_threshold_weeks", DEFAULT_SILENCE_THRESHOLD_WEEKS))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    required = {
        # Door Math is a distribution/penetration tool — units, not dollars.
        "scans": pos.scan_spec(tool=TOOL, version=TOOL_VERSION,
                               week_convention=week_conv_name, require_dollars=False),
        "authorizations": pos.authorization_spec(tool=TOOL, version=TOOL_VERSION),
        "stores": pos.store_spec(tool=TOOL, version=TOOL_VERSION),
    }
    missing_files = [k for k, v in inputs.items() if k in required and not v]
    if missing_files:
        raise SystemExit(f"missing required input(s): {', '.join(missing_files)}.")

    reads, reports, frames = {}, {}, {}
    for key, spec in required.items():
        read = read_table(inputs[key])
        report, frame = pos.intake(read, spec, config)
        reads[key], reports[key], frames[key] = read, report, frame

    reports["scans"].disclosures.append(
        pos.declared_disclosures(week_conv_name, "retail_scan")[0])  # week-convention line

    blocked = {k: r for k, r in reports.items() if not r.passed}
    provenance = build_provenance(
        tool=TOOL, tool_version=TOOL_VERSION, inputs=[reads[k] for k in required],
        config=config,
        validation_status=validation_status_label("failed" if blocked else "clean",
                                                   sum(r.n_warnings for r in reports.values())),
        extra={"Week convention": week_conv_name},
    )
    if blocked:
        written = {}
        for key, report in blocked.items():
            paths = write_report(report, config, str(out), provenance=provenance, draft=not final,
                                 basename=f"data-readiness-{key}",
                                 title=f"Door Math Data Readiness Report — {key}")
            written[key] = paths["html"]
        return {"status": "blocked", "blocked_files": list(blocked), "readiness_reports": written}

    scans, auth, stores = frames["scans"], frames["authorizations"], frames["stores"]
    as_of = pd.Timestamp(config.as_of_date)
    if (scans["week_ending"] <= as_of).sum() == 0:
        raise SystemExit(f"as_of_date {config.as_of_date} precedes every scan week.")

    summary, exceptions = compute_penetration(scans, auth, stores, as_of, threshold)
    first, last = scans["week_ending"].min(), scans["week_ending"].max()
    window_label = (f"scan weeks {first.strftime('%b %d, %Y')} – {last.strftime('%b %d, %Y')} "
                    f"· as of {as_of.strftime('%b %d, %Y')}")

    limitations = []
    for key, report in reports.items():
        for f in report.findings:
            if f.severity == "warning":
                limitations.append(f"[{key}] {f.message}")
    if not limitations:
        limitations.append("No warnings — all three inputs passed preflight cleanly.")

    csv_path = out / "weeks-silent-exceptions.csv"
    exceptions.to_csv(csv_path, index=False)
    html_path = out / "distribution-penetration.html"
    html_path.write_text(_deliverable_html(config, summary, exceptions, window_label,
                                            week_conv_name, limitations, provenance, draft=not final),
                         encoding="utf-8")
    return {"status": "ok", "penetration": summary["penetration"],
            "n_exceptions": summary["n_exceptions"], "report": str(html_path),
            "exceptions_csv": str(csv_path), "n_warnings": sum(r.n_warnings for r in reports.values())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="doormath client mode")
    ap.add_argument("--config", required=True)
    ap.add_argument("--scans"); ap.add_argument("--auth"); ap.add_argument("--stores")
    ap.add_argument("--out", default="client-output"); ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.config, args.out, args, final=args.final)
    if result["status"] == "blocked":
        print("BLOCKED — data not ready. Readiness report(s):")
        for key, path in result["readiness_reports"].items():
            print(f"  {key}: {path}")
        return 3
    print(f"penetration {result['penetration']*100:.1f}% · {result['n_exceptions']:,} weeks-silent exceptions"
          + (f" · {result['n_warnings']} warning(s)" if result["n_warnings"] else ""))
    print(f"report -> {result['report']}\ncsv    -> {result['exceptions_csv']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
