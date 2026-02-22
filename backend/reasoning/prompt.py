"""Prompt templates for Haiku reasoning on triggers."""


def build_reasoning_prompt(trigger, evidence, project_context):
    """
    Build a prompt for Haiku to reason about a specific trigger.

    Args:
        trigger: dict with trigger_id, type, severity, headline, metrics_json
        evidence: dict with field_notes, related_cos, related_rfis, material_issues
        project_context: dict with project_name, contract_value, health_score, etc.

    Returns:
        str: The prompt to send to Haiku
    """
    import json

    metrics = json.loads(trigger["metrics_json"]) if trigger["metrics_json"] else {}

    prompt = f"""You are an expert HVAC construction financial analyst. Analyze this trigger event and provide structured reasoning.

## Project Context
- Project: {project_context['project_name']} ({project_context['project_id']})
- Contract Value: ${project_context['contract_value']:,.0f}
- Health Score: {project_context.get('health_score', 'N/A')}/100 ({project_context.get('status', 'N/A')})
- Bid Margin: {project_context.get('bid_margin_pct', 'N/A')}%
- Realized Margin: {project_context.get('realized_margin_pct', 'N/A')}%

## Trigger Details
- Type: {trigger['type']}
- Severity: {trigger['severity']}
- Date: {trigger['date']}
- Headline: {trigger['headline']}
- Metrics: {json.dumps(metrics, indent=2)}

## Evidence

### Field Notes (±7 days of trigger)
"""
    for note in evidence.get("field_notes", [])[:5]:
        prompt += f"- [{note['date']}] {note['author']}: {note['content']}\n"

    if not evidence.get("field_notes"):
        prompt += "- No field notes found for this period\n"

    prompt += "\n### Related Change Orders\n"
    for co in evidence.get("related_cos", [])[:5]:
        prompt += f"- {co['co_number']}: ${co['amount']:,.0f} ({co['status']}) — {co.get('description', 'N/A')}\n"

    if not evidence.get("related_cos"):
        prompt += "- No related change orders\n"

    prompt += "\n### Related RFIs\n"
    for rfi in evidence.get("related_rfis", [])[:5]:
        prompt += f"- {rfi['rfi_number']}: {rfi['subject']} ({rfi['days_open']}d open, priority: {rfi['priority']})\n"

    if not evidence.get("related_rfis"):
        prompt += "- No related RFIs\n"

    prompt += "\n### Material Deliveries\n"
    for mat in evidence.get("material_issues", [])[:5]:
        prompt += f"- {mat['delivery_id']}: {mat['material_type']} — ${mat['total_cost']:,.0f} ({mat['status']})\n"

    if not evidence.get("material_issues"):
        prompt += "- No material issues\n"

    prompt += """
## Your Task

Based on the trigger metrics and evidence above, provide analysis in the following JSON format. Be specific — reference actual CO numbers, RFI numbers, field note content, and dollar amounts from the evidence.

```json
{
  "root_cause": "One paragraph explaining the primary root cause, referencing specific evidence",
  "contributing_factors": [
    "Factor 1 with specific reference",
    "Factor 2 with specific reference",
    "Factor 3 with specific reference"
  ],
  "recovery_actions": [
    "Specific action 1 with estimated $ recovery",
    "Specific action 2 with estimated $ recovery",
    "Specific action 3 with estimated $ recovery"
  ],
  "recoverable_amount": 50000,
  "confidence": "HIGH or MEDIUM or LOW",
  "scoring": {
    "financial_impact": 98200,
    "recoverability_pct": 53,
    "schedule_risk_days": 5
  }
}
```

Respond with ONLY the JSON block, no other text.
"""
    return prompt
