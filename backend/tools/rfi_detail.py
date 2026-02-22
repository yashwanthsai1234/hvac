"""Tool: query RFI details for a project."""

from backend.db.connection import get_db


def get_rfi_detail(
    project_id: str,
    rfi_number: str = None,
) -> list[dict]:
    """Return RFI records for a project, optionally filtered by RFI number.

    Parameters
    ----------
    project_id : str
        The project to query.
    rfi_number : str, optional
        If provided, return only the matching RFI(s).

    Returns
    -------
    list[dict]
        Each dict mirrors the rfis table columns.
    """
    db = get_db()

    sql = (
        "SELECT rfi_number, project_id, date_submitted, subject, "
        "       submitted_by, assigned_to, priority, status, "
        "       date_required, date_responded, response_summary, "
        "       cost_impact, schedule_impact "
        "FROM rfis "
        "WHERE project_id = ?"
    )
    params: list = [project_id]

    if rfi_number is not None:
        sql += " AND rfi_number = ?"
        params.append(rfi_number)

    sql += " ORDER BY date_submitted DESC"

    rows = db.execute(sql, params).fetchall()

    return [
        {
            "rfi_number": row["rfi_number"],
            "project_id": row["project_id"],
            "date_submitted": row["date_submitted"],
            "subject": row["subject"],
            "submitted_by": row["submitted_by"],
            "assigned_to": row["assigned_to"],
            "priority": row["priority"],
            "status": row["status"],
            "date_required": row["date_required"],
            "date_responded": row["date_responded"],
            "response_summary": row["response_summary"],
            "cost_impact": row["cost_impact"],
            "schedule_impact": row["schedule_impact"],
        }
        for row in rows
    ]
