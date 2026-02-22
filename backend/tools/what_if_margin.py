"""Tool: run what-if margin scenarios for a project."""

from backend.db.connection import get_db

_VALID_SCENARIOS = {"co_rejected", "co_approved", "labor_recovery"}


def what_if_margin(
    project_id: str,
    scenario: str,
    co_number: str = None,
) -> dict:
    """Compute a before/after margin comparison for a hypothetical scenario.

    Supported scenarios
    -------------------
    * **co_rejected** -- Remove a specific CO's approved amount from the
      adjusted contract value.  Requires *co_number*.
    * **co_approved** -- Assume a pending CO is approved and add its amount
      to the adjusted contract value.  Requires *co_number*.
    * **labor_recovery** -- Simulate a 10 % reduction in actual labour cost.

    Parameters
    ----------
    project_id : str
        The project to evaluate.
    scenario : str
        One of ``co_rejected``, ``co_approved``, ``labor_recovery``.
    co_number : str, optional
        Required for the ``co_rejected`` and ``co_approved`` scenarios.

    Returns
    -------
    dict
        {
            "project_id": str,
            "scenario": str,
            "co_number": str | None,
            "before": { ... metrics snapshot ... },
            "after":  { ... adjusted metrics ... },
            "delta": { ... difference ... },
        }
    """
    if scenario not in _VALID_SCENARIOS:
        return {
            "error": f"Unknown scenario '{scenario}'. "
            f"Choose from: {', '.join(sorted(_VALID_SCENARIOS))}."
        }

    if scenario in ("co_rejected", "co_approved") and co_number is None:
        return {"error": f"Scenario '{scenario}' requires a co_number."}

    db = get_db()

    # ------------------------------------------------------------------
    # Fetch current project metrics
    # ------------------------------------------------------------------
    metrics_row = db.execute(
        "SELECT contract_value, adjusted_contract_value, "
        "       total_actual_cost, actual_labor_cost, actual_material_cost, "
        "       approved_co_total, pending_co_total, "
        "       total_estimated_cost, bid_margin_pct, realized_margin_pct "
        "FROM computed_project_metrics "
        "WHERE project_id = ?",
        [project_id],
    ).fetchone()

    if metrics_row is None:
        return {"error": f"No computed metrics found for project '{project_id}'."}

    contract_value = metrics_row["contract_value"] or 0.0
    adjusted_cv = metrics_row["adjusted_contract_value"] or 0.0
    total_actual_cost = metrics_row["total_actual_cost"] or 0.0
    actual_labor_cost = metrics_row["actual_labor_cost"] or 0.0
    actual_material_cost = metrics_row["actual_material_cost"] or 0.0
    approved_co_total = metrics_row["approved_co_total"] or 0.0
    pending_co_total = metrics_row["pending_co_total"] or 0.0
    total_estimated_cost = metrics_row["total_estimated_cost"] or 0.0
    bid_margin_pct = metrics_row["bid_margin_pct"] or 0.0
    realized_margin_pct = metrics_row["realized_margin_pct"] or 0.0

    before = {
        "contract_value": contract_value,
        "adjusted_contract_value": adjusted_cv,
        "total_actual_cost": total_actual_cost,
        "actual_labor_cost": actual_labor_cost,
        "actual_material_cost": actual_material_cost,
        "approved_co_total": approved_co_total,
        "pending_co_total": pending_co_total,
        "bid_margin_pct": bid_margin_pct,
        "realized_margin_pct": realized_margin_pct,
    }

    # Start with current values for the "after" state
    after_cv = adjusted_cv
    after_actual_cost = total_actual_cost
    after_labor_cost = actual_labor_cost
    after_approved_co = approved_co_total
    after_pending_co = pending_co_total

    # ------------------------------------------------------------------
    # Apply scenario adjustments
    # ------------------------------------------------------------------
    co_amount = 0.0

    if scenario in ("co_rejected", "co_approved"):
        co_row = db.execute(
            "SELECT amount, status FROM change_orders "
            "WHERE project_id = ? AND co_number = ?",
            [project_id, co_number],
        ).fetchone()

        if co_row is None:
            return {
                "error": f"Change order '{co_number}' not found "
                f"for project '{project_id}'."
            }

        co_amount = co_row["amount"] or 0.0

    if scenario == "co_rejected":
        # Simulate removing an approved CO from the contract value
        after_cv -= co_amount
        after_approved_co -= co_amount

    elif scenario == "co_approved":
        # Simulate approving a pending CO
        after_cv += co_amount
        after_approved_co += co_amount
        after_pending_co -= co_amount

    elif scenario == "labor_recovery":
        # Reduce actual labour cost by 10 %
        savings = actual_labor_cost * 0.10
        after_labor_cost -= savings
        after_actual_cost -= savings

    # ------------------------------------------------------------------
    # Recompute realized margin
    # ------------------------------------------------------------------
    def _margin_pct(revenue: float, cost: float) -> float:
        if revenue == 0:
            return 0.0
        return round((revenue - cost) / revenue * 100, 2)

    after_realized_margin = _margin_pct(after_cv, after_actual_cost)

    after = {
        "contract_value": contract_value,
        "adjusted_contract_value": round(after_cv, 2),
        "total_actual_cost": round(after_actual_cost, 2),
        "actual_labor_cost": round(after_labor_cost, 2),
        "actual_material_cost": actual_material_cost,
        "approved_co_total": round(after_approved_co, 2),
        "pending_co_total": round(after_pending_co, 2),
        "bid_margin_pct": bid_margin_pct,
        "realized_margin_pct": after_realized_margin,
    }

    delta = {key: round(after[key] - before[key], 2) for key in before}

    return {
        "project_id": project_id,
        "scenario": scenario,
        "co_number": co_number,
        "before": before,
        "after": after,
        "delta": delta,
    }
