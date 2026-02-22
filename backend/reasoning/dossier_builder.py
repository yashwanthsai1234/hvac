"""Build complete dossier JSON per project and store in SQLite."""

import json

from backend.db.connection import get_db
from backend.reasoning.evidence_puller import pull_evidence
from backend.reasoning.reasoning_engine import reason_about_trigger


def build_project_dossier(project_id, use_api=True):
    """
    Build a complete dossier JSON for a single project.

    Combines:
      - Project metadata from contracts
      - Financial metrics from computed_project_metrics
      - Triggers with evidence and reasoning
      - SOV-line details

    Returns: dict (the dossier)
    """
    db = get_db()

    # ── Project metadata ──────────────────────────────
    contract = db.execute(
        "SELECT * FROM contracts WHERE project_id = ?", (project_id,)
    ).fetchone()

    if not contract:
        raise ValueError(f"Project {project_id} not found")

    metrics = db.execute(
        "SELECT * FROM computed_project_metrics WHERE project_id = ?", (project_id,)
    ).fetchone()

    project_context = {
        "project_id": project_id,
        "project_name": contract["project_name"],
        "contract_value": contract["original_contract_value"],
        "health_score": metrics["health_score"] if metrics else None,
        "status": metrics["status"] if metrics else None,
        "bid_margin_pct": metrics["bid_margin_pct"] if metrics else None,
        "realized_margin_pct": metrics["realized_margin_pct"] if metrics else None,
    }

    # ── Financials ────────────────────────────────────
    financials = {}
    if metrics:
        financials = {
            "estimated_cost": metrics["total_estimated_cost"],
            "actual_cost": metrics["total_actual_cost"],
            "actual_labor_cost": metrics["actual_labor_cost"],
            "actual_material_cost": metrics["actual_material_cost"],
            "estimated_labor_cost": metrics["estimated_labor_cost"],
            "estimated_material_cost": metrics["estimated_material_cost"],
            "estimated_sub_cost": metrics["estimated_sub_cost"],
            "approved_cos": metrics["approved_co_total"],
            "pending_cos": metrics["pending_co_total"],
            "rejected_cos": metrics["rejected_co_total"],
            "adjusted_contract": metrics["adjusted_contract_value"],
            "bid_margin_pct": metrics["bid_margin_pct"],
            "realized_margin_pct": metrics["realized_margin_pct"],
            "margin_erosion_pct": metrics["margin_erosion_pct"],
            "cumulative_billed": metrics["cumulative_billed"],
            "earned_value": metrics["earned_value"],
            "billing_lag": metrics["billing_lag"],
            "billing_lag_pct": metrics["billing_lag_pct"],
        }

    # ── RFI summary ───────────────────────────────────
    rfi_summary = {}
    if metrics:
        rfi_summary = {
            "total": metrics["rfi_total"],
            "open": metrics["rfi_open"],
            "overdue": metrics["rfi_overdue"],
            "orphan_count": metrics["rfi_orphan_count"],
            "avg_response_days": metrics["rfi_avg_response_days"],
        }

    # ── SOV line details ──────────────────────────────
    sov_lines = []
    sov_rows = db.execute("""
        SELECT csm.*, s.description, s.scheduled_value
        FROM computed_sov_metrics csm
        JOIN sov s ON csm.sov_line_id = s.sov_line_id
        WHERE csm.project_id = ?
        ORDER BY csm.sov_line_id
    """, (project_id,)).fetchall()

    for row in sov_rows:
        sov_lines.append({
            "sov_line_id": row["sov_line_id"],
            "description": row["description"],
            "scheduled_value": row["scheduled_value"],
            "estimated_labor_cost": row["estimated_labor_cost"],
            "actual_labor_cost": row["actual_labor_cost"],
            "estimated_material_cost": row["estimated_material_cost"],
            "actual_material_cost": row["actual_material_cost"],
            "labor_overrun_pct": row["labor_overrun_pct"],
            "material_variance_pct": row["material_variance_pct"],
            "actual_labor_hours": row["actual_labor_hours"],
            "estimated_labor_hours": row["estimated_labor_hours"],
            "pct_complete": row["pct_complete"],
            "total_billed": row["total_billed"],
        })

    # ── Triggers with evidence + reasoning ────────────
    trigger_rows = db.execute("""
        SELECT * FROM triggers
        WHERE project_id = ?
        ORDER BY severity DESC, date
    """, (project_id,)).fetchall()

    triggers_with_reasoning = []
    # Limit API calls: reason about top triggers only
    # Sort by severity HIGH first, then limit
    high_triggers = [t for t in trigger_rows if t["severity"] == "HIGH"]
    medium_triggers = [t for t in trigger_rows if t["severity"] == "MEDIUM"]

    # Reason about up to 5 HIGH triggers and 3 MEDIUM triggers with API
    api_triggers = high_triggers[:5] + medium_triggers[:3]
    fallback_triggers = [t for t in trigger_rows if t not in api_triggers]

    for trigger in api_triggers:
        evidence = pull_evidence(trigger)
        reasoning = reason_about_trigger(trigger, evidence, project_context, use_api=use_api)
        trigger_metrics = json.loads(trigger["metrics_json"]) if trigger["metrics_json"] else {}

        triggers_with_reasoning.append({
            "trigger_id": trigger["trigger_id"],
            "date": trigger["date"],
            "type": trigger["type"],
            "severity": trigger["severity"],
            "headline": trigger["headline"],
            "value": trigger["value"],
            "affected_sov_lines": trigger["affected_sov_lines"],
            "metrics": trigger_metrics,
            "evidence": evidence,
            "reasoning": reasoning,
        })

    for trigger in fallback_triggers:
        evidence = pull_evidence(trigger)
        reasoning = reason_about_trigger(trigger, evidence, project_context, use_api=False)
        trigger_metrics = json.loads(trigger["metrics_json"]) if trigger["metrics_json"] else {}

        triggers_with_reasoning.append({
            "trigger_id": trigger["trigger_id"],
            "date": trigger["date"],
            "type": trigger["type"],
            "severity": trigger["severity"],
            "headline": trigger["headline"],
            "value": trigger["value"],
            "affected_sov_lines": trigger["affected_sov_lines"],
            "metrics": trigger_metrics,
            "evidence": evidence,
            "reasoning": reasoning,
        })

    # ── Assemble dossier ──────────────────────────────
    dossier = {
        "project_id": project_id,
        "name": contract["project_name"],
        "contract_value": contract["original_contract_value"],
        "start_date": contract["contract_date"],
        "end_date": contract["substantial_completion_date"],
        "gc_name": contract["gc_name"],
        "architect": contract["architect"],
        "retention_pct": contract["retention_pct"],
        "payment_terms": contract["payment_terms"],
        "health_score": metrics["health_score"] if metrics else None,
        "status": metrics["status"] if metrics else None,
        "financials": financials,
        "rfi_summary": rfi_summary,
        "sov_lines": sov_lines,
        "triggers": triggers_with_reasoning,
        "trigger_summary": {
            "total": len(trigger_rows),
            "high": len(high_triggers),
            "medium": len(medium_triggers),
            "by_type": {},
        },
    }

    # Count triggers by type
    for t in trigger_rows:
        ttype = t["type"]
        if ttype not in dossier["trigger_summary"]["by_type"]:
            dossier["trigger_summary"]["by_type"][ttype] = 0
        dossier["trigger_summary"]["by_type"][ttype] += 1

    return dossier


def build_and_store_dossier(project_id, use_api=True):
    """Build dossier and store in SQLite dossiers table."""
    db = get_db()
    dossier = build_project_dossier(project_id, use_api=use_api)
    dossier_json = json.dumps(dossier)

    db.execute("DELETE FROM dossiers WHERE project_id = ?", (project_id,))
    db.execute(
        "INSERT INTO dossiers (project_id, dossier_json) VALUES (?, ?)",
        (project_id, dossier_json),
    )
    db.commit()

    trigger_count = len(dossier["triggers"])
    print(f"  dossier_builder.py: built dossier for {project_id} ({trigger_count} triggers)")
    return dossier
