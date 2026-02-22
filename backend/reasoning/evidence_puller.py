"""Pull evidence bundles for each trigger from the database."""

from backend.db.connection import get_db


def pull_evidence(trigger):
    """
    Given a trigger row, query SQLite for relevant evidence:
      - field_notes ±7 days of trigger date, matching SOV lines if applicable
      - change_orders related to the affected SOV lines
      - rfis related to those COs or the SOV lines
      - material_deliveries for the affected SOV lines

    Returns a dict with: field_notes, related_cos, related_rfis, material_issues
    """
    db = get_db()
    pid = trigger["project_id"]
    trigger_date = trigger["date"]
    affected_sov = trigger["affected_sov_lines"] or ""
    sov_lines = [s.strip() for s in affected_sov.split(",") if s.strip()]

    # ── Field Notes ±7 days ──────────────────────────
    if trigger_date:
        notes = db.execute("""
            SELECT note_id, date, author, content
            FROM field_notes
            WHERE project_id = ?
              AND date BETWEEN date(?, '-7 days') AND date(?, '+7 days')
            ORDER BY date
            LIMIT 10
        """, (pid, trigger_date, trigger_date)).fetchall()
    else:
        notes = db.execute("""
            SELECT note_id, date, author, content
            FROM field_notes
            WHERE project_id = ?
            ORDER BY date DESC
            LIMIT 10
        """, (pid,)).fetchall()

    field_notes = []
    for n in notes:
        field_notes.append({
            "note_id": n["note_id"],
            "date": n["date"],
            "author": n["author"],
            "content": n["content"][:500],
        })

    # ── Change Orders for affected SOV lines ──────────
    related_cos = []
    if sov_lines:
        for sov_id in sov_lines[:3]:
            cos = db.execute("""
                SELECT co_number, amount, status, description, date_submitted,
                       affected_sov_lines, related_rfi
                FROM change_orders
                WHERE project_id = ?
                  AND affected_sov_lines LIKE ?
                ORDER BY date_submitted
            """, (pid, f"%{sov_id}%")).fetchall()
            for co in cos:
                related_cos.append({
                    "co_number": co["co_number"],
                    "amount": co["amount"],
                    "status": co["status"],
                    "description": co["description"][:200] if co["description"] else None,
                    "date_submitted": co["date_submitted"],
                })
    else:
        # For triggers without specific SOV lines (e.g., PENDING_CO), get all COs
        cos = db.execute("""
            SELECT co_number, amount, status, description, date_submitted,
                   affected_sov_lines, related_rfi
            FROM change_orders
            WHERE project_id = ?
            ORDER BY amount DESC
            LIMIT 10
        """, (pid,)).fetchall()
        for co in cos:
            related_cos.append({
                "co_number": co["co_number"],
                "amount": co["amount"],
                "status": co["status"],
                "description": co["description"][:200] if co["description"] else None,
                "date_submitted": co["date_submitted"],
            })

    # Deduplicate COs
    seen_cos = set()
    unique_cos = []
    for co in related_cos:
        if co["co_number"] not in seen_cos:
            seen_cos.add(co["co_number"])
            unique_cos.append(co)
    related_cos = unique_cos[:10]

    # ── RFIs related to the trigger ──────────────────
    related_rfis = []

    # Get RFIs linked via COs
    co_numbers = [co["co_number"] for co in related_cos]
    if co_numbers:
        placeholders = ",".join("?" * len(co_numbers))
        rfis_from_cos = db.execute(f"""
            SELECT DISTINCT r.rfi_number, r.subject, r.date_submitted,
                   r.date_responded, r.priority, r.cost_impact,
                   julianday('now') - julianday(r.date_submitted) as days_open
            FROM rfis r
            JOIN change_orders co ON co.related_rfi = r.rfi_number AND co.project_id = r.project_id
            WHERE r.project_id = ?
              AND co.co_number IN ({placeholders})
            LIMIT 5
        """, (pid, *co_numbers)).fetchall()
        for rfi in rfis_from_cos:
            related_rfis.append({
                "rfi_number": rfi["rfi_number"],
                "subject": rfi["subject"],
                "days_open": round(rfi["days_open"]) if rfi["days_open"] else 0,
                "priority": rfi["priority"],
                "cost_impact": rfi["cost_impact"],
            })

    # For ORPHAN_RFI triggers, include the specific RFI
    if trigger["type"] == "ORPHAN_RFI":
        import json
        metrics = json.loads(trigger["metrics_json"]) if trigger["metrics_json"] else {}
        rfi_num = metrics.get("rfi_number")
        if rfi_num and rfi_num not in [r["rfi_number"] for r in related_rfis]:
            rfi = db.execute("""
                SELECT rfi_number, subject, date_submitted, date_responded,
                       priority, cost_impact,
                       julianday('now') - julianday(date_submitted) as days_open
                FROM rfis
                WHERE project_id = ? AND rfi_number = ?
                LIMIT 1
            """, (pid, rfi_num)).fetchone()
            if rfi:
                related_rfis.append({
                    "rfi_number": rfi["rfi_number"],
                    "subject": rfi["subject"],
                    "days_open": round(rfi["days_open"]) if rfi["days_open"] else 0,
                    "priority": rfi["priority"],
                    "cost_impact": rfi["cost_impact"],
                })

    # ── Material issues for affected SOV lines ────────
    material_issues = []
    if sov_lines:
        for sov_id in sov_lines[:3]:
            deliveries = db.execute("""
                SELECT delivery_id, date, material_category, item_description,
                       quantity, unit_cost, total_cost, condition_notes
                FROM material_deliveries
                WHERE project_id = ? AND sov_line_id = ?
                ORDER BY date DESC
                LIMIT 5
            """, (pid, sov_id)).fetchall()
            for d in deliveries:
                material_issues.append({
                    "delivery_id": d["delivery_id"],
                    "date": d["date"],
                    "material_type": d["material_category"],
                    "total_cost": d["total_cost"],
                    "status": d["condition_notes"] or "Delivered",
                })

    return {
        "field_notes": field_notes,
        "related_cos": related_cos,
        "related_rfis": related_rfis,
        "material_issues": material_issues[:10],
    }
