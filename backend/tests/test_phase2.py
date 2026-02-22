"""Phase 2 gate test — verify compute engine outputs are consistent and realistic."""

import sys
sys.path.insert(0, ".")

from backend.db.connection import get_db, init_db

db = None
PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  -- {detail}")


def run():
    global db
    init_db()
    db = get_db()

    print("\n=== Phase 2 Gate Tests ===\n")

    # ── computed_sov_metrics ──────────────────────────
    print("--- computed_sov_metrics ---")

    count = db.execute("SELECT COUNT(*) FROM computed_sov_metrics").fetchone()[0]
    check("75 SOV line metrics exist", count == 75, f"got {count}")

    # Every SOV line should have estimated_labor_cost >= 0
    neg = db.execute("SELECT COUNT(*) FROM computed_sov_metrics WHERE estimated_labor_cost < 0").fetchone()[0]
    check("No negative estimated_labor_cost", neg == 0, f"{neg} rows")

    # Every SOV line should have actual_labor_cost >= 0
    neg = db.execute("SELECT COUNT(*) FROM computed_sov_metrics WHERE actual_labor_cost < 0").fetchone()[0]
    check("No negative actual_labor_cost", neg == 0, f"{neg} rows")

    # Estimated labor comes from sov_budget (internal rates, should be < scheduled_value * labor_pct)
    bad = db.execute("""
        SELECT COUNT(*) FROM computed_sov_metrics csm
        JOIN sov s ON csm.sov_line_id = s.sov_line_id
        WHERE csm.estimated_labor_cost > s.scheduled_value * s.labor_pct * 1.01
        AND csm.estimated_labor_cost > 0
    """).fetchone()[0]
    check("Est labor < revenue allocation for all lines", bad == 0, f"{bad} lines exceed")

    # Material variance: lines WITH deliveries should be ~0% (billing rate match)
    # Lines without deliveries (SOV-01,02,13,14,15) will show -100% which is expected
    max_mat_var = db.execute("""
        SELECT MAX(ABS(material_variance_pct)) FROM computed_sov_metrics
        WHERE estimated_material_cost > 0 AND actual_material_cost > 0
    """).fetchone()[0] or 0
    check("Material variance ~0% where deliveries exist", max_mat_var < 1.0, f"max={max_mat_var:.1f}%")

    # Labor overrun should exist on most lines (data has massive overruns)
    overrun_count = db.execute("""
        SELECT COUNT(*) FROM computed_sov_metrics
        WHERE labor_overrun_pct > 15 AND estimated_labor_hours > 0
    """).fetchone()[0]
    check("Many SOV lines with >15% labor overrun", overrun_count > 30, f"got {overrun_count}")

    # Actual labor hours should sum to labor_logs total
    computed_hours = db.execute("SELECT SUM(actual_labor_hours) FROM computed_sov_metrics").fetchone()[0]
    raw_hours = db.execute("SELECT SUM(hours_st + hours_ot) FROM labor_logs").fetchone()[0]
    diff_pct = abs(computed_hours - raw_hours) / raw_hours * 100 if raw_hours else 0
    check("Actual labor hours match labor_logs total (<1%)", diff_pct < 1.0, f"diff={diff_pct:.2f}%")

    # Total billed should be populated for most lines
    billed_count = db.execute("SELECT COUNT(*) FROM computed_sov_metrics WHERE total_billed > 0").fetchone()[0]
    check("Most SOV lines have billing data", billed_count > 50, f"got {billed_count}")

    # ── computed_project_metrics ──────────────────────
    print("\n--- computed_project_metrics ---")

    count = db.execute("SELECT COUNT(*) FROM computed_project_metrics").fetchone()[0]
    check("5 project metrics exist", count == 5, f"got {count}")

    # Contract values should match contracts table
    mismatch = db.execute("""
        SELECT COUNT(*) FROM computed_project_metrics cpm
        JOIN contracts c ON cpm.project_id = c.project_id
        WHERE cpm.contract_value != c.original_contract_value
    """).fetchone()[0]
    check("Contract values match source", mismatch == 0, f"{mismatch} mismatches")

    # Bid margins should be in 40-55% range (internal labor + billing materials)
    projects = db.execute("SELECT * FROM computed_project_metrics").fetchall()
    margins_ok = all(35 < p["bid_margin_pct"] < 55 for p in projects)
    check("Bid margins in 35-55% range", margins_ok,
          ", ".join(f"{p['project_id']}={p['bid_margin_pct']:.1f}%" for p in projects))

    # PRJ-2024-003 should have positive margin erosion (distressed)
    p3 = db.execute("SELECT * FROM computed_project_metrics WHERE project_id = 'PRJ-2024-003'").fetchone()
    check("PRJ-2024-003 has positive margin erosion", p3["margin_erosion_pct"] > 5,
          f"erosion={p3['margin_erosion_pct']:.1f}%")

    # Total actual cost should be less than or equal to contract + COs
    for p in projects:
        headroom = (p["adjusted_contract_value"] - p["total_actual_cost"]) / p["adjusted_contract_value"] * 100
        check(f"{p['project_id']} actual cost < adjusted contract",
              p["total_actual_cost"] < p["adjusted_contract_value"],
              f"actual={p['total_actual_cost']:,.0f} adj_contract={p['adjusted_contract_value']:,.0f}")

    # Billing lag should be near zero (< 1% of contract)
    for p in projects:
        check(f"{p['project_id']} billing lag < 1%",
              abs(p["billing_lag_pct"]) < 1.0,
              f"lag={p['billing_lag_pct']:.2f}%")

    # Earned value should be reasonable
    for p in projects:
        ev_pct = p["earned_value"] / p["contract_value"] * 100 if p["contract_value"] else 0
        check(f"{p['project_id']} earned value > 50% of contract",
              ev_pct > 50, f"EV={ev_pct:.1f}%")

    # ── health scores ──────────────────────────────────
    print("\n--- health scores ---")

    # All projects should have health scores
    scored = db.execute("SELECT COUNT(*) FROM computed_project_metrics WHERE health_score IS NOT NULL").fetchone()[0]
    check("All 5 projects have health scores", scored == 5, f"got {scored}")

    # PRJ-2024-003 should be RED
    p3_status = db.execute("SELECT status FROM computed_project_metrics WHERE project_id = 'PRJ-2024-003'").fetchone()["status"]
    check("PRJ-2024-003 is RED", p3_status == "RED", f"got {p3_status}")

    # Health scores should be 0-100
    bad_scores = db.execute("""
        SELECT COUNT(*) FROM computed_project_metrics
        WHERE health_score < 0 OR health_score > 100
    """).fetchone()[0]
    check("All health scores in 0-100", bad_scores == 0, f"{bad_scores} out of range")

    # ── triggers ──────────────────────────────────────
    print("\n--- triggers ---")

    total_triggers = db.execute("SELECT COUNT(*) FROM triggers").fetchone()[0]
    check("Triggers detected (>50)", total_triggers > 50, f"got {total_triggers}")

    # LABOR_OVERRUN triggers exist
    lo = db.execute("SELECT COUNT(*) FROM triggers WHERE type = 'LABOR_OVERRUN'").fetchone()[0]
    check("Labor overrun triggers exist (>20)", lo > 20, f"got {lo}")

    # ORPHAN_RFI triggers exist
    orfi = db.execute("SELECT COUNT(*) FROM triggers WHERE type = 'ORPHAN_RFI'").fetchone()[0]
    check("Orphan RFI triggers exist (>20)", orfi > 20, f"got {orfi}")

    # All triggers have valid project_ids
    bad_pid = db.execute("""
        SELECT COUNT(*) FROM triggers t
        WHERE NOT EXISTS (SELECT 1 FROM contracts c WHERE c.project_id = t.project_id)
    """).fetchone()[0]
    check("All triggers have valid project_ids", bad_pid == 0, f"{bad_pid} invalid")

    # All triggers have dates
    no_date = db.execute("SELECT COUNT(*) FROM triggers WHERE date IS NULL").fetchone()[0]
    check("All triggers have dates", no_date == 0, f"{no_date} missing")

    # Triggers have metrics_json
    no_json = db.execute("SELECT COUNT(*) FROM triggers WHERE metrics_json IS NULL").fetchone()[0]
    check("All triggers have metrics_json", no_json == 0, f"{no_json} missing")

    # ── RFI metrics ──────────────────────────────────
    print("\n--- RFI metrics ---")

    rfi_orphans = db.execute("SELECT SUM(rfi_orphan_count) FROM computed_project_metrics").fetchone()[0] or 0
    check("Orphan RFIs detected", rfi_orphans > 0, f"got {rfi_orphans}")

    rfi_total = db.execute("SELECT SUM(rfi_total) FROM computed_project_metrics").fetchone()[0] or 0
    raw_rfi_count = db.execute("SELECT COUNT(*) FROM rfis").fetchone()[0]
    check("RFI total matches raw row count", rfi_total == raw_rfi_count,
          f"computed={rfi_total} raw={raw_rfi_count}")

    # ── Summary ──────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"Phase 2 Gate: {PASS} passed, {FAIL} failed out of {PASS+FAIL}")
    if FAIL == 0:
        print("ALL TESTS PASSED — Phase 2 complete!")
    else:
        print(f"FAILURES: {FAIL} tests need attention")
    print()

    return FAIL == 0


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
