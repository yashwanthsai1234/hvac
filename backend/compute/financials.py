"""Compute project-level financial rollups from SOV-line metrics."""

from backend.db.connection import get_db


def compute_project_financials():
    """
    Aggregate SOV-line metrics to project level. Compute margins, CO totals.
    Writes to computed_project_metrics.

    Cost model:
      - estimated_labor = SUM(sov_budget.estimated_labor_cost) — internal burdened rates
      - estimated_material = SUM(scheduled_value * material_pct) — billing rates (= delivery pricing)
      - total_estimated = estimated_labor + estimated_material
      - actual_labor from labor_logs (internal burdened rates)
      - actual_material from material_deliveries (billing rates)

    Margin calculation:
      - bid_margin = (contract_value - total_estimated) / contract_value
      - realized_margin uses projected total cost based on burn rate at current % complete
      - margin_erosion = bid_margin - realized_margin (positive = erosion)
    """
    db = get_db()
    db.execute("DELETE FROM computed_project_metrics")

    projects = db.execute("SELECT project_id, original_contract_value FROM contracts").fetchall()

    for proj in projects:
        pid = proj["project_id"]
        contract_value = proj["original_contract_value"]

        # Aggregate SOV-line actual costs
        sov_agg = db.execute("""
            SELECT
                COALESCE(SUM(actual_labor_cost), 0) as actual_labor,
                COALESCE(SUM(actual_material_cost), 0) as actual_material,
                COALESCE(SUM(estimated_labor_cost), 0) as est_labor,
                COALESCE(SUM(estimated_material_cost), 0) as est_material,
                COALESCE(SUM(total_billed), 0) as total_billed
            FROM computed_sov_metrics
            WHERE project_id = ?
        """, (pid,)).fetchone()

        # Estimated sub + equipment costs from sov_budget
        sub_equip = db.execute("""
            SELECT
                COALESCE(SUM(estimated_sub_cost), 0) as est_sub,
                COALESCE(SUM(estimated_equipment_cost), 0) as est_equip
            FROM sov_budget
            WHERE project_id = ?
        """, (pid,)).fetchone()

        # Change order totals by status
        co_approved = db.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM change_orders
            WHERE project_id = ? AND status = 'Approved'
        """, (pid,)).fetchone()[0]

        co_pending = db.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM change_orders
            WHERE project_id = ? AND status IN ('Pending', 'Under Review')
        """, (pid,)).fetchone()[0]

        co_rejected = db.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM change_orders
            WHERE project_id = ? AND status = 'Rejected'
        """, (pid,)).fetchone()[0]

        # Total estimated cost = internal labor budget + material (at billing rates) + sub + equip
        est_labor = sov_agg["est_labor"]
        est_material = sov_agg["est_material"]
        est_sub = sub_equip["est_sub"]
        total_estimated = est_labor + est_material + est_sub

        # Total actual cost TO DATE
        actual_labor = sov_agg["actual_labor"]
        actual_material = sov_agg["actual_material"]
        total_actual = actual_labor + actual_material

        # Overall percent complete (weighted by scheduled value from billing)
        pct_row = db.execute("""
            SELECT
                SUM(bi.pct_complete * s.scheduled_value) / SUM(s.scheduled_value) as weighted_pct
            FROM (
                SELECT sov_line_id, MAX(application_number) as max_app
                FROM billing_line_items
                WHERE project_id = ?
                GROUP BY sov_line_id
            ) latest
            JOIN billing_line_items bi
                ON bi.sov_line_id = latest.sov_line_id
                AND bi.application_number = latest.max_app
                AND bi.project_id = ?
            JOIN sov s ON s.sov_line_id = bi.sov_line_id
        """, (pid, pid)).fetchone()
        overall_pct_complete = pct_row["weighted_pct"] if pct_row and pct_row["weighted_pct"] else 0
        overall_pct_complete = overall_pct_complete / 100.0 if overall_pct_complete > 1 else overall_pct_complete

        adjusted_contract = contract_value + co_approved

        # Bid margin = (contract - estimated_cost) / contract
        # This will be high (~50-80%) because labor estimates are at internal rates
        # while materials at billing rates make up the bulk
        bid_margin_pct = ((contract_value - total_estimated) / contract_value * 100) if contract_value else 0

        # Projected total cost at completion = actual_to_date / pct_complete
        if overall_pct_complete > 0.05:
            projected_total_actual = total_actual / overall_pct_complete
        else:
            projected_total_actual = total_actual

        # Realized margin = projected final margin based on current burn rate
        realized_margin_pct = ((adjusted_contract - projected_total_actual) / adjusted_contract * 100) if adjusted_contract else 0

        # Margin erosion: positive = margins are shrinking
        margin_erosion_pct = bid_margin_pct - realized_margin_pct

        # Billing metrics
        cumulative_billed = sov_agg["total_billed"]
        earned_value = contract_value * overall_pct_complete
        billing_lag = earned_value - cumulative_billed
        billing_lag_pct = (billing_lag / contract_value * 100) if contract_value else 0

        db.execute("""
            INSERT INTO computed_project_metrics (
                project_id, contract_value, total_estimated_cost, total_actual_cost,
                actual_labor_cost, actual_material_cost,
                estimated_labor_cost, estimated_material_cost, estimated_sub_cost,
                approved_co_total, pending_co_total, rejected_co_total,
                adjusted_contract_value,
                bid_margin_pct, realized_margin_pct, margin_erosion_pct,
                cumulative_billed, earned_value, billing_lag, billing_lag_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pid, contract_value, total_estimated, total_actual,
            actual_labor, actual_material,
            est_labor, est_material,
            est_sub,
            co_approved, co_pending, co_rejected,
            adjusted_contract,
            round(bid_margin_pct, 2), round(realized_margin_pct, 2),
            round(margin_erosion_pct, 2),
            cumulative_billed, round(earned_value, 0), round(billing_lag, 0),
            round(billing_lag_pct, 2),
        ))

    db.commit()
    print(f"  financials.py: computed project-level metrics for {len(projects)} projects")
