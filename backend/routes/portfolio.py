"""GET /api/portfolio — return portfolio summary JSON."""

import json
from fastapi import APIRouter, HTTPException
from backend.db.connection import get_db

router = APIRouter()


@router.get("/api/portfolio")
def get_portfolio():
    """Return the pre-computed portfolio summary."""
    db = get_db()
    row = db.execute(
        "SELECT dossier_json FROM dossiers WHERE project_id = 'PORTFOLIO'"
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Portfolio not built yet. Run build_dossiers first.")

    return json.loads(row["dossier_json"])


@router.get("/api/contracts")
def get_contracts():
    """Return basic contract info for all projects (STATE 1 cold data)."""
    db = get_db()
    rows = db.execute("""
        SELECT project_id, project_name, original_contract_value,
               contract_date, substantial_completion_date, gc_name,
               architect, retention_pct, payment_terms
        FROM contracts
        ORDER BY project_id
    """).fetchall()

    return [dict(r) for r in rows]
