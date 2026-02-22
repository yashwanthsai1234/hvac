"""Compute engine orchestrator — runs all computation steps in order."""

from backend.compute.labor import compute_labor_metrics
from backend.compute.materials import compute_material_metrics
from backend.compute.billing import compute_billing_metrics
from backend.compute.financials import compute_project_financials
from backend.compute.rfis import compute_rfi_metrics
from backend.compute.health_score import compute_health_scores
from backend.compute.triggers import compute_triggers


def run_compute_engine():
    """Run all compute steps in dependency order."""
    print("\n[COMPUTE ENGINE] Starting...")

    # Step 1: SOV-line level metrics
    compute_labor_metrics()
    compute_material_metrics()
    compute_billing_metrics()

    # Step 2: Project-level rollups
    compute_project_financials()
    compute_rfi_metrics()

    # Step 3: Health scores (depends on financials + RFIs)
    compute_health_scores()

    # Step 4: Trigger detection (depends on all above)
    compute_triggers()

    print("[COMPUTE ENGINE] Done.\n")
