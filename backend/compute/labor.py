"""Compute actual labor cost per SOV line from labor_logs."""

from backend.db.connection import get_db


def compute_labor_metrics():
    """
    For each (project_id, sov_line_id), compute:
      - actual_labor_cost = SUM((hours_st + hours_ot * 1.5) * hourly_rate * burden_multiplier)
      - actual_labor_hours = SUM(hours_st + hours_ot)
      - actual_labor_hours_ot = SUM(hours_ot)
      - estimated_labor_cost = sov_budget.estimated_labor_cost (internal burdened rate)
      - estimated_material_cost = scheduled_value * material_pct (billing rate — matches delivery costs)
      - estimated_labor_hours from sov_budget

    Data model notes:
      - labor_logs costs are at INTERNAL burdened rates → compare vs sov_budget.estimated_labor_cost
      - material_deliveries costs are at BILLING rates → compare vs scheduled_value * material_pct
      - sov_budget.estimated_material_cost is ~10% of delivery cost (internal handling only), NOT useful
    """
    db = get_db()

    # Ensure computed_sov_metrics is empty before we start
    db.execute("DELETE FROM computed_sov_metrics")

    # Insert a row for every SOV line with budget estimates
    # Labor estimate: sov_budget.estimated_labor_cost (internal burdened cost)
    # Material estimate: scheduled_value * material_pct (billing rate, matches delivery pricing)
    db.execute("""
        INSERT INTO computed_sov_metrics
            (sov_line_id, project_id, estimated_labor_cost, estimated_labor_hours,
             estimated_material_cost)
        SELECT
            s.sov_line_id,
            s.project_id,
            COALESCE(sb.estimated_labor_cost, 0),
            COALESCE(sb.estimated_labor_hours, 0),
            s.scheduled_value * s.material_pct
        FROM sov s
        LEFT JOIN sov_budget sb ON s.sov_line_id = sb.sov_line_id
    """)

    # Now compute actual labor from labor_logs and update
    db.execute("""
        UPDATE computed_sov_metrics
        SET
            actual_labor_cost = COALESCE((
                SELECT SUM((l.hours_st + l.hours_ot * 1.5) * l.hourly_rate * l.burden_multiplier)
                FROM labor_logs l
                WHERE l.sov_line_id = computed_sov_metrics.sov_line_id
            ), 0),
            actual_labor_hours = COALESCE((
                SELECT SUM(l.hours_st + l.hours_ot)
                FROM labor_logs l
                WHERE l.sov_line_id = computed_sov_metrics.sov_line_id
            ), 0),
            actual_labor_hours_ot = COALESCE((
                SELECT SUM(l.hours_ot)
                FROM labor_logs l
                WHERE l.sov_line_id = computed_sov_metrics.sov_line_id
            ), 0)
    """)

    # Compute labor overrun pct (hours-based using sov_budget estimated hours)
    db.execute("""
        UPDATE computed_sov_metrics
        SET labor_overrun_pct = CASE
            WHEN estimated_labor_hours > 0
            THEN ((actual_labor_hours - estimated_labor_hours) / estimated_labor_hours) * 100
            ELSE 0
        END
    """)

    db.commit()

    count = db.execute("SELECT COUNT(*) FROM computed_sov_metrics").fetchone()[0]
    print(f"  labor.py: computed {count} SOV line metrics")
