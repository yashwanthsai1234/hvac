"""Tool: query labor detail for a project, aggregated by SOV line and role."""

from backend.db.connection import get_db


def get_labor_detail(
    project_id: str,
    sov_line_id: str = None,
) -> dict:
    """Return labour hours/cost aggregated by SOV line, with per-role breakdown.

    Parameters
    ----------
    project_id : str
        The project to query.
    sov_line_id : str, optional
        If provided, restrict results to a single SOV line.

    Returns
    -------
    dict
        {
            "project_id": str,
            "hours_st": float,
            "hours_ot": float,
            "total_cost": float,
            "by_sov_line": [
                {
                    "sov_line_id": str,
                    "hours_st": float,
                    "hours_ot": float,
                    "total_cost": float,
                    "roles": [
                        {
                            "role": str,
                            "hours_st": float,
                            "hours_ot": float,
                            "total_cost": float,
                        }
                    ]
                }
            ]
        }
    """
    db = get_db()

    # ------------------------------------------------------------------
    # Build the base WHERE clause
    # ------------------------------------------------------------------
    where = "WHERE project_id = ?"
    params: list = [project_id]

    if sov_line_id is not None:
        where += " AND sov_line_id = ?"
        params.append(sov_line_id)

    # ------------------------------------------------------------------
    # Project-level totals
    # ------------------------------------------------------------------
    totals_sql = (
        "SELECT "
        "  COALESCE(SUM(hours_st), 0)  AS hours_st, "
        "  COALESCE(SUM(hours_ot), 0)  AS hours_ot, "
        "  COALESCE(SUM((hours_st + hours_ot * 1.5) * hourly_rate * burden_multiplier), 0) AS total_cost "
        f"FROM labor_logs {where}"
    )
    totals_row = db.execute(totals_sql, params).fetchone()

    result: dict = {
        "project_id": project_id,
        "hours_st": totals_row["hours_st"],
        "hours_ot": totals_row["hours_ot"],
        "total_cost": round(totals_row["total_cost"], 2),
        "by_sov_line": [],
    }

    # ------------------------------------------------------------------
    # Per-SOV-line totals
    # ------------------------------------------------------------------
    line_sql = (
        "SELECT "
        "  sov_line_id, "
        "  COALESCE(SUM(hours_st), 0)  AS hours_st, "
        "  COALESCE(SUM(hours_ot), 0)  AS hours_ot, "
        "  COALESCE(SUM((hours_st + hours_ot * 1.5) * hourly_rate * burden_multiplier), 0) AS total_cost "
        f"FROM labor_logs {where} "
        "GROUP BY sov_line_id "
        "ORDER BY sov_line_id"
    )
    line_rows = db.execute(line_sql, params).fetchall()

    for line_row in line_rows:
        line_id = line_row["sov_line_id"]

        # Per-role breakdown within this SOV line
        role_sql = (
            "SELECT "
            "  role, "
            "  COALESCE(SUM(hours_st), 0)  AS hours_st, "
            "  COALESCE(SUM(hours_ot), 0)  AS hours_ot, "
            "  COALESCE(SUM((hours_st + hours_ot * 1.5) * hourly_rate * burden_multiplier), 0) AS total_cost "
            "FROM labor_logs "
            "WHERE project_id = ? AND sov_line_id = ? "
            "GROUP BY role "
            "ORDER BY role"
        )
        role_rows = db.execute(role_sql, [project_id, line_id]).fetchall()

        roles = [
            {
                "role": r["role"],
                "hours_st": r["hours_st"],
                "hours_ot": r["hours_ot"],
                "total_cost": round(r["total_cost"], 2),
            }
            for r in role_rows
        ]

        result["by_sov_line"].append(
            {
                "sov_line_id": line_id,
                "hours_st": line_row["hours_st"],
                "hours_ot": line_row["hours_ot"],
                "total_cost": round(line_row["total_cost"], 2),
                "roles": roles,
            }
        )

    return result
