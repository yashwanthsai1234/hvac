"""Seed the SQLite database from all 10 CSV files."""

import csv
import sys
from pathlib import Path

# Allow running as: python -m backend.scripts.seed_db
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.db.connection import reset_db, get_db

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Map CSV filename -> (table_name, columns_in_csv_order)
CSV_MAP = {
    "contracts.csv": (
        "contracts",
        ["project_id", "project_name", "original_contract_value",
         "contract_date", "substantial_completion_date", "retention_pct",
         "payment_terms", "gc_name", "architect", "engineer_of_record"],
    ),
    "sov.csv": (
        "sov",
        ["project_id", "sov_line_id", "line_number", "description",
         "scheduled_value", "labor_pct", "material_pct"],
    ),
    "sov_budget.csv": (
        "sov_budget",
        ["project_id", "sov_line_id", "estimated_labor_hours",
         "estimated_labor_cost", "estimated_material_cost",
         "estimated_equipment_cost", "estimated_sub_cost",
         "productivity_factor", "key_assumptions"],
    ),
    "labor_logs.csv": (
        "labor_logs",
        ["project_id", "log_id", "date", "employee_id", "role",
         "sov_line_id", "hours_st", "hours_ot", "hourly_rate",
         "burden_multiplier", "work_area", "cost_code"],
    ),
    "material_deliveries.csv": (
        "material_deliveries",
        ["project_id", "delivery_id", "date", "sov_line_id",
         "material_category", "item_description", "quantity", "unit",
         "unit_cost", "total_cost", "po_number", "vendor", "received_by",
         "condition_notes"],
    ),
    "billing_history.csv": (
        "billing_history",
        ["project_id", "application_number", "period_end", "period_total",
         "cumulative_billed", "retention_held", "net_payment_due", "status",
         "payment_date", "line_item_count"],
    ),
    "billing_line_items.csv": (
        "billing_line_items",
        ["sov_line_id", "description", "scheduled_value", "previous_billed",
         "this_period", "total_billed", "pct_complete", "balance_to_finish",
         "project_id", "application_number"],
    ),
    "change_orders.csv": (
        "change_orders",
        ["project_id", "co_number", "date_submitted", "reason_category",
         "description", "amount", "status", "related_rfi",
         "affected_sov_lines", "labor_hours_impact", "schedule_impact_days",
         "submitted_by", "approved_by"],
    ),
    "rfis.csv": (
        "rfis",
        ["project_id", "rfi_number", "date_submitted", "subject",
         "submitted_by", "assigned_to", "priority", "status",
         "date_required", "date_responded", "response_summary",
         "cost_impact", "schedule_impact"],
    ),
    "field_notes.csv": (
        "field_notes",
        ["project_id", "note_id", "date", "author", "note_type", "content",
         "photos_attached", "weather", "temp_high", "temp_low"],
    ),
}

# Columns that should be cast to float (numeric fields)
NUMERIC_COLS = {
    "original_contract_value", "retention_pct", "scheduled_value",
    "labor_pct", "material_pct", "estimated_labor_hours",
    "estimated_labor_cost", "estimated_material_cost",
    "estimated_equipment_cost", "estimated_sub_cost", "productivity_factor",
    "hours_st", "hours_ot", "hourly_rate", "burden_multiplier",
    "quantity", "unit_cost", "total_cost", "period_total",
    "cumulative_billed", "retention_held", "net_payment_due",
    "previous_billed", "this_period", "total_billed", "pct_complete",
    "balance_to_finish", "amount", "labor_hours_impact",
    "schedule_impact_days", "temp_high", "temp_low",
}

INT_COLS = {
    "line_number", "application_number", "line_item_count",
    "photos_attached",
}


def parse_value(col: str, val: str):
    """Convert a CSV string value to the appropriate Python type."""
    if val == "" or val is None:
        return None
    if col in NUMERIC_COLS:
        try:
            return float(val)
        except ValueError:
            return None
    if col in INT_COLS:
        try:
            return int(val)
        except ValueError:
            return None
    return val


def seed():
    """Drop and recreate DB, then import all CSVs."""
    print("Resetting database...")
    reset_db()
    db = get_db()

    # Import order matters for foreign keys
    import_order = [
        "contracts.csv",
        "sov.csv",
        "sov_budget.csv",
        "labor_logs.csv",
        "material_deliveries.csv",
        "billing_history.csv",
        "billing_line_items.csv",
        "change_orders.csv",
        "rfis.csv",
        "field_notes.csv",
    ]

    for csv_file in import_order:
        table, columns = CSV_MAP[csv_file]
        filepath = DATA_DIR / csv_file
        if not filepath.exists():
            print(f"  SKIP {csv_file} — file not found")
            continue

        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

        rows = []
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                values = tuple(parse_value(c, row.get(c, "")) for c in columns)
                rows.append(values)

        db.executemany(sql, rows)
        db.commit()
        print(f"  {csv_file:30s} → {table:25s} {len(rows):>6,} rows")

    print("\nDone. Database at:", db.execute("PRAGMA database_list").fetchone()[2])


if __name__ == "__main__":
    seed()
