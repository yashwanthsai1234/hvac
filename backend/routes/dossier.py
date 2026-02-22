"""GET /api/dossier/{project_id} — return full project dossier JSON."""

import json
from fastapi import APIRouter, HTTPException
from backend.db.connection import get_db

router = APIRouter()


@router.get("/api/dossier/{project_id}")
def get_dossier(project_id: str):
    """Return the pre-computed dossier for a specific project."""
    db = get_db()
    row = db.execute(
        "SELECT dossier_json FROM dossiers WHERE project_id = ?", (project_id,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Dossier not found for {project_id}")

    return json.loads(row["dossier_json"])
