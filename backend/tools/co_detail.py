"""Tool: query change-order details for a project."""

from backend.db.connection import get_db


def get_co_detail(
    project_id: str,
    co_number: str = None,
) -> list[dict]:
    """Return change-order records for a project, optionally filtered by CO number.

    Parameters
    ----------
    project_id : str
        The project to query.
    co_number : str, optional
        If provided, return only the matching change order(s).

    Returns
    -------
    list[dict]
        Each dict mirrors the change_orders table columns.
    """
    db = get_db()

    sql = (
        "SELECT co_number, project_id, date_submitted, reason_category, "
        "       description, amount, status, related_rfi, affected_sov_lines, "
        "       labor_hours_impact, schedule_impact_days, submitted_by, approved_by "
        "FROM change_orders "
        "WHERE project_id = ?"
    )
    params: list = [project_id]

    if co_number is not None:
        sql += " AND co_number = ?"
        params.append(co_number)

    sql += " ORDER BY date_submitted DESC"

    rows = db.execute(sql, params).fetchall()

    return [
        {
            "co_number": row["co_number"],
            "project_id": row["project_id"],
            "date_submitted": row["date_submitted"],
            "reason_category": row["reason_category"],
            "description": row["description"],
            "amount": row["amount"],
            "status": row["status"],
            "related_rfi": row["related_rfi"],
            "affected_sov_lines": row["affected_sov_lines"],
            "labor_hours_impact": row["labor_hours_impact"],
            "schedule_impact_days": row["schedule_impact_days"],
            "submitted_by": row["submitted_by"],
            "approved_by": row["approved_by"],
        }
        for row in rows
    ]
