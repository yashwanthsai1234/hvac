"""Run LLM reasoning on all 129 triggers via Claude Haiku and output a single dossiers.json.

Reads from:
  - backend/data/projects.jsonl   (5 lines — project context + financials)
  - backend/data/triggers.jsonl   (129 lines — trigger + metrics + evidence)

Outputs:
  - backend/data/dossiers.json    (single file — all 5 project dossiers with LLM reasoning)
  - Also stores each dossier in SQLite for API serving

Usage (run inside tmux):
    ANTHROPIC_API_KEY=sk-... python -m backend.scripts.run_reasoning
"""

import json
import os
import sys
import time

import anthropic

from backend.db.connection import get_db, init_db
from backend.reasoning.portfolio_builder import build_and_store_portfolio

# ── Paths ──────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PROJECTS_JSONL = os.path.join(DATA_DIR, "projects.jsonl")
TRIGGERS_JSONL = os.path.join(DATA_DIR, "triggers.jsonl")
OUTPUT_JSON = os.path.join(DATA_DIR, "dossiers.json")

# ── Haiku config ───────────────────────────────────────
MODEL = "claude-haiku-4-20250414"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are an expert HVAC construction financial analyst specializing in margin recovery for commercial mechanical contractors.

You analyze triggers — specific financial anomalies detected by our compute engine — and provide actionable reasoning.

Your analysis must be:
- Grounded in the exact numbers from the metrics and evidence provided
- Specific: reference actual CO numbers, RFI numbers, field note content, dollar amounts
- Actionable: every recovery action should have an estimated dollar value
- Honest about confidence level based on evidence quality

Respond with ONLY a JSON object, no other text."""


def build_user_prompt(trigger: dict) -> str:
    """Build the user prompt for a single trigger, injecting all context from JSONL."""
    ctx = trigger["project_context"]
    metrics = trigger["metrics"]
    evidence = trigger["evidence"]

    prompt = f"""Analyze this financial trigger and provide structured reasoning.

## Project
- Name: {ctx['project_name']} ({ctx['project_id']})
- Contract: ${ctx['contract_value']:,.0f}
- Health: {ctx['health_score']}/100 ({ctx['status']})
- Bid Margin: {ctx['bid_margin_pct']:.1f}% → Realized: {ctx['realized_margin_pct']:.1f}% (erosion: {ctx['margin_erosion_pct']:.1f}%)
- Est Cost: ${ctx['total_estimated_cost']:,.0f} | Actual Cost: ${ctx['total_actual_cost']:,.0f}

## Trigger
- ID: {trigger['trigger_id']}
- Type: {trigger['type']} | Severity: {trigger['severity']}
- Date: {trigger['date']}
- Headline: {trigger['headline']}
- Affected SOV Lines: {trigger['affected_sov_lines']}
- Metrics: {json.dumps(metrics, indent=2)}

## Evidence

### Field Notes (from job site, ±7 days)
"""
    for note in evidence.get("field_notes", [])[:8]:
        prompt += f"- [{note['date']}] {note['author']}: {note['content'][:400]}\n"
    if not evidence.get("field_notes"):
        prompt += "- No field notes for this period\n"

    prompt += "\n### Related Change Orders\n"
    for co in evidence.get("related_cos", [])[:8]:
        desc = co.get('description', 'N/A')
        if desc and len(desc) > 200:
            desc = desc[:200] + "..."
        prompt += f"- {co['co_number']}: ${co['amount']:,.0f} ({co['status']}) — {desc}\n"
    if not evidence.get("related_cos"):
        prompt += "- No related change orders\n"

    prompt += "\n### Related RFIs\n"
    for rfi in evidence.get("related_rfis", [])[:8]:
        prompt += f"- {rfi['rfi_number']}: {rfi['subject']} ({rfi['days_open']}d open, priority: {rfi['priority']}, cost_impact: {rfi.get('cost_impact', 'N/A')})\n"
    if not evidence.get("related_rfis"):
        prompt += "- No related RFIs\n"

    prompt += "\n### Material Deliveries\n"
    for mat in evidence.get("material_issues", [])[:5]:
        prompt += f"- {mat['delivery_id']}: {mat['material_type']} — ${mat['total_cost']:,.0f} ({mat.get('status', 'N/A')})\n"
    if not evidence.get("material_issues"):
        prompt += "- No material issues\n"

    prompt += """
## Required Output

Return a JSON object with these exact fields:

```json
{
  "root_cause": "Detailed paragraph explaining the root cause. Reference specific evidence — CO numbers, RFI numbers, field note quotes, exact dollar amounts.",
  "contributing_factors": [
    "Factor 1 — reference specific data points",
    "Factor 2 — reference specific data points",
    "Factor 3 — reference specific data points"
  ],
  "recovery_actions": [
    "Action 1 with estimated $ recovery amount",
    "Action 2 with estimated $ recovery amount",
    "Action 3 with estimated $ recovery amount"
  ],
  "recoverable_amount": 50000,
  "confidence": "HIGH or MEDIUM or LOW",
  "scoring": {
    "financial_impact": 98200,
    "recoverability_pct": 53,
    "schedule_risk_days": 5
  }
}
```"""
    return prompt


def parse_json_response(text: str) -> dict:
    """Extract JSON from Claude's response."""
    import re
    # Try code block first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Try raw JSON
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    raise ValueError(f"Could not parse JSON: {text[:200]}")


def run_reasoning():
    """Main: process all 129 triggers through Haiku and build dossiers.json."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # ── Load JSONL data ────────────────────────────────
    print("[REASONING] Loading JSONL data...")
    projects = {}
    with open(PROJECTS_JSONL) as f:
        for line in f:
            p = json.loads(line)
            projects[p["project_id"]] = p

    triggers_by_project = {}
    total_triggers = 0
    with open(TRIGGERS_JSONL) as f:
        for line in f:
            t = json.loads(line)
            pid = t["project_id"]
            if pid not in triggers_by_project:
                triggers_by_project[pid] = []
            triggers_by_project[pid].append(t)
            total_triggers += 1

    print(f"  {len(projects)} projects, {total_triggers} triggers loaded")

    # ── Process each trigger ───────────────────────────
    print(f"\n[REASONING] Calling {MODEL} for {total_triggers} triggers...")
    all_dossiers = {}
    processed = 0
    failed = 0
    start_time = time.time()

    for pid in sorted(projects.keys()):
        project = projects[pid]
        trigger_list = triggers_by_project.get(pid, [])
        print(f"\n  === {pid}: {project['project_name']} ({len(trigger_list)} triggers) ===")

        reasoned_triggers = []

        for trigger in trigger_list:
            processed += 1
            tid = trigger["trigger_id"]
            sys.stdout.write(f"    [{processed}/{total_triggers}] {tid}... ")
            sys.stdout.flush()

            try:
                user_prompt = build_user_prompt(trigger)

                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                text = response.content[0].text
                reasoning = parse_json_response(text)

                # Validate required fields
                for field in ["root_cause", "contributing_factors", "recovery_actions",
                              "recoverable_amount", "confidence"]:
                    if field not in reasoning:
                        reasoning[field] = "N/A" if isinstance(field, str) else 0

                if "scoring" not in reasoning:
                    reasoning["scoring"] = {
                        "financial_impact": 0,
                        "recoverability_pct": 0,
                        "schedule_risk_days": 0,
                    }

                print(f"OK ({reasoning['confidence']}, ${reasoning.get('recoverable_amount', 0):,.0f} recoverable)")

            except Exception as e:
                print(f"FAILED: {e}")
                failed += 1
                reasoning = {
                    "root_cause": f"LLM reasoning failed: {str(e)}",
                    "contributing_factors": ["API call unsuccessful"],
                    "recovery_actions": ["Retry reasoning or review manually"],
                    "recoverable_amount": 0,
                    "confidence": "LOW",
                    "scoring": {
                        "financial_impact": trigger["metrics"].get("overrun_cost", 0),
                        "recoverability_pct": 0,
                        "schedule_risk_days": 0,
                    },
                }

            # Assemble trigger with reasoning
            reasoned_triggers.append({
                "trigger_id": trigger["trigger_id"],
                "date": trigger["date"],
                "type": trigger["type"],
                "severity": trigger["severity"],
                "headline": trigger["headline"],
                "value": trigger["value"],
                "affected_sov_lines": trigger["affected_sov_lines"],
                "metrics": trigger["metrics"],
                "evidence": trigger["evidence"],
                "reasoning": reasoning,
            })

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        # ── Count by type ──────────────────────────────
        by_type = {}
        high_count = 0
        medium_count = 0
        for t in reasoned_triggers:
            by_type[t["type"]] = by_type.get(t["type"], 0) + 1
            if t["severity"] == "HIGH":
                high_count += 1
            elif t["severity"] == "MEDIUM":
                medium_count += 1

        # ── Assemble project dossier ───────────────────
        dossier = {
            "project_id": pid,
            "name": project["project_name"],
            "contract_value": project["contract_value"],
            "start_date": project["contract_date"],
            "end_date": project["completion_date"],
            "gc_name": project["gc_name"],
            "architect": project["architect"],
            "retention_pct": project["retention_pct"],
            "payment_terms": project["payment_terms"],
            "health_score": project["health_score"],
            "status": project["status"],
            "financials": project["financials"],
            "rfi_summary": project["rfi_summary"],
            "sov_lines": project["sov_lines"],
            "triggers": reasoned_triggers,
            "trigger_summary": {
                "total": len(reasoned_triggers),
                "high": high_count,
                "medium": medium_count,
                "by_type": by_type,
            },
        }

        all_dossiers[pid] = dossier

    elapsed = time.time() - start_time

    # ── Write single dossiers.json ─────────────────────
    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": MODEL,
        "total_triggers": total_triggers,
        "triggers_reasoned": processed - failed,
        "triggers_failed": failed,
        "projects": all_dossiers,
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[REASONING] Complete in {elapsed:.1f}s")
    print(f"  {processed - failed}/{total_triggers} triggers reasoned, {failed} failed")
    print(f"  Output: {OUTPUT_JSON}")

    # ── Also store in SQLite for API ───────────────────
    print("\n[REASONING] Storing dossiers in SQLite...")
    init_db()
    db = get_db()

    for pid, dossier in all_dossiers.items():
        db.execute("DELETE FROM dossiers WHERE project_id = ?", (pid,))
        db.execute(
            "INSERT INTO dossiers (project_id, dossier_json) VALUES (?, ?)",
            (pid, json.dumps(dossier)),
        )
    db.commit()

    # Build portfolio
    build_and_store_portfolio()
    print("[REASONING] SQLite updated. Done.")


if __name__ == "__main__":
    run_reasoning()
