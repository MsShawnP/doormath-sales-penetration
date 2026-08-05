"""Client-mode + POS-intake tests for Door Math (checklist §6).

Skipped unless the shared ``lailara_engagement`` lib is installed. Fixtures are
generated on the fly — no client identifiers, no committed data.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("lailara_engagement")

import client_mode  # noqa: E402

AS_OF = pd.Timestamp("2025-12-27")            # a Saturday
WEEKS = [AS_OF - timedelta(weeks=(11 - i)) for i in range(12)]
EARLY = WEEKS[0] - timedelta(weeks=4)
SKU = "CHP-AS-001"
_RET = [("RET-WMT", "Walmart", "Southeast"), ("RET-COST", "Costco", "West"),
        ("RET-WFM", "Whole Foods", "Northeast"), ("RET-SPR", "Sprouts", "Southwest"),
        ("RET-KRG", "Kroger", "Midwest"), ("RET-RGL", "Regional Group", "Southeast")]


def _world():
    """6 authorized pairs: S1-S4 carrying all weeks, S5 never-scanned,
    S6 went silent after week 2. -> penetration 5/6, 2 exceptions."""
    stores, auth, scans = [], [], []
    for i, (rid, chain, region) in enumerate(_RET, start=1):
        sid = f"S{i}"
        stores.append((sid, rid, chain, region, "GA", "medium"))
        auth.append((SKU, sid, EARLY.strftime("%Y-%m-%d"), ""))
        if i <= 4:                                    # carrying every week
            for w in WEEKS:
                scans.append((sid, SKU, w.strftime("%Y-%m-%d"), 4, 20.0))
        elif i == 6:                                  # went silent after week 2
            for w in WEEKS[:3]:
                scans.append((sid, SKU, w.strftime("%Y-%m-%d"), 4, 20.0))
        # i == 5 -> never scanned
    return (pd.DataFrame(stores, columns=["store_id", "retailer_id", "chain_name", "region", "state", "volume_tier"]),
            pd.DataFrame(auth, columns=["sku", "store_id", "authorized_date", "deauthorized_date"]),
            pd.DataFrame(scans, columns=["store_id", "sku", "week_ending", "units_sold", "dollars_sold"]))


def _write_trio(d: Path):
    stores, auth, scans = _world()
    sp, ap, stp = d / "scans.csv", d / "auth.csv", d / "stores.csv"
    scans.to_csv(sp, index=False); auth.to_csv(ap, index=False); stores.to_csv(stp, index=False)
    return sp, ap, stp


def _write_config(d: Path, *, columns=None):
    import yaml
    cfg = {"client": {"name": "Cinderhaven Provisions (demo)"}, "engagement": {"id": "T-1"},
           "as_of_date": "2025-12-27", "demo": True,
           "basis": {"week_convention": "week_ending_saturday", "silence_threshold_weeks": 4},
           "columns": columns or {}}
    p = d / "engagement.demo.yml"; p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


def _args(scans=None, auth=None, stores=None):
    return SimpleNamespace(scans=scans, auth=auth, stores=stores)


def test_clean_trio_computes_penetration_and_exceptions(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "ok"
    assert res["penetration"] == 0.8333           # 5 carrying / 6 addressable
    assert res["n_exceptions"] == 2               # S5 never + S6 silent 9 weeks
    assert Path(res["report"]).is_file() and Path(res["exceptions_csv"]).is_file()


def test_weeks_silent_is_date_arithmetic_not_iso_week(tmp_path):
    # S6 last scan is WEEKS[2]; as_of is WEEKS[11] -> exactly 9 whole weeks.
    sp, ap, stp = _write_trio(tmp_path)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    ex = pd.read_csv(Path(res["exceptions_csv"]))
    s6 = ex[ex["store_id"] == "S6"].iloc[0]
    assert int(s6["weeks_silent"]) == 9


def test_deliverable_carries_basis_window_and_convention(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    html = Path(res["report"]).read_text(encoding="utf-8")
    assert "distribution penetration" in html
    assert "week convention: week_ending_saturday" in html
    assert "Window: scan weeks" in html
    assert "DRAFT" in html


def test_missing_units_blocks(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    pd.read_csv(sp).drop(columns=["units_sold"]).to_csv(sp, index=False)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "blocked" and res["blocked_files"] == ["scans"]


def test_off_convention_week_blocks(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    df = pd.read_csv(sp); df.loc[0, "week_ending"] = "2025-12-29"  # Monday, ISO 2026-W01
    df.to_csv(sp, index=False)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "blocked"
    assert "Saturday" in Path(res["readiness_reports"]["scans"]).read_text(encoding="utf-8")


def test_header_mapping(tmp_path):
    stores, auth, scans = _world()
    scans = scans.rename(columns={"store_id": "Store", "sku": "Item", "week_ending": "Wk",
                                  "units_sold": "U"})
    sp, ap, stp = tmp_path / "s.csv", tmp_path / "a.csv", tmp_path / "st.csv"
    scans.to_csv(sp, index=False); auth.to_csv(ap, index=False); stores.to_csv(stp, index=False)
    cfg = _write_config(tmp_path, columns={"store_id": "Store", "sku": "Item",
                                           "week_ending": "Wk", "units_sold": "U"})
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "ok"
    assert res["penetration"] == 0.8333
