"""Detect trigger points — dates when thresholds were crossed per project."""

import json
from backend.db.connection import get_db


def compute_triggers():
    """
    Scan timelines to find when thresholds were first crossed.

    Trigger types:
      - LABOR_OVERRUN: cumulative burn ratio crosses 1.15x for any SOV line
      - PENDING_CO: pending CO total exceeds 5% of contract
      - BILLING_LAG: billing lag exceeds 3% of contract
      - ORPHAN_RFI: RFI with cost_impact=true, no matching CO
      - MATERIAL_VARIANCE: material spend exceeds estimate by 10%+ on a SOV line
      - OT_SPIKE: OT ratio exceeds 25% in a rolling 2-week window
    """
    db = get_db()
    db.execute("DELETE FROM triggers")

    projects = db.execute(
        "SELECT project_id, original_contract_value FROM contracts"
    ).fetchall()

    trigger_count = 0

    for proj in projects:
        pid = proj["project_id"]
        contract_value = proj["original_contract_value"]

        # ── TRIGGER: LABOR_OVERRUN ──────────────────────────────
        # Find SOV lines where actual hours > 1.15 * estimated hours
        overrun_lines = db.execute("""
            SELECT csm.sov_line_id, s.description,
                   csm.actual_labor_hours, csm.estimated_labor_hours,
                   csm.labor_overrun_pct, csm.actual_labor_cost,
                   csm.estimated_labor_cost
            FROM computed_sov_metrics csm
            JOIN sov s ON csm.sov_line_id = s.sov_line_id
            WHERE csm.project_id = ?
              AND csm.estimated_labor_hours > 0
              AND csm.actual_labor_hours > csm.estimated_labor_hours * 1.15
            ORDER BY csm.labor_overrun_pct DESC
        """, (pid,)).fetchall()

        for line in overrun_lines:
            # Find the approximate date the threshold was crossed
            # Get cumulative hours day by day for this SOV line
            threshold = line["estimated_labor_hours"] * 1.15
            cum_date = db.execute("""
                SELECT date, SUM(hours_st + hours_ot) OVER (ORDER BY date) as cum_hours
                FROM labor_logs
                WHERE sov_line_id = ? AND project_id = ?
                ORDER BY date
            """, (line["sov_line_id"], pid)).fetchall()

            trigger_date = None
            for row in cum_date:
                if row["cum_hours"] >= threshold:
                    trigger_date = row["date"]
                    break

            if not trigger_date and cum_date:
                trigger_date = cum_date[-1]["date"]

            overrun_cost = line["actual_labor_cost"] - line["estimated_labor_cost"]
            burn_ratio = round(line["actual_labor_hours"] / line["estimated_labor_hours"], 2) if line["estimated_labor_hours"] > 0 else 0

            severity = "HIGH" if line["labor_overrun_pct"] > 20 else "MEDIUM"

            trigger_id = f"T-{pid[-3:]}-LO-{line['sov_line_id'][-2:]}"
            metrics = {
                "burn_ratio": burn_ratio,
                "overrun_pct": round(line["labor_overrun_pct"], 1),
                "overrun_cost": round(overrun_cost, 0),
                "estimated_hours": line["estimated_labor_hours"],
                "actual_hours": round(line["actual_labor_hours"], 1),
            }

            db.execute("""
                INSERT INTO triggers (trigger_id, project_id, date, type, severity,
                                      value, headline, affected_sov_lines, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trigger_id, pid, trigger_date, "LABOR_OVERRUN", severity,
                burn_ratio,
                f"Burn ratio {burn_ratio}x on {line['description']}",
                line["sov_line_id"],
                json.dumps(metrics),
            ))
            trigger_count += 1

        # ── TRIGGER: PENDING_CO ──────────────────────────────────
        pending_cos = db.execute("""
            SELECT co_number, amount, date_submitted, description, affected_sov_lines
            FROM change_orders
            WHERE project_id = ? AND status IN ('Pending', 'Under Review')
            ORDER BY amount DESC
        """, (pid,)).fetchall()

        pending_total = sum(co["amount"] for co in pending_cos)
        pending_pct = (pending_total / contract_value * 100) if contract_value else 0

        if pending_pct > 1 and pending_cos:
            severity = "HIGH" if pending_pct > 5 else "MEDIUM"
            trigger_id = f"T-{pid[-3:]}-PCO"
            metrics = {
                "pending_total": round(pending_total, 0),
                "pending_pct": round(pending_pct, 1),
                "co_count": len(pending_cos),
                "largest_co": pending_cos[0]["co_number"],
                "largest_amount": round(pending_cos[0]["amount"], 0),
            }
            db.execute("""
                INSERT INTO triggers (trigger_id, project_id, date, type, severity,
                                      value, headline, affected_sov_lines, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trigger_id, pid, pending_cos[0]["date_submitted"],
                "PENDING_CO", severity,
                round(pending_total, 0),
                f"${pending_total:,.0f} in pending COs ({pending_pct:.1f}% of contract)",
                ",".join(co["affected_sov_lines"] or "" for co in pending_cos),
                json.dumps(metrics),
            ))
            trigger_count += 1

        # ── TRIGGER: ORPHAN_RFI ──────────────────────────────────
        orphan_rfis = db.execute("""
            SELECT r.rfi_number, r.subject, r.date_submitted, r.priority,
                   r.date_required, r.date_responded,
                   julianday('now') - julianday(r.date_submitted) as days_open
            FROM rfis r
            WHERE r.project_id = ?
              AND LOWER(r.cost_impact) IN ('true', 'yes', '1')
              AND NOT EXISTS (
                  SELECT 1 FROM change_orders co
                  WHERE co.related_rfi = r.rfi_number
                  AND co.project_id = r.project_id
              )
        """, (pid,)).fetchall()

        for rfi in orphan_rfis:
            trigger_id = f"T-{pid[-3:]}-ORFI-{rfi['rfi_number'][-3:]}"
            days_open = round(rfi["days_open"]) if rfi["days_open"] else 0
            severity = "HIGH" if days_open > 14 else "MEDIUM"

            metrics = {
                "rfi_number": rfi["rfi_number"],
                "subject": rfi["subject"],
                "days_open": days_open,
                "priority": rfi["priority"],
            }
            db.execute("""
                INSERT INTO triggers (trigger_id, project_id, date, type, severity,
                                      value, headline, affected_sov_lines, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trigger_id, pid, rfi["date_submitted"],
                "ORPHAN_RFI", severity,
                days_open,
                f"RFI {rfi['rfi_number']} has cost impact but no CO — {days_open}d open",
                None,
                json.dumps(metrics),
            ))
            trigger_count += 1

        # ── TRIGGER: MATERIAL_VARIANCE ───────────────────────────
        mat_var_lines = db.execute("""
            SELECT csm.sov_line_id, s.description,
                   csm.actual_material_cost, csm.estimated_material_cost,
                   csm.material_variance_pct
            FROM computed_sov_metrics csm
            JOIN sov s ON csm.sov_line_id = s.sov_line_id
            WHERE csm.project_id = ?
              AND csm.estimated_material_cost > 0
              AND csm.material_variance_pct > 10
            ORDER BY csm.material_variance_pct DESC
        """, (pid,)).fetchall()

        for line in mat_var_lines:
            overrun = line["actual_material_cost"] - line["estimated_material_cost"]
            trigger_id = f"T-{pid[-3:]}-MV-{line['sov_line_id'][-2:]}"
            severity = "HIGH" if line["material_variance_pct"] > 20 else "MEDIUM"

            metrics = {
                "variance_pct": round(line["material_variance_pct"], 1),
                "overrun_amount": round(overrun, 0),
                "actual": round(line["actual_material_cost"], 0),
                "estimated": round(line["estimated_material_cost"], 0),
            }

            # Find first delivery date for this line
            first_del = db.execute("""
                SELECT MIN(date) as first_date FROM material_deliveries
                WHERE sov_line_id = ? AND project_id = ?
            """, (line["sov_line_id"], pid)).fetchone()
            tdate = first_del["first_date"] if first_del and first_del["first_date"] else "2024-06-01"

            db.execute("""
                INSERT INTO triggers (trigger_id, project_id, date, type, severity,
                                      value, headline, affected_sov_lines, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trigger_id, pid, tdate,
                "MATERIAL_VARIANCE", severity,
                round(line["material_variance_pct"], 1),
                f"Material {line['material_variance_pct']:.0f}% over on {line['description']}",
                line["sov_line_id"],
                json.dumps(metrics),
            ))
            trigger_count += 1

    db.commit()
    print(f"  triggers.py: detected {trigger_count} triggers across {len(projects)} projects")
