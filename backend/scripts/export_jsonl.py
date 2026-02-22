"""Export computed scores + evidence as JSONL for LLM reasoning input.

Produces two files:
  - backend/data/triggers.jsonl   — one JSON line per trigger (with project context + evidence)
  - backend/data/projects.jsonl   — one JSON line per project (full financial summary)

Usage:
    python -m backend.scripts.export_jsonl
"""

import json

from backend.db.connection import get_db, init_db
from backend.reasoning.evidence_puller import pull_evidence


def export_projects_jsonl(output_path="backend/data/projects.jsonl"):
    """Export one JSON line per project with all computed financial metrics."""
    db = get_db()

    rows = db.execute("""
        SELECT c.project_id, c.project_name, c.original_contract_value,
               c.contract_date, c.substantial_completion_date,
               c.gc_name, c.architect, c.retention_pct, c.payment_terms,
               m.health_score, m.status,
               m.total_estimated_cost, m.total_actual_cost,
               m.actual_labor_cost, m.actual_material_cost,
               m.estimated_labor_cost, m.estimated_material_cost, m.estimated_sub_cost,
               m.approved_co_total, m.pending_co_total, m.rejected_co_total,
               m.adjusted_contract_value,
               m.bid_margin_pct, m.realized_margin_pct, m.margin_erosion_pct,
               m.cumulative_billed, m.earned_value, m.billing_lag, m.billing_lag_pct,
               m.rfi_total, m.rfi_open, m.rfi_overdue, m.rfi_orphan_count,
               m.rfi_avg_response_days
        FROM contracts c
        JOIN computed_project_metrics m ON c.project_id = m.project_id
        ORDER BY c.project_id
    """).fetchall()

    count = 0
    with open(output_path, "w") as f:
        for row in rows:
            # SOV line breakdown
            sov_rows = db.execute("""
                SELECT csm.sov_line_id, s.description, s.scheduled_value,
                       csm.estimated_labor_cost, csm.actual_labor_cost,
                       csm.estimated_material_cost, csm.actual_material_cost,
                       csm.labor_overrun_pct, csm.material_variance_pct,
                       csm.actual_labor_hours, csm.estimated_labor_hours,
                       csm.pct_complete, csm.total_billed
                FROM computed_sov_metrics csm
                JOIN sov s ON csm.sov_line_id = s.sov_line_id
                WHERE csm.project_id = ?
                ORDER BY csm.sov_line_id
            """, (row["project_id"],)).fetchall()

            sov_lines = [dict(r) for r in sov_rows]

            record = {
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "contract_value": row["original_contract_value"],
                "contract_date": row["contract_date"],
                "completion_date": row["substantial_completion_date"],
                "gc_name": row["gc_name"],
                "architect": row["architect"],
                "retention_pct": row["retention_pct"],
                "payment_terms": row["payment_terms"],
                "health_score": row["health_score"],
                "status": row["status"],
                "financials": {
                    "estimated_cost": row["total_estimated_cost"],
                    "actual_cost": row["total_actual_cost"],
                    "actual_labor_cost": row["actual_labor_cost"],
                    "actual_material_cost": row["actual_material_cost"],
                    "estimated_labor_cost": row["estimated_labor_cost"],
                    "estimated_material_cost": row["estimated_material_cost"],
                    "estimated_sub_cost": row["estimated_sub_cost"],
                    "approved_cos": row["approved_co_total"],
                    "pending_cos": row["pending_co_total"],
                    "rejected_cos": row["rejected_co_total"],
                    "adjusted_contract": row["adjusted_contract_value"],
                    "bid_margin_pct": row["bid_margin_pct"],
                    "realized_margin_pct": row["realized_margin_pct"],
                    "margin_erosion_pct": row["margin_erosion_pct"],
                    "cumulative_billed": row["cumulative_billed"],
                    "earned_value": row["earned_value"],
                    "billing_lag": row["billing_lag"],
                    "billing_lag_pct": row["billing_lag_pct"],
                },
                "rfi_summary": {
                    "total": row["rfi_total"],
                    "open": row["rfi_open"],
                    "overdue": row["rfi_overdue"],
                    "orphan_count": row["rfi_orphan_count"],
                    "avg_response_days": row["rfi_avg_response_days"],
                },
                "sov_lines": sov_lines,
            }
            f.write(json.dumps(record) + "\n")
            count += 1

    print(f"  export_jsonl: wrote {count} projects to {output_path}")
    return count


def export_triggers_jsonl(output_path="backend/data/triggers.jsonl"):
    """Export one JSON line per trigger with project context, metrics, and evidence."""
    db = get_db()

    # Load project context lookup
    project_ctx = {}
    for row in db.execute("""
        SELECT c.project_id, c.project_name, c.original_contract_value,
               m.health_score, m.status, m.bid_margin_pct, m.realized_margin_pct,
               m.margin_erosion_pct, m.total_estimated_cost, m.total_actual_cost
        FROM contracts c
        JOIN computed_project_metrics m ON c.project_id = m.project_id
    """).fetchall():
        project_ctx[row["project_id"]] = {
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "contract_value": row["original_contract_value"],
            "health_score": row["health_score"],
            "status": row["status"],
            "bid_margin_pct": row["bid_margin_pct"],
            "realized_margin_pct": row["realized_margin_pct"],
            "margin_erosion_pct": row["margin_erosion_pct"],
            "total_estimated_cost": row["total_estimated_cost"],
            "total_actual_cost": row["total_actual_cost"],
        }

    # Export all triggers
    trigger_rows = db.execute("""
        SELECT * FROM triggers ORDER BY project_id, severity DESC, date
    """).fetchall()

    count = 0
    with open(output_path, "w") as f:
        for trigger in trigger_rows:
            pid = trigger["project_id"]
            ctx = project_ctx.get(pid, {})

            # Pull evidence for this trigger
            evidence = pull_evidence(trigger)

            # Parse metrics JSON
            metrics = json.loads(trigger["metrics_json"]) if trigger["metrics_json"] else {}

            record = {
                "trigger_id": trigger["trigger_id"],
                "project_id": pid,
                "date": trigger["date"],
                "type": trigger["type"],
                "severity": trigger["severity"],
                "headline": trigger["headline"],
                "value": trigger["value"],
                "affected_sov_lines": trigger["affected_sov_lines"],
                "metrics": metrics,
                "project_context": ctx,
                "evidence": evidence,
            }
            f.write(json.dumps(record) + "\n")
            count += 1

    print(f"  export_jsonl: wrote {count} triggers to {output_path}")
    return count


def export_all():
    """Export both projects and triggers JSONL files."""
    init_db()
    print("[EXPORT] Exporting computed scores to JSONL...")
    export_projects_jsonl()
    export_triggers_jsonl()
    print("[EXPORT] Done.")


if __name__ == "__main__":
    export_all()
