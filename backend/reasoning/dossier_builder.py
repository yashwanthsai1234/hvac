"""Build complete dossier JSON per project from JSONL data and store in SQLite."""

import json
import os

from backend.db.connection import get_db
from backend.reasoning.reasoning_engine import reason_about_trigger

TRIGGERS_JSONL = os.path.join(os.path.dirname(__file__), "..", "data", "triggers.jsonl")
PROJECTS_JSONL = os.path.join(os.path.dirname(__file__), "..", "data", "projects.jsonl")


def _load_triggers_from_jsonl(project_id):
    """Load trigger records for a project from the JSONL file."""
    triggers = []
    with open(TRIGGERS_JSONL) as f:
        for line in f:
            record = json.loads(line)
            if record["project_id"] == project_id:
                triggers.append(record)
    return triggers


def _load_project_from_jsonl(project_id):
    """Load a project record from the JSONL file."""
    with open(PROJECTS_JSONL) as f:
        for line in f:
            record = json.loads(line)
            if record["project_id"] == project_id:
                return record
    return None


def build_project_dossier(project_id, use_api=True):
    """
    Build a complete dossier JSON for a single project.

    Reads from the exported JSONL files (triggers.jsonl, projects.jsonl)
    which contain all computed scores, metrics, and evidence.

    Returns: dict (the dossier)
    """
    # ── Load from JSONL ────────────────────────────────
    project = _load_project_from_jsonl(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found in {PROJECTS_JSONL}")

    trigger_records = _load_triggers_from_jsonl(project_id)

    project_context = {
        "project_id": project_id,
        "project_name": project["project_name"],
        "contract_value": project["contract_value"],
        "health_score": project["health_score"],
        "status": project["status"],
        "bid_margin_pct": project["financials"]["bid_margin_pct"],
        "realized_margin_pct": project["financials"]["realized_margin_pct"],
    }

    # ── Triggers with evidence + reasoning ────────────
    # Each JSONL record already has metrics + evidence baked in
    high_triggers = [t for t in trigger_records if t["severity"] == "HIGH"]
    medium_triggers = [t for t in trigger_records if t["severity"] == "MEDIUM"]

    # Reason about up to 5 HIGH + 3 MEDIUM with API; rest get fallback
    api_set = set()
    for t in high_triggers[:5]:
        api_set.add(t["trigger_id"])
    for t in medium_triggers[:3]:
        api_set.add(t["trigger_id"])

    triggers_with_reasoning = []
    for record in trigger_records:
        should_use_api = use_api and record["trigger_id"] in api_set

        reasoning = reason_about_trigger(
            record,              # JSONL record has metrics dict + all fields
            record["evidence"],  # evidence already pulled and baked in
            project_context,
            use_api=should_use_api,
        )

        triggers_with_reasoning.append({
            "trigger_id": record["trigger_id"],
            "date": record["date"],
            "type": record["type"],
            "severity": record["severity"],
            "headline": record["headline"],
            "value": record["value"],
            "affected_sov_lines": record["affected_sov_lines"],
            "metrics": record["metrics"],
            "evidence": record["evidence"],
            "reasoning": reasoning,
        })

    # ── Count by type ──────────────────────────────────
    by_type = {}
    for t in trigger_records:
        ttype = t["type"]
        by_type[ttype] = by_type.get(ttype, 0) + 1

    # ── Assemble dossier ──────────────────────────────
    dossier = {
        "project_id": project_id,
        "name": project["project_name"],
        "contract_value": project["contract_value"],
        "start_date": project["contract_date"],
        "end_date": project["completion_date"],
        "gc_name": project["gc_name"],
        "architect": project["architect"],
        "retention_pct": project["retention_pct"],
        "payment_terms": project["payment_terms"],
        "health_score": project["health_score"],
        "status": project["status"],
        "financials": project["financials"],
        "rfi_summary": project["rfi_summary"],
        "sov_lines": project["sov_lines"],
        "triggers": triggers_with_reasoning,
        "trigger_summary": {
            "total": len(trigger_records),
            "high": len(high_triggers),
            "medium": len(medium_triggers),
            "by_type": by_type,
        },
    }

    return dossier


def build_and_store_dossier(project_id, use_api=True):
    """Build dossier from JSONL and store in SQLite dossiers table."""
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
    print(f"  dossier_builder: {project_id} — {trigger_count} triggers (from JSONL)")
    return dossier
