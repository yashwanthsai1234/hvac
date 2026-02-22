"""Compute health score (0-100) per project and assign RED/YELLOW/GREEN status."""

from backend.db.connection import get_db


def compute_health_scores():
    """
    Start at 100, deduct points per research.md:
      - Margin erosion > 2%:              -5 per 1% (max -25)
      - Labor overrun (worst SOV line):   -2 per 1% (max -20)
      - Billing lag > 3%:                 -3 per 1% (max -15)
      - Pending CO exposure > 1%:         -3 per 1% (max -15)
      - Orphan RFIs (cost impact, no CO): -3 per RFI (max -10)
      - Overdue RFIs:                     -2 per RFI (max -10)
      - Material variance > 5%:           -1 per 1% (max -5)

    Bands:
      80-100: GREEN
      50-79:  YELLOW
      0-49:   RED
    """
    db = get_db()

    projects = db.execute("SELECT * FROM computed_project_metrics").fetchall()

    for proj in projects:
        pid = proj["project_id"]
        score = 100

        # 1. Margin erosion
        erosion = proj["margin_erosion_pct"] or 0
        if erosion > 2:
            deduction = min(25, int((erosion - 2) * 5))
            score -= deduction

        # 2. Worst labor overrun across SOV lines
        worst_overrun = db.execute("""
            SELECT MAX(labor_overrun_pct) FROM computed_sov_metrics
            WHERE project_id = ?
        """, (pid,)).fetchone()[0] or 0
        if worst_overrun > 0:
            deduction = min(20, int(worst_overrun * 2))
            score -= deduction

        # 3. Billing lag
        billing_lag_pct = proj["billing_lag_pct"] or 0
        if billing_lag_pct > 3:
            deduction = min(15, int((billing_lag_pct - 3) * 3))
            score -= deduction

        # 4. Pending CO exposure
        pending_co = proj["pending_co_total"] or 0
        contract = proj["contract_value"] or 1
        pending_pct = (pending_co / contract) * 100
        if pending_pct > 1:
            deduction = min(15, int((pending_pct - 1) * 3))
            score -= deduction

        # 5. Orphan RFIs
        orphan_rfis = proj["rfi_orphan_count"] or 0
        if orphan_rfis > 0:
            deduction = min(10, orphan_rfis * 3)
            score -= deduction

        # 6. Overdue RFIs
        overdue_rfis = proj["rfi_overdue"] or 0
        if overdue_rfis > 0:
            deduction = min(10, overdue_rfis * 2)
            score -= deduction

        # 7. Material variance (worst SOV line)
        worst_mat_var = db.execute("""
            SELECT MAX(material_variance_pct) FROM computed_sov_metrics
            WHERE project_id = ?
        """, (pid,)).fetchone()[0] or 0
        if worst_mat_var > 5:
            deduction = min(5, int((worst_mat_var - 5) * 1))
            score -= deduction

        # Clamp to 0-100
        score = max(0, min(100, score))

        # Status bands
        if score >= 80:
            status = "GREEN"
        elif score >= 50:
            status = "YELLOW"
        else:
            status = "RED"

        db.execute("""
            UPDATE computed_project_metrics
            SET health_score = ?, status = ?
            WHERE project_id = ?
        """, (score, status, pid))

    db.commit()
    print(f"  health_score.py: computed health scores for {len(projects)} projects")
