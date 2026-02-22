"""Build portfolio summary JSON from all project dossiers."""

import json

from backend.db.connection import get_db


def build_portfolio_summary():
    """
    Build portfolio.json summarizing all 5 projects.
    Reads from computed_project_metrics and contracts.

    Returns: dict (the portfolio summary)
    """
    db = get_db()

    projects = db.execute("""
        SELECT c.project_id, c.project_name, c.original_contract_value,
               c.contract_date, c.substantial_completion_date, c.gc_name,
               cpm.health_score, cpm.status,
               cpm.bid_margin_pct, cpm.realized_margin_pct, cpm.margin_erosion_pct,
               cpm.total_actual_cost, cpm.adjusted_contract_value,
               cpm.approved_co_total, cpm.pending_co_total,
               cpm.cumulative_billed, cpm.billing_lag_pct
        FROM contracts c
        LEFT JOIN computed_project_metrics cpm ON c.project_id = cpm.project_id
        ORDER BY c.project_id
    """).fetchall()

    project_summaries = []
    total_contract = 0
    total_at_risk = 0

    for p in projects:
        pid = p["project_id"]
        total_contract += p["original_contract_value"]

        # Count triggers
        trigger_count = db.execute(
            "SELECT COUNT(*) FROM triggers WHERE project_id = ?", (pid,)
        ).fetchone()[0]

        high_triggers = db.execute(
            "SELECT COUNT(*) FROM triggers WHERE project_id = ? AND severity = 'HIGH'",
            (pid,),
        ).fetchone()[0]

        # Erosion dollar amount
        erosion_pct = p["margin_erosion_pct"] or 0
        erosion_amount = p["original_contract_value"] * erosion_pct / 100

        if erosion_pct > 0:
            total_at_risk += erosion_amount

        summary = {
            "project_id": pid,
            "name": p["project_name"],
            "contract_value": p["original_contract_value"],
            "start_date": p["contract_date"],
            "end_date": p["substantial_completion_date"],
            "gc_name": p["gc_name"],
            "health_score": p["health_score"],
            "status": p["status"],
            "bid_margin_pct": p["bid_margin_pct"],
            "realized_margin_pct": p["realized_margin_pct"],
            "margin_erosion_pct": p["margin_erosion_pct"],
            "approved_cos": p["approved_co_total"],
            "pending_cos": p["pending_co_total"],
            "billing_lag_pct": p["billing_lag_pct"],
            "trigger_count": trigger_count,
            "high_trigger_count": high_triggers,
        }
        project_summaries.append(summary)

    # Portfolio-level stats
    scores = [p["health_score"] for p in project_summaries if p["health_score"] is not None]
    statuses = [p["status"] for p in project_summaries if p["status"]]

    portfolio = {
        "portfolio_health": round(sum(scores) / len(scores)) if scores else 0,
        "total_contract_value": total_contract,
        "total_at_risk": round(total_at_risk),
        "project_count": len(projects),
        "at_risk_count": statuses.count("RED"),
        "watch_count": statuses.count("YELLOW"),
        "healthy_count": statuses.count("GREEN"),
        "projects": project_summaries,
    }

    return portfolio


def build_and_store_portfolio():
    """Build portfolio summary and store in SQLite dossiers table."""
    db = get_db()
    portfolio = build_portfolio_summary()
    portfolio_json = json.dumps(portfolio)

    db.execute("DELETE FROM dossiers WHERE project_id = 'PORTFOLIO'")
    db.execute(
        "INSERT INTO dossiers (project_id, dossier_json) VALUES (?, ?)",
        ("PORTFOLIO", portfolio_json),
    )
    db.commit()

    print(f"  portfolio_builder.py: built portfolio summary ({portfolio['project_count']} projects, "
          f"health={portfolio['portfolio_health']}/100)")
    return portfolio
