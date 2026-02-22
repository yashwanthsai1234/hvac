"""Phase 1 Gate Test: Data integrity verification."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.db.connection import get_db, init_db

EXPECTED_COUNTS = {
    "contracts": 5,
    "sov": 75,
    "sov_budget": 75,
    "labor_logs": 16445,
    "material_deliveries": 269,
    "billing_history": 83,
    "billing_line_items": 1163,
    "change_orders": 64,
    "rfis": 317,
    "field_notes": 1328,
}

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def main():
    global passed, failed
    init_db()
    db = get_db()

    print("\n=== TEST 1: Row counts ===")
    for table, expected in EXPECTED_COUNTS.items():
        actual = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        check(
            f"{table} count",
            actual == expected,
            f"expected={expected}, got={actual}",
        )

    print("\n=== TEST 2: Foreign key integrity ===")
    # Every labor_logs.project_id exists in contracts
    orphan = db.execute("""
        SELECT COUNT(*) FROM labor_logs l
        LEFT JOIN contracts c ON l.project_id = c.project_id
        WHERE c.project_id IS NULL
    """).fetchone()[0]
    check("labor_logs → contracts FK", orphan == 0, f"{orphan} orphans")

    # Every labor_logs.sov_line_id exists in sov
    orphan = db.execute("""
        SELECT COUNT(*) FROM labor_logs l
        LEFT JOIN sov s ON l.sov_line_id = s.sov_line_id
        WHERE s.sov_line_id IS NULL AND l.sov_line_id IS NOT NULL
    """).fetchone()[0]
    check("labor_logs → sov FK", orphan == 0, f"{orphan} orphans")

    # Every billing_line_items.sov_line_id exists in sov
    orphan = db.execute("""
        SELECT COUNT(*) FROM billing_line_items b
        LEFT JOIN sov s ON b.sov_line_id = s.sov_line_id
        WHERE s.sov_line_id IS NULL
    """).fetchone()[0]
    check("billing_items → sov FK", orphan == 0, f"{orphan} orphans")

    # Every sov_budget.sov_line_id exists in sov
    orphan = db.execute("""
        SELECT COUNT(*) FROM sov_budget sb
        LEFT JOIN sov s ON sb.sov_line_id = s.sov_line_id
        WHERE s.sov_line_id IS NULL
    """).fetchone()[0]
    check("sov_budget → sov FK", orphan == 0, f"{orphan} orphans")

    print("\n=== TEST 3: No NULLs in required fields ===")
    null_prj = db.execute(
        "SELECT COUNT(*) FROM labor_logs WHERE project_id IS NULL"
    ).fetchone()[0]
    check("labor_logs.project_id not null", null_prj == 0, f"{null_prj} nulls")

    null_rate = db.execute(
        "SELECT COUNT(*) FROM labor_logs WHERE hourly_rate IS NULL"
    ).fetchone()[0]
    check("labor_logs.hourly_rate not null", null_rate == 0, f"{null_rate} nulls")

    null_date = db.execute(
        "SELECT COUNT(*) FROM labor_logs WHERE date IS NULL"
    ).fetchone()[0]
    check("labor_logs.date not null", null_date == 0, f"{null_date} nulls")

    print("\n=== TEST 4: Spot checks ===")
    # PRJ-2024-001 contract value
    row = db.execute(
        "SELECT original_contract_value FROM contracts WHERE project_id = 'PRJ-2024-001'"
    ).fetchone()
    check(
        "PRJ-2024-001 contract = $35,194,000",
        row is not None and abs(row[0] - 35194000) < 1,
        f"got {row[0] if row else 'NULL'}",
    )

    # SOV lines per project
    for pid in ["PRJ-2024-001", "PRJ-2024-002", "PRJ-2024-003", "PRJ-2024-004", "PRJ-2024-005"]:
        cnt = db.execute(
            "SELECT COUNT(*) FROM sov WHERE project_id = ?", (pid,)
        ).fetchone()[0]
        check(f"{pid} has 15 SOV lines", cnt == 15, f"got {cnt}")

    # Labor log count per project (should be > 0 for all)
    for pid in ["PRJ-2024-001", "PRJ-2024-002", "PRJ-2024-003", "PRJ-2024-004", "PRJ-2024-005"]:
        cnt = db.execute(
            "SELECT COUNT(*) FROM labor_logs WHERE project_id = ?", (pid,)
        ).fetchone()[0]
        check(f"{pid} has labor logs", cnt > 0, f"got {cnt}")

    print("\n=== TEST 5: Date validation ===")
    # Check dates parse (YYYY-MM-DD format)
    bad_dates = db.execute("""
        SELECT COUNT(*) FROM labor_logs
        WHERE date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    """).fetchone()[0]
    check("labor_logs dates are YYYY-MM-DD", bad_dates == 0, f"{bad_dates} bad dates")

    bad_dates = db.execute("""
        SELECT COUNT(*) FROM contracts
        WHERE contract_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    """).fetchone()[0]
    check("contracts dates are YYYY-MM-DD", bad_dates == 0, f"{bad_dates} bad dates")

    print(f"\n{'='*50}")
    print(f"  PASSED: {passed}  |  FAILED: {failed}")
    print(f"{'='*50}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
