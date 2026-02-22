You are an expert HVAC construction financial analyst. Your job is to analyze financial triggers detected across 5 commercial HVAC construction projects and produce reasoning for each one.

## Instructions

1. Read the file `backend/data/triggers.jsonl` — it has 129 lines, one JSON per trigger. Each line contains:
   - `trigger_id`, `type` (LABOR_OVERRUN or ORPHAN_RFI), `severity`, `headline`
   - `metrics` — computed financial scores (burn_ratio, overrun_cost, days_open, etc.)
   - `project_context` — project name, contract value, health score, margins
   - `evidence` — field_notes, related_cos, related_rfis, material_issues from the job site

2. Read the file `backend/data/projects.jsonl` — it has 5 lines, one JSON per project. Each contains full financial summary, SOV line breakdowns, and RFI summary.

3. For EACH of the 129 triggers, generate a reasoning object with these fields:
   - `root_cause`: One detailed paragraph. Reference specific CO numbers, RFI numbers, field note quotes, and exact dollar amounts from the evidence.
   - `contributing_factors`: Array of 3 strings, each referencing specific data points from the evidence.
   - `recovery_actions`: Array of 3 strings, each with a specific action and estimated dollar recovery.
   - `recoverable_amount`: Integer — estimated total dollars recoverable.
   - `confidence`: "HIGH", "MEDIUM", or "LOW" based on evidence quality.
   - `scoring`: Object with `financial_impact` (integer), `recoverability_pct` (0-100), `schedule_risk_days` (integer).

4. Assemble everything into a single JSON file at `backend/data/dossiers.json` with this structure:

```json
{
  "generated_at": "ISO timestamp",
  "model": "claude-code-haiku",
  "total_triggers": 129,
  "triggers_reasoned": 129,
  "triggers_failed": 0,
  "projects": {
    "PRJ-2024-001": {
      "project_id": "PRJ-2024-001",
      "name": "...",
      "contract_value": ...,
      "start_date": "...",
      "end_date": "...",
      "gc_name": "...",
      "architect": "...",
      "retention_pct": ...,
      "payment_terms": "...",
      "health_score": ...,
      "status": "...",
      "financials": { ... from projects.jsonl ... },
      "rfi_summary": { ... from projects.jsonl ... },
      "sov_lines": [ ... from projects.jsonl ... ],
      "triggers": [
        {
          "trigger_id": "...",
          "date": "...",
          "type": "...",
          "severity": "...",
          "headline": "...",
          "value": ...,
          "affected_sov_lines": "...",
          "metrics": { ... from triggers.jsonl ... },
          "evidence": { ... from triggers.jsonl ... },
          "reasoning": {
            "root_cause": "YOUR ANALYSIS HERE",
            "contributing_factors": ["...", "...", "..."],
            "recovery_actions": ["...", "...", "..."],
            "recoverable_amount": ...,
            "confidence": "...",
            "scoring": { "financial_impact": ..., "recoverability_pct": ..., "schedule_risk_days": ... }
          }
        }
      ],
      "trigger_summary": {
        "total": ...,
        "high": ...,
        "medium": ...,
        "by_type": { "LABOR_OVERRUN": ..., "ORPHAN_RFI": ... }
      }
    }
  }
}
```

## Guidelines for Analysis

**For LABOR_OVERRUN triggers:**
- Look at burn_ratio, overrun_pct, overrun_cost in metrics
- Check field notes for mentions of rework, delays, coordination issues, weather
- Check if related COs cover the additional scope
- Recovery actions: back-charges, CO submissions, productivity improvements
- Recoverable amount: typically 20-40% of overrun cost

**For ORPHAN_RFI triggers:**
- An RFI with cost_impact=true but no corresponding change order = revenue leakage
- Check days_open — longer means more risk
- Check priority — High priority RFIs need immediate CO filing
- Recovery actions: file CO immediately, document work performed, negotiate with GC
- Recoverable amount: estimate based on similar COs in evidence

**Confidence levels:**
- HIGH: Multiple evidence sources corroborate, clear dollar amounts
- MEDIUM: Some evidence supports analysis, estimates involved
- LOW: Limited evidence, speculative reasoning

## IMPORTANT

- Process ALL 129 triggers. Do not skip any.
- Write the output to `backend/data/dossiers.json` as valid JSON.
- The file will be large. That is expected.
- Also after writing dossiers.json, run this command to store dossiers in SQLite:
  `python3 -c "
import json
from backend.db.connection import get_db, init_db
from backend.reasoning.portfolio_builder import build_and_store_portfolio
init_db()
db = get_db()
with open('backend/data/dossiers.json') as f:
    data = json.load(f)
for pid, dossier in data['projects'].items():
    db.execute('DELETE FROM dossiers WHERE project_id = ?', (pid,))
    db.execute('INSERT INTO dossiers (project_id, dossier_json) VALUES (?, ?)', (pid, json.dumps(dossier)))
db.commit()
build_and_store_portfolio()
print('SQLite updated with', len(data['projects']), 'dossiers + portfolio')
"`
