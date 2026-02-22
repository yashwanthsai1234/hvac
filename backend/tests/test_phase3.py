"""Phase 3 gate test — verify dossiers, evidence, reasoning, and portfolio."""

import json
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

    print("\n=== Phase 3 Gate Tests ===\n")

    # ── Dossier storage ──────────────────────────────
    print("--- dossier storage ---")

    dossier_count = db.execute("SELECT COUNT(*) FROM dossiers").fetchone()[0]
    check("6 dossiers stored (5 projects + 1 portfolio)", dossier_count == 6, f"got {dossier_count}")

    # All 5 projects have dossiers
    project_ids = [r[0] for r in db.execute("SELECT project_id FROM dossiers WHERE project_id != 'PORTFOLIO'").fetchall()]
    check("All 5 project dossiers exist", len(project_ids) == 5, f"got {len(project_ids)}")

    # Portfolio exists
    portfolio_row = db.execute("SELECT dossier_json FROM dossiers WHERE project_id = 'PORTFOLIO'").fetchone()
    check("Portfolio dossier exists", portfolio_row is not None)

    # ── Dossier structure ────────────────────────────
    print("\n--- dossier structure ---")

    for pid in project_ids:
        row = db.execute("SELECT dossier_json FROM dossiers WHERE project_id = ?", (pid,)).fetchone()
        dossier = json.loads(row["dossier_json"])

        # Required top-level fields
        required_fields = ["project_id", "name", "contract_value", "health_score",
                          "status", "financials", "triggers", "sov_lines", "trigger_summary"]
        missing = [f for f in required_fields if f not in dossier]
        check(f"{pid} has all required fields", len(missing) == 0, f"missing: {missing}")

        # Financials sub-fields
        fin_fields = ["estimated_cost", "actual_cost", "bid_margin_pct",
                      "realized_margin_pct", "margin_erosion_pct"]
        fin_missing = [f for f in fin_fields if f not in dossier.get("financials", {})]
        check(f"{pid} has financial fields", len(fin_missing) == 0, f"missing: {fin_missing}")

        # SOV lines
        check(f"{pid} has 15 SOV lines", len(dossier.get("sov_lines", [])) == 15,
              f"got {len(dossier.get('sov_lines', []))}")

    # ── Evidence quality ─────────────────────────────
    print("\n--- evidence quality ---")

    for pid in project_ids:
        row = db.execute("SELECT dossier_json FROM dossiers WHERE project_id = ?", (pid,)).fetchone()
        dossier = json.loads(row["dossier_json"])

        triggers = dossier.get("triggers", [])
        check(f"{pid} has triggers", len(triggers) > 0, f"got {len(triggers)}")

        # Check evidence on first trigger
        if triggers:
            t = triggers[0]
            evidence = t.get("evidence", {})
            has_evidence = (
                len(evidence.get("field_notes", [])) > 0
                or len(evidence.get("related_cos", [])) > 0
                or len(evidence.get("related_rfis", [])) > 0
            )
            check(f"{pid} first trigger has evidence", has_evidence,
                  f"notes={len(evidence.get('field_notes', []))} cos={len(evidence.get('related_cos', []))} rfis={len(evidence.get('related_rfis', []))}")

    # Check that evidence field_notes have proper structure
    row = db.execute("SELECT dossier_json FROM dossiers WHERE project_id = 'PRJ-2024-001'").fetchone()
    d = json.loads(row["dossier_json"])
    first_trigger = d["triggers"][0] if d["triggers"] else None
    if first_trigger and first_trigger["evidence"]["field_notes"]:
        note = first_trigger["evidence"]["field_notes"][0]
        note_fields = ["note_id", "date", "author", "content"]
        missing = [f for f in note_fields if f not in note]
        check("Field notes have proper structure", len(missing) == 0, f"missing: {missing}")
    else:
        check("Field notes have proper structure", False, "no field notes found")

    # ── Reasoning quality ────────────────────────────
    print("\n--- reasoning quality ---")

    for pid in project_ids:
        row = db.execute("SELECT dossier_json FROM dossiers WHERE project_id = ?", (pid,)).fetchone()
        dossier = json.loads(row["dossier_json"])

        for t in dossier.get("triggers", [])[:3]:
            reasoning = t.get("reasoning", {})

            # Required reasoning fields
            has_root_cause = bool(reasoning.get("root_cause"))
            has_factors = len(reasoning.get("contributing_factors", [])) > 0
            has_actions = len(reasoning.get("recovery_actions", [])) > 0
            has_amount = "recoverable_amount" in reasoning
            has_confidence = reasoning.get("confidence") in ["HIGH", "MEDIUM", "LOW"]

            check(f"{pid}/{t['trigger_id']} has root_cause", has_root_cause)
            check(f"{pid}/{t['trigger_id']} has contributing_factors", has_factors)
            check(f"{pid}/{t['trigger_id']} has recovery_actions", has_actions)
            check(f"{pid}/{t['trigger_id']} has recoverable_amount", has_amount)
            check(f"{pid}/{t['trigger_id']} has valid confidence", has_confidence,
                  f"got {reasoning.get('confidence')}")

    # ── PRJ-2024-003 specific checks (RED project) ──
    print("\n--- PRJ-2024-003 (RED) specific ---")

    row = db.execute("SELECT dossier_json FROM dossiers WHERE project_id = 'PRJ-2024-003'").fetchone()
    d003 = json.loads(row["dossier_json"])

    check("PRJ-2024-003 is RED", d003["status"] == "RED", f"got {d003['status']}")
    check("PRJ-2024-003 health < 50", d003["health_score"] < 50, f"got {d003['health_score']}")
    check("PRJ-2024-003 has positive margin erosion",
          d003["financials"]["margin_erosion_pct"] > 5,
          f"got {d003['financials']['margin_erosion_pct']}")
    check("PRJ-2024-003 has many triggers", len(d003["triggers"]) > 10,
          f"got {len(d003['triggers'])}")

    # ── Portfolio structure ───────────────────────────
    print("\n--- portfolio summary ---")

    portfolio = json.loads(portfolio_row["dossier_json"])

    check("Portfolio has 5 projects", len(portfolio.get("projects", [])) == 5,
          f"got {len(portfolio.get('projects', []))}")

    check("Portfolio has health score", "portfolio_health" in portfolio)
    check("Portfolio health is 0-100", 0 <= portfolio.get("portfolio_health", -1) <= 100)

    check("Portfolio has total_contract_value", portfolio.get("total_contract_value", 0) > 0)
    check("Portfolio has at_risk_count", "at_risk_count" in portfolio)
    check("Portfolio at_risk_count = 1 (PRJ-2024-003)", portfolio.get("at_risk_count") == 1,
          f"got {portfolio.get('at_risk_count')}")

    # Each project summary has required fields
    for proj_summary in portfolio.get("projects", []):
        req = ["project_id", "name", "health_score", "status", "trigger_count"]
        missing = [f for f in req if f not in proj_summary]
        check(f"Portfolio {proj_summary.get('project_id', '?')} has required fields",
              len(missing) == 0, f"missing: {missing}")

    # ── Summary ──────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"Phase 3 Gate: {PASS} passed, {FAIL} failed out of {PASS+FAIL}")
    if FAIL == 0:
        print("ALL TESTS PASSED — Phase 3 complete!")
    else:
        print(f"FAILURES: {FAIL} tests need attention")
    print()

    return FAIL == 0


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
