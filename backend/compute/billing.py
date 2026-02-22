"""Compute billing lag per SOV line and per project."""

from backend.db.connection import get_db


def compute_billing_metrics():
    """
    For each SOV line:
      - total_billed = MAX(total_billed) from billing_line_items
        (latest application's cumulative total)
      - pct_complete = MAX(pct_complete) from billing_line_items
      - billing_lag = (actual_cost_spent - total_billed)
        where actual_cost = actual_labor_cost + actual_material_cost

    Updates computed_sov_metrics (must run after labor + materials).
    """
    db = get_db()

    # Get the latest billing snapshot per SOV line
    # (highest application_number = most recent billing period)
    db.execute("""
        UPDATE computed_sov_metrics
        SET
            total_billed = COALESCE((
                SELECT bi.total_billed
                FROM billing_line_items bi
                WHERE bi.sov_line_id = computed_sov_metrics.sov_line_id
                  AND bi.project_id = computed_sov_metrics.project_id
                ORDER BY bi.application_number DESC
                LIMIT 1
            ), 0),
            pct_complete = COALESCE((
                SELECT bi.pct_complete
                FROM billing_line_items bi
                WHERE bi.sov_line_id = computed_sov_metrics.sov_line_id
                  AND bi.project_id = computed_sov_metrics.project_id
                ORDER BY bi.application_number DESC
                LIMIT 1
            ), 0)
    """)

    # Billing lag = actual cost spent - total billed
    # Positive = we spent more than we billed (underbilling)
    db.execute("""
        UPDATE computed_sov_metrics
        SET billing_lag = (actual_labor_cost + actual_material_cost) - total_billed
    """)

    db.commit()
    print("  billing.py: updated billing metrics for all SOV lines")
