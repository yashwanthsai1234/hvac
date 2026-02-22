"""Compute actual material cost per SOV line from material_deliveries."""

from backend.db.connection import get_db


def compute_material_metrics():
    """
    For each SOV line, compute:
      - actual_material_cost = SUM(material_deliveries.total_cost)
      - material_variance_pct = ((actual - estimated) / estimated) * 100
    Updates computed_sov_metrics (must run after labor.py populates it).
    """
    db = get_db()

    # Update actual material cost from deliveries
    db.execute("""
        UPDATE computed_sov_metrics
        SET actual_material_cost = COALESCE((
            SELECT SUM(md.total_cost)
            FROM material_deliveries md
            WHERE md.sov_line_id = computed_sov_metrics.sov_line_id
        ), 0)
    """)

    # Compute material variance pct
    db.execute("""
        UPDATE computed_sov_metrics
        SET material_variance_pct = CASE
            WHEN estimated_material_cost > 0
            THEN ((actual_material_cost - estimated_material_cost) / estimated_material_cost) * 100
            ELSE 0
        END
    """)

    db.commit()
    print("  materials.py: updated material costs for all SOV lines")
