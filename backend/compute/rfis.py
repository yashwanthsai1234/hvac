"""Compute RFI metrics per project."""

from backend.db.connection import get_db


def compute_rfi_metrics():
    """
    Per project, compute:
      - rfi_total: total RFIs
      - rfi_open: status not in ('Closed', 'Resolved')
      - rfi_overdue: date_required < date_responded or (date_required < 'today' and no response)
      - rfi_orphan_count: cost_impact is true but no matching CO with related_rfi
      - rfi_avg_response_days: average days between submitted and responded

    Updates computed_project_metrics.
    """
    db = get_db()

    projects = db.execute("SELECT project_id FROM contracts").fetchall()

    for proj in projects:
        pid = proj["project_id"]

        total = db.execute(
            "SELECT COUNT(*) FROM rfis WHERE project_id = ?", (pid,)
        ).fetchone()[0]

        open_count = db.execute("""
            SELECT COUNT(*) FROM rfis
            WHERE project_id = ? AND status NOT IN ('Closed', 'Resolved')
        """, (pid,)).fetchone()[0]

        # Overdue: date_required passed but not responded, or responded after required
        overdue = db.execute("""
            SELECT COUNT(*) FROM rfis
            WHERE project_id = ?
            AND date_required IS NOT NULL
            AND (
                (date_responded IS NULL AND date_required < date('now'))
                OR (date_responded IS NOT NULL AND date_responded > date_required)
            )
        """, (pid,)).fetchone()[0]

        # Orphan RFIs: cost_impact is true-ish but no change order references this RFI
        orphan = db.execute("""
            SELECT COUNT(*) FROM rfis r
            WHERE r.project_id = ?
            AND LOWER(r.cost_impact) IN ('true', 'yes', '1')
            AND NOT EXISTS (
                SELECT 1 FROM change_orders co
                WHERE co.related_rfi = r.rfi_number
                AND co.project_id = r.project_id
            )
        """, (pid,)).fetchone()[0]

        # Average response time (days) for responded RFIs
        avg_resp = db.execute("""
            SELECT AVG(julianday(date_responded) - julianday(date_submitted))
            FROM rfis
            WHERE project_id = ?
            AND date_responded IS NOT NULL
            AND date_submitted IS NOT NULL
        """, (pid,)).fetchone()[0]
        avg_resp = round(avg_resp, 1) if avg_resp else 0

        db.execute("""
            UPDATE computed_project_metrics
            SET rfi_total = ?,
                rfi_open = ?,
                rfi_overdue = ?,
                rfi_orphan_count = ?,
                rfi_avg_response_days = ?
            WHERE project_id = ?
        """, (total, open_count, overdue, orphan, avg_resp, pid))

    db.commit()
    print(f"  rfis.py: computed RFI metrics for {len(projects)} projects")
