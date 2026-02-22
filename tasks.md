# HVAC Margin Rescue Agent — Implementation Plan

---

## Overview

```
  5 PHASES — BUILD, TEST, ADVANCE
  ════════════════════════════════

  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ PHASE 1  │──►│ PHASE 2  │──►│ PHASE 3  │──►│ PHASE 4  │──►│ PHASE 5  │
  │          │   │          │   │          │   │          │   │          │
  │ DATA     │   │ COMPUTE  │   │ REASONING│   │ FRONTEND │   │ CHAT +   │
  │ FOUNDATION   │ ENGINE   │   │ ENGINE   │   │ UI       │   │ DEPLOY   │
  │          │   │          │   │          │   │          │   │          │
  │ SQLite   │   │ Metrics  │   │ Haiku    │   │ v0       │   │ Vercel   │
  │ + CSVs   │   │ + Scores │   │ + tmux   │   │ scaffold │   │ AI SDK   │
  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
       │              │              │              │              │
       ▼              ▼              ▼              ▼              ▼
    TEST 1         TEST 2         TEST 3         TEST 4         TEST 5
    Data           Math           Reasoning      Render         End-to-end
    integrity      correctness    quality        + routing      full flow
```

**Tech Stack**: **FastAPI** (Python backend) + **Next.js** (frontend), SQLite, v0 scaffolded UI, Vercel AI SDK, Claude Haiku via Claude Code tmux

```
  TWO-SERVICE ARCHITECTURE
  ════════════════════════

  ┌─────────────────────────┐          ┌─────────────────────────┐
  │  FRONTEND (Next.js)     │          │  BACKEND (FastAPI)      │
  │                         │   HTTP   │                         │
  │  v0 scaffolded UI       │ ◄──────► │  Python compute engine  │
  │  Vercel AI SDK (chat)   │   JSON   │  SQLite database        │
  │  Components + pages     │          │  Haiku reasoning        │
  │  Deployed on Vercel     │          │  All data APIs          │
  │                         │          │  Chat endpoint          │
  │  Port 3000              │          │  Port 8000              │
  └─────────────────────────┘          └─────────────────────────┘

  WHY THIS SPLIT?
  ───────────────
  - Python is better for data wrangling (pandas, numpy)
  - FastAPI is fast, typed, auto-generates OpenAPI docs
  - Next.js stays thin — just UI rendering + AI SDK chat
  - Backend can run independently for testing
  - Clean separation: Python does math, JS does UI
```

**Database Choice — SQLite**:
```
  WHY SQLite OVER FLAT JSON?
  ══════════════════════════

  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  Chat escape hatches need QUERIES:                           │
  │    "Show me field notes from March 2025 mentioning duct"    │
  │    → SELECT * FROM field_notes                               │
  │      WHERE project_id = ? AND date BETWEEN ? AND ?          │
  │      AND content LIKE '%duct%'                               │
  │                                                              │
  │  JSON files can't do this. SQLite can.                       │
  │                                                              │
  │  SQLite gives us:                                            │
  │    ✓  Raw data tables (10 CSV imports)                       │
  │    ✓  Computed metrics tables (pre-calculated)               │
  │    ✓  Dossier JSON stored as TEXT column (serve as-is)       │
  │    ✓  Ad-hoc queries from chat tools (escape hatches)        │
  │    ✓  Single file, zero config, ships with the backend       │
  │    ✓  Python has excellent sqlite3 in stdlib                 │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: Data Foundation

**Goal**: All 10 CSVs loaded into SQLite. Every row queryable. Relationships enforced. One script to rebuild from scratch.

```
  PHASE 1 ARCHITECTURE
  ════════════════════

  ┌──────────────────┐         ┌──────────────────────────┐
  │  10 CSV files    │         │  SQLite: hvac.db          │
  │  (data/)         │         │                          │
  │                  │  seed   │  ┌──────────────────┐    │
  │  contracts.csv   │ ──────► │  │ contracts        │    │
  │  sov.csv         │ script  │  │ sov              │    │
  │  sov_budget.csv  │         │  │ sov_budget       │    │
  │  labor_logs.csv  │         │  │ labor_logs       │    │
  │  material_deliv. │         │  │ material_delivs  │    │
  │  billing_hist.   │         │  │ billing_history  │    │
  │  billing_items.  │         │  │ billing_items    │    │
  │  change_orders.  │         │  │ change_orders    │    │
  │  rfis.csv        │         │  │ rfis             │    │
  │  field_notes.csv │         │  │ field_notes      │    │
  │                  │         │  └──────────────────┘    │
  └──────────────────┘         │                          │
                               │  Indexes on:             │
                               │   - project_id (all tbl) │
                               │   - sov_line_id          │
                               │   - date columns         │
                               └──────────────────────────┘
```

### Tasks

| # | Task | Vertical Slice | Output |
|---|------|----------------|--------|
| 1.1 | **Scaffold both projects** | Backend: `mkdir backend && cd backend && pip install fastapi uvicorn pandas`. Frontend: `npx create-next-app frontend`. Create folder structure | Both projects boot |
| 1.2 | **Create SQLite schema** | `backend/db/schema.sql` — CREATE TABLE for all 10 tables with proper types, PKs, indexes | Schema file |
| 1.3 | **Write seed script** | `backend/scripts/seed_db.py` — reads all 10 CSVs with pandas, INSERTs into SQLite | hvac.db file generated |
| 1.4 | **Create db connection helper** | `backend/db/connection.py` — singleton connection, context manager, query helpers | Reusable DB module |
| 1.5 | **Copy CSV data into project** | Copy all 10 CSVs from `Hackathon-5/hvac_construction_dataset/` into `backend/data/` | Data files in project |
| 1.6 | **FastAPI app skeleton** | `backend/main.py` — FastAPI app with CORS enabled for Next.js, health check endpoint | `GET /health` returns 200 |

### Schema Design

```sql
  KEY TABLES AND THEIR COLUMNS
  ════════════════════════════

  contracts
  ─────────
  project_id           TEXT PK
  project_name         TEXT
  original_contract_value  REAL
  contract_date        TEXT (ISO date)
  substantial_completion_date  TEXT
  retention_pct        REAL
  payment_terms        TEXT
  gc_name              TEXT
  architect            TEXT
  engineer_of_record   TEXT

  labor_logs
  ──────────
  log_id               TEXT PK
  project_id           TEXT FK → contracts
  date                 TEXT (ISO date)
  employee_id          TEXT
  role                 TEXT
  sov_line_id          TEXT FK → sov
  hours_st             REAL
  hours_ot             REAL
  hourly_rate          REAL
  burden_multiplier    REAL
  work_area            TEXT
  cost_code            TEXT

  INDEX: idx_labor_project_date ON labor_logs(project_id, date)
  INDEX: idx_labor_sov ON labor_logs(sov_line_id)

  (similar pattern for all 10 tables)
```

### Phase 1 Gate Tests

```
  TEST 1: DATA INTEGRITY
  ═══════════════════════

  ┌───────────────────────────────────────────────────────────┐
  │  backend/tests/test_phase1.py                              │
  │                                                           │
  │  1. Row counts match CSV:                                 │
  │     contracts:         5 rows    ✓                        │
  │     sov:              75 rows    ✓                        │
  │     sov_budget:       75 rows    ✓                        │
  │     labor_logs:   16,445 rows    ✓                        │
  │     material_deliveries: 269     ✓                        │
  │     billing_history:    83       ✓                        │
  │     billing_line_items: 1,163    ✓                        │
  │     change_orders:      64       ✓                        │
  │     rfis:              317       ✓                        │
  │     field_notes:     1,328       ✓                        │
  │                                                           │
  │  2. Foreign keys valid:                                   │
  │     Every labor_logs.project_id exists in contracts  ✓    │
  │     Every labor_logs.sov_line_id exists in sov       ✓    │
  │     Every billing_item.sov_line_id exists in sov     ✓    │
  │                                                           │
  │  3. No NULL in required fields                       ✓    │
  │                                                           │
  │  4. Date parsing works (all dates are valid ISO)     ✓    │
  │                                                           │
  │  5. Spot checks:                                          │
  │     contracts WHERE project_id = 'PRJ-2024-001'           │
  │       → original_contract_value = 35194000           ✓    │
  │     COUNT(labor_logs WHERE project_id = 'PRJ-2024-001')   │
  │       → should be several thousand                   ✓    │
  │                                                           │
  └───────────────────────────────────────────────────────────┘
```

---

## PHASE 2: Compute Engine

**Goal**: All deterministic metrics computed and stored. Health scores calculated. Triggers detected. Zero LLM involvement.

```
  PHASE 2 ARCHITECTURE
  ════════════════════

  ┌──────────────┐         ┌────────────────────────────────────┐
  │  SQLite      │         │  NEW TABLES IN SQLite              │
  │  (raw data)  │         │                                    │
  │              │ compute │  ┌────────────────────────────┐    │
  │  labor_logs  │ ──────► │  │ computed_sov_metrics       │    │
  │  materials   │ engine  │  │  - actual_labor_cost       │    │
  │  billing_*   │         │  │  - actual_material_cost    │    │
  │  sov_budget  │         │  │  - estimated_labor_cost    │    │
  │  change_ords │         │  │  - estimated_material_cost │    │
  │  rfis        │         │  │  - labor_overrun_pct       │    │
  │              │         │  │  - material_variance_pct   │    │
  │              │         │  └────────────────────────────┘    │
  │              │         │                                    │
  │              │         │  ┌────────────────────────────┐    │
  │              │         │  │ computed_project_metrics    │    │
  │              │         │  │  - total_actual_cost       │    │
  │              │         │  │  - bid_margin_pct          │    │
  │              │         │  │  - realized_margin_pct     │    │
  │              │         │  │  - margin_erosion_pct      │    │
  │              │         │  │  - billing_lag             │    │
  │              │         │  │  - pending_co_exposure     │    │
  │              │         │  │  - health_score            │    │
  │              │         │  │  - status (RED/YEL/GRN)    │    │
  │              │         │  └────────────────────────────┘    │
  │              │         │                                    │
  │              │         │  ┌────────────────────────────┐    │
  │              │         │  │ triggers                    │    │
  │              │         │  │  - trigger_id              │    │
  │              │         │  │  - project_id              │    │
  │              │         │  │  - date                    │    │
  │              │         │  │  - type                    │    │
  │              │         │  │  - severity                │    │
  │              │         │  │  - value                   │    │
  │              │         │  │  - affected_sov_lines      │    │
  │              │         │  └────────────────────────────┘    │
  │              │         │                                    │
  └──────────────┘         └────────────────────────────────────┘
```

### Tasks

| # | Task | Vertical Slice | Output |
|---|------|----------------|--------|
| 2.1 | **SOV-line labor cost computation** | `backend/compute/labor.py` — for each project + SOV line, compute `SUM((hrs_st + hrs_ot*1.5) * rate * burden)` from labor_logs. Write to `computed_sov_metrics` | Actual labor cost per SOV line |
| 2.2 | **SOV-line material cost computation** | `backend/compute/materials.py` — for each project + SOV line, compute `SUM(total_cost)` from material_deliveries. Write to `computed_sov_metrics` | Actual material cost per SOV line |
| 2.3 | **Project-level financial rollups** | `backend/compute/financials.py` — aggregate SOV-line costs to project level. Compute bid margin, realized margin, erosion. CO totals by status. Write to `computed_project_metrics` | Project-level financials |
| 2.4 | **Billing lag computation** | `backend/compute/billing.py` — compare earned value (% complete * scheduled_value) vs cumulative billed from billing_line_items. Per SOV line and per project | Billing lag per SOV line + project |
| 2.5 | **RFI metrics** | `backend/compute/rfis.py` — open count, overdue count, orphan RFIs (cost_impact=true but no matching CO), avg response time | RFI health indicators |
| 2.6 | **Health score calculator** | `backend/compute/health_score.py` — start at 100, deduct based on thresholds from research.md. Assign RED/YELLOW/GREEN | Health score per project |
| 2.7 | **Trigger detector** | `backend/compute/triggers.py` — scan timeline day-by-day per project. Find first date each threshold was crossed. Detect: labor overrun >1.15x, pending CO exposure >5%, billing lag >3%, orphan RFIs, material variance >5% | Trigger rows in `triggers` table |
| 2.8 | **Compute orchestrator** | `backend/compute/__init__.py` — runs all compute steps in order (2.1→2.7), wraps in a transaction | Single `run_compute_engine()` function |

### Phase 2 Gate Tests

```
  TEST 2: MATH CORRECTNESS
  ═════════════════════════

  ┌───────────────────────────────────────────────────────────┐
  │  backend/tests/test_phase2.py                              │
  │                                                           │
  │  1. Manual labor cost check:                              │
  │     Pick 3 known labor_log rows, compute by hand          │
  │     (hrs_st + hrs_ot*1.5) * rate * burden                 │
  │     Compare to computed_sov_metrics → must match      ✓   │
  │                                                           │
  │  2. SOV line totals add up to project total:              │
  │     SUM(computed_sov_metrics.actual_labor_cost)           │
  │       WHERE project_id = 'PRJ-2024-001'                   │
  │     = computed_project_metrics.total_actual_labor_cost ✓   │
  │                                                           │
  │  3. Margin math:                                          │
  │     bid_margin = (contract_value - estimated_cost)         │
  │                  / contract_value                          │
  │     realized_margin = (contract_value - actual_cost)       │
  │                       / contract_value                     │
  │     erosion = bid_margin - realized_margin             ✓   │
  │                                                           │
  │  4. Health score sanity:                                   │
  │     All scores between 0-100                          ✓   │
  │     RED projects have score < 50                      ✓   │
  │     GREEN projects have score >= 80                   ✓   │
  │                                                           │
  │  5. Trigger detection:                                     │
  │     At least 1 trigger per RED project                ✓   │
  │     Trigger dates are within project date range        ✓   │
  │     Trigger values match the threshold crossed         ✓   │
  │                                                           │
  │  6. CO totals:                                             │
  │     SUM(change_orders WHERE status='Approved')             │
  │     = computed_project_metrics.approved_cos            ✓   │
  │                                                           │
  │  7. No division by zero, no NaN, no negative hours    ✓   │
  │                                                           │
  └───────────────────────────────────────────────────────────┘
```

---

## PHASE 3: Reasoning Engine + Dossier Assembly

**Goal**: For every trigger, pull evidence, generate reasoning via Haiku, assemble final dossier JSONs, store in SQLite.

```
  PHASE 3 ARCHITECTURE
  ════════════════════

  ┌──────────────────┐
  │  triggers table   │   For each trigger:
  │  (from Phase 2)  │
  └────────┬─────────┘
           │
           │  1. PULL EVIDENCE
           ▼
  ┌──────────────────────────────────────┐
  │  evidence-puller.ts                   │
  │                                      │
  │  Given: trigger (project, date, SOV) │
  │  Query SQLite for:                   │
  │   - field_notes ±7 days of trigger   │
  │   - change_orders for that SOV line  │
  │   - rfis linked to those COs         │
  │   - material_deliveries with issues  │
  │   - labor_logs OT spike data         │
  │                                      │
  │  Output: evidence bundle JSON        │
  └──────────────┬───────────────────────┘
                 │
                 │  2. REASON (Haiku via Claude Code tmux)
                 ▼
  ┌──────────────────────────────────────┐
  │  reasoning-engine.ts                  │
  │                                      │
  │  For each trigger's evidence bundle: │
  │   - Build prompt (from research.md)  │
  │   - Call Haiku via Claude Code tmux  │
  │   - Parse JSON response              │
  │   - Validate required fields         │
  │                                      │
  │  Output: reasoning JSON per trigger  │
  └──────────────┬───────────────────────┘
                 │
                 │  3. ASSEMBLE DOSSIER
                 ▼
  ┌──────────────────────────────────────┐
  │  dossier-builder.ts                   │
  │                                      │
  │  Per project:                        │
  │   - Pull project metrics             │
  │   - Pull all triggers + evidence     │
  │   - Attach reasoning to each trigger │
  │   - Build complete dossier JSON      │
  │   - Store in `dossiers` table        │
  │     (project_id, dossier_json TEXT)  │
  │                                      │
  │  Also build portfolio.json:          │
  │   - Summary of all 5 projects        │
  │   - Health scores, status, headline  │
  │                                      │
  └──────────────────────────────────────┘
```

### Tasks

| # | Task | Vertical Slice | Output |
|---|------|----------------|--------|
| 3.1 | **Evidence puller** | `backend/reasoning/evidence_puller.py` — given a trigger row, query SQLite for field_notes (±7 days, matching SOV lines), related COs, RFIs, material deliveries, OT spikes. Return structured evidence bundle | Evidence bundle JSON per trigger |
| 3.2 | **Haiku prompt template** | `backend/reasoning/prompt.py` — the carefully crafted prompt from research.md. Template slots for trigger type, project name, SOV description, evidence bundle. Strict JSON output format | Reusable prompt builder |
| 3.3 | **Reasoning engine (Haiku via tmux)** | `backend/reasoning/reasoning_engine.py` — takes evidence bundle, builds prompt, invokes Haiku (via `subprocess` calling Claude Code CLI or Anthropic Python SDK), parses JSON response, validates schema | Reasoning JSON per trigger |
| 3.4 | **Dossier builder** | `backend/reasoning/dossier_builder.py` — per project: pull computed metrics + triggers + evidence + reasoning. Assemble into the full dossier JSON structure from research.md. Store in `dossiers` table | Complete dossier JSON per project |
| 3.5 | **Portfolio summary builder** | `backend/reasoning/portfolio_builder.py` — build portfolio.json from all 5 project summaries (health, status, headline, key metric). Store in `dossiers` table with project_id='PORTFOLIO' | portfolio.json |
| 3.6 | **Pipeline orchestrator** | `backend/scripts/build_dossiers.py` — runs seed → compute → reasoning → stores everything. Single command: `python -m backend.scripts.build_dossiers` | One command builds all data |

### Phase 3 Gate Tests

```
  TEST 3: REASONING QUALITY
  ══════════════════════════

  ┌───────────────────────────────────────────────────────────┐
  │  backend/tests/test_phase3.py                              │
  │                                                           │
  │  1. Evidence bundles are non-empty:                       │
  │     Every trigger has >= 1 field note              ✓      │
  │     Evidence date range is within ±7 days          ✓      │
  │                                                           │
  │  2. Haiku reasoning parses as valid JSON:                 │
  │     Every reasoning has: root_cause, contributing_factors,│
  │       recovery_actions, recoverable_amount, confidence ✓  │
  │                                                           │
  │  3. Reasoning references real evidence:                   │
  │     CO numbers in reasoning exist in change_orders  ✓     │
  │     RFI numbers in reasoning exist in rfis          ✓     │
  │     Field note IDs referenced actually exist        ✓     │
  │                                                           │
  │  4. Dossier JSON structure matches schema:                │
  │     Required fields: project_id, name, health_score,      │
  │       status, financials, triggers[]                 ✓    │
  │     Each trigger has: trigger_id, date, type,             │
  │       severity, metrics, evidence, reasoning         ✓    │
  │                                                           │
  │  5. Portfolio summary has all 5 projects              ✓   │
  │                                                           │
  │  6. Dossiers stored in SQLite dossiers table          ✓   │
  │     SELECT COUNT(*) FROM dossiers = 6                     │
  │     (5 projects + 1 portfolio)                            │
  │                                                           │
  └───────────────────────────────────────────────────────────┘
```

---

## PHASE 4: Frontend UI

**Goal**: Full UI scaffolded with v0. All three states working (cold → analyzed → insights). Serves pre-computed data from SQLite.

```
  PHASE 4 ARCHITECTURE
  ════════════════════

  ┌────────────────────────────────┐      ┌─────────────────────────────┐
  │  NEXT.JS FRONTEND              │      │  FASTAPI BACKEND             │
  │                                │      │                             │
  │  PAGES                         │ HTTP │  ENDPOINTS                   │
  │  ─────                         │ ◄──► │  ─────────                   │
  │                                │      │                             │
  │  app/page.tsx                  │      │  GET /api/portfolio          │
  │  (STATE 1: cold cards)         │      │  (reads dossiers table,     │
  │  (STATE 2: analyzed cards)     │      │   returns portfolio.json)   │
  │                                │      │                             │
  │  app/project/[id]/page.tsx     │      │  GET /api/dossier/{id}      │
  │  (STATE 3: insights)           │      │  (reads dossiers table,     │
  │  (STATE 3b: reasoning expand)  │      │   returns prj-xxx.json)     │
  │                                │      │                             │
  │  COMPONENTS (v0 scaffolded)    │      │  POST /api/chat             │
  │  ──────────                    │      │  (context + query → LLM)    │
  │  portfolio-grid.tsx            │      │                             │
  │  project-card.tsx              │      │  POST /api/email            │
  │  dossier-header.tsx            │      │  (send email)               │
  │  issue-card.tsx                │      │                             │
  │  reasoning-panel.tsx           │      │  GET /api/field-notes       │
  │  scoring-bars.tsx              │      │  GET /api/labor-detail      │
  │  chat-panel.tsx                │      │  GET /api/co/{co_number}    │
  │                                │      │  GET /api/rfi/{rfi_number}  │
  │                                │      │  POST /api/what-if-margin   │
  └────────────────────────────────┘      └─────────────────────────────┘
```

### Tasks

| # | Task | Vertical Slice | Output |
|---|------|----------------|--------|
| 4.1 | **FastAPI endpoint: GET /api/portfolio** | `backend/routes/portfolio.py` — read portfolio JSON from SQLite `dossiers` table, return as JSON response | Working API endpoint |
| 4.2 | **FastAPI endpoint: GET /api/dossier/{id}** | `backend/routes/dossier.py` — read project dossier from SQLite, return full dossier JSON | Working API endpoint |
| 4.3 | **Portfolio page — STATE 1 (cold)** | `frontend/app/page.tsx` + `portfolio-grid.tsx` + `project-card.tsx` — render 5 cards with basic contract info. "Run Real-Time Analysis" button. Fetch from FastAPI | Static cards, no colors |
| 4.4 | **Portfolio page — STATE 2 (analyzed)** | On button click, fetch `BACKEND_URL/api/portfolio`, animate cards with health colors (RED/YELLOW/GREEN), show scores + margin + issue count. "View Insights" button per card | Cards with colors and scores |
| 4.5 | **Dossier page — STATE 3 (insights)** | `frontend/app/project/[id]/page.tsx` — fetch `BACKEND_URL/api/dossier/{id}`. Show financial summary bar + issue cards with metrics + "View Reasoning" button. Back-to-portfolio link | Full dossier page |
| 4.6 | **Reasoning panel — STATE 3b (expanded)** | `reasoning-panel.tsx` — expand on "View Reasoning" click. Show timeline, root cause, contributing factors, action items with $ amounts, scoring bars, confidence | Reasoning expansion works |
| 4.7 | **Scaffold with v0** | Use v0 to generate initial component shells for the cards, bars, panels. Then wire to real data from FastAPI | Polished UI components |

### Phase 4 Gate Tests

```
  TEST 4: RENDER + ROUTING
  ═════════════════════════

  ┌───────────────────────────────────────────────────────────┐
  │  Manual testing + backend/tests/test_phase4.py            │
  │                                                           │
  │  1. API routes return valid JSON:                         │
  │     GET localhost:8000/api/portfolio → 200, 5 projects✓   │
  │     GET localhost:8000/api/dossier/PRJ-2024-001 → 200✓   │
  │     GET localhost:8000/api/dossier/INVALID → 404     ✓   │
  │                                                           │
  │  2. STATE 1 renders:                                      │
  │     5 cards visible on page load                     ✓   │
  │     No colors, no scores                             ✓   │
  │     "Run Real-Time Analysis" button visible          ✓   │
  │                                                           │
  │  3. STATE 2 transition:                                   │
  │     Click button → cards get colors                  ✓   │
  │     RED projects show health < 50                    ✓   │
  │     GREEN projects show health >= 80                 ✓   │
  │     "View Insights" button appears per card          ✓   │
  │                                                           │
  │  4. STATE 3 navigation:                                   │
  │     Click "View Insights" → navigates to /project/X  ✓   │
  │     Financial summary bar shows correct numbers      ✓   │
  │     Issue cards render with correct trigger data      ✓   │
  │     Back link returns to portfolio                   ✓   │
  │                                                           │
  │  5. STATE 3b expansion:                                   │
  │     Click "View Reasoning" → panel expands           ✓   │
  │     Timeline events render in chronological order    ✓   │
  │     Root cause text displays                         ✓   │
  │     Action items show with $ amounts                 ✓   │
  │     Scoring bars render with correct values          ✓   │
  │                                                           │
  └───────────────────────────────────────────────────────────┘
```

---

## PHASE 5: Chat + Email + Deploy

**Goal**: Working chat with direct context injection. Email capability. Deployed to Vercel.

```
  PHASE 5 ARCHITECTURE
  ════════════════════

  ┌────────────────────────────────────────────────────────────────┐
  │                                                                │
  │  CHAT (Vercel AI SDK)                                          │
  │  ════════════════════                                          │
  │                                                                │
  │  ┌──────────┐    ┌──────────────────────────────────────────┐ │
  │  │ useChat() │───►│ Next.js API route /api/chat              │ │
  │  │ hook      │    │ (thin proxy using Vercel AI SDK)         │ │
  │  │ (client)  │    │                                          │ │
  │  └──────────┘    │ OR                                       │ │
  │                   │                                          │ │
  │                   │ FastAPI POST /api/chat                   │ │
  │                   │ (streaming response with SSE)            │ │
  │                   │                                          │ │
  │                   │ 1. Read project_id from request          │ │
  │                   │ 2. Load dossier JSON from SQLite         │ │
  │                   │ 3. Inject dossier into system prompt     │ │
  │                   │    (DIRECT INJECTION — NO RAG)           │ │
  │                   │ 4. Stream response with tool calls       │ │
  │                   │                                          │ │
  │                   │ TOOLS (backend query functions):         │ │
  │                   │  ┌──────────────────────────────────┐    │ │
  │                   │  │ get_field_notes(prj, date, kw)   │    │ │
  │                   │  │ get_labor_detail(prj, sov_line)  │    │ │
  │                   │  │ get_co_detail(co_number)         │    │ │
  │                   │  │ get_rfi_detail(rfi_number)       │    │ │
  │                   │  │ what_if_margin(prj, scenario)    │    │ │
  │                   │  │ send_email(to, subject, body)    │    │ │
  │                   │  └──────────────────────────────────┘    │ │
  │                   │                                          │ │
  │                   └──────────────────────────────────────────┘ │
  │                                                                │
  │  EMAIL (Hackathon requirement)                                 │
  │  ═════════════════════════════                                 │
  │                                                                │
  │  api/email/route.ts                                            │
  │   - Receives: to, subject, body                                │
  │   - Sends via Resend / Nodemailer / Vercel email               │
  │   - Called by chat tool or direct UI button                    │
  │                                                                │
  └────────────────────────────────────────────────────────────────┘
```

### Tasks

| # | Task | Vertical Slice | Output |
|---|------|----------------|--------|
| 5.1 | **Chat endpoint (FastAPI)** | `backend/routes/chat.py` — receives message + project_id, loads dossier from SQLite, injects into system prompt, calls Claude/LLM, streams response via SSE. Tool-calling loop for escape hatches | Working streaming chat endpoint |
| 5.2 | **Chat UI component (Next.js)** | `frontend/components/chat-panel.tsx` — `useChat()` hook or custom SSE consumer. Shows at bottom of portfolio page AND dossier page. Project-aware context | Chat panel in UI |
| 5.3 | **Chat tool: get_field_notes** | `backend/tools/field_notes.py` — query SQLite for field notes by project, date range, keyword search in content | Tool callable by LLM |
| 5.4 | **Chat tool: get_labor_detail** | `backend/tools/labor_detail.py` — query labor_logs for a specific project + SOV line. Return hours, cost, OT breakdown | Tool callable by LLM |
| 5.5 | **Chat tool: get_co_detail** | `backend/tools/co_detail.py` — query change_orders by CO number. Return full details | Tool callable by LLM |
| 5.6 | **Chat tool: get_rfi_detail** | `backend/tools/rfi_detail.py` — query rfis by RFI number. Return full details | Tool callable by LLM |
| 5.7 | **Chat tool: what_if_margin** | `backend/tools/what_if_margin.py` — given a project + scenario (e.g., "CO-017 rejected"), recalculate margin impact | Tool callable by LLM |
| 5.8 | **Email endpoint** | `backend/routes/email.py` + `backend/tools/send_email.py` — send email via Resend/SMTP. Callable as chat tool AND as direct API | Email sending works |
| 5.9 | **Deploy** | Backend: deploy FastAPI (Railway / Render / fly.io). Frontend: deploy Next.js to Vercel. Configure CORS + env vars | Live URLs for both |
| 5.10 | **End-to-end smoke test** | Full flow: load page → analyze → view insights → view reasoning → chat → send email | Everything works together |

### Phase 5 Gate Tests

```
  TEST 5: END-TO-END
  ═══════════════════

  ┌───────────────────────────────────────────────────────────┐
  │  Manual E2E + backend/tests/test_phase5.py                │
  │                                                           │
  │  1. Chat responds with project-aware answers:             │
  │     Ask "What's wrong with Mercy Hospital?"               │
  │     → Response mentions specific triggers, COs, $$$  ✓   │
  │                                                           │
  │  2. Chat tools work:                                      │
  │     Ask "Show me field notes from March 2025"             │
  │     → LLM calls get_field_notes tool, returns data   ✓   │
  │                                                           │
  │  3. What-if scenario:                                     │
  │     Ask "What happens if CO-017 gets rejected?"           │
  │     → LLM calls what_if_margin, explains impact      ✓   │
  │                                                           │
  │  4. Email works:                                          │
  │     Ask "Send an email to PM about CO-017"                │
  │     → LLM calls send_email tool                      ✓   │
  │     → Email actually delivered (or logged)            ✓   │
  │                                                           │
  │  5. Deployment:                                            │
  │     Backend responds on deployed URL                 ✓   │
  │     Frontend loads on vercel.app URL                 ✓   │
  │     Frontend ↔ Backend CORS works                    ✓   │
  │     All states work                                  ✓   │
  │     Chat works                                       ✓   │
  │     No console errors                                ✓   │
  │                                                           │
  │  6. Performance:                                          │
  │     Page load < 2 seconds                            ✓   │
  │     Analysis click < 500ms (pre-computed)            ✓   │
  │     Chat first token < 1 second                      ✓   │
  │                                                           │
  └───────────────────────────────────────────────────────────┘
```

---

## Full Task Dependency Graph

```
  PHASE 1 (Python)           PHASE 2 (Python)          PHASE 3 (Python)
  ══════════════             ══════════════            ══════════════

  1.5 Copy CSVs ─┐
                  │
  1.1 Scaffold ──┤
                  ├──► 1.3 Seed ──┐
  1.2 Schema ────┤     script     │
                  │                ├──► 2.1 Labor cost ──┐
  1.4 DB helper ─┤                │    2.2 Material cost │
                  │                │    2.4 Billing lag  ─┤
  1.6 FastAPI ───┘                │    2.5 RFI metrics   │
                                  │    2.7 Triggers ◄────┤
                    TEST 1 ◄──────┘    2.3 Financials ◄──┤
                                       2.6 Health score ◄─┤
                                       2.8 Orchestrator ◄─┘
                                            │
                                       TEST 2
                                            │
                                            ├──► 3.1 Evidence puller
                                            ├──► 3.2 Prompt template
                                            │         │
                                            │    3.3 Reasoning engine ◄─┘
                                            │         │
                                            ├──► 3.4 Dossier builder ◄──┘
                                            └──► 3.5 Portfolio builder
                                                      │
                                                 3.6 Pipeline orchestrator
                                                      │
                                                 TEST 3


  PHASE 4 (Both)                           PHASE 5 (Both)
  ══════════════                           ══════════════

  4.1 FastAPI /portfolio ─┐
  4.2 FastAPI /dossier ───┤
                           ├──► 4.3 State 1 (cold)
  4.7 v0 scaffold ────────┤    4.4 State 2 (analyzed)
                           │    4.5 State 3 (insights)
                           │    4.6 State 3b (reasoning)
                           │         │
                           │    TEST 4
                           │         │
                           │         ├──► 5.1 Chat API (FastAPI)
                           │         ├──► 5.2 Chat UI (Next.js)
                           │         ├──► 5.3-5.7 Chat tools (Python)
                           │         ├──► 5.8 Email (Python)
                           │         ├──► 5.9 Deploy (both services)
                           │         │
                           │         └──► 5.10 E2E test
                           │                   │
                           │              TEST 5
                           │
                           └──► DONE
```

---

## Final File Structure

```
  hvac-margin-agent/
  │
  ├── backend/                         ◄── PYTHON / FASTAPI
  │   │
  │   ├── data/
  │   │   ├── contracts.csv
  │   │   ├── sov.csv
  │   │   ├── sov_budget.csv
  │   │   ├── labor_logs.csv
  │   │   ├── material_deliveries.csv
  │   │   ├── billing_history.csv
  │   │   ├── billing_line_items.csv
  │   │   ├── change_orders.csv
  │   │   ├── rfis.csv
  │   │   └── field_notes.csv
  │   │
  │   ├── db/
  │   │   ├── connection.py            ◄── SQLite connection singleton
  │   │   └── schema.sql               ◄── CREATE TABLE statements
  │   │
  │   ├── compute/
  │   │   ├── __init__.py              ◄── orchestrator (runs all)
  │   │   ├── labor.py                 ◄── labor cost per SOV line
  │   │   ├── materials.py             ◄── material cost per SOV line
  │   │   ├── financials.py            ◄── project-level rollups
  │   │   ├── billing.py               ◄── billing lag computation
  │   │   ├── rfis.py                  ◄── RFI metrics
  │   │   ├── health_score.py          ◄── 0-100 score + RED/YEL/GRN
  │   │   └── triggers.py              ◄── threshold crossing detector
  │   │
  │   ├── reasoning/
  │   │   ├── evidence_puller.py       ◄── query evidence per trigger
  │   │   ├── prompt.py                ◄── Haiku prompt template
  │   │   ├── reasoning_engine.py      ◄── Haiku invocation via tmux
  │   │   ├── dossier_builder.py       ◄── assemble project dossier
  │   │   └── portfolio_builder.py     ◄── assemble portfolio summary
  │   │
  │   ├── routes/
  │   │   ├── portfolio.py             ◄── GET /api/portfolio
  │   │   ├── dossier.py               ◄── GET /api/dossier/{id}
  │   │   ├── chat.py                  ◄── POST /api/chat (SSE stream)
  │   │   └── email.py                 ◄── POST /api/email
  │   │
  │   ├── tools/
  │   │   ├── field_notes.py           ◄── chat tool: query field notes
  │   │   ├── labor_detail.py          ◄── chat tool: query labor logs
  │   │   ├── co_detail.py             ◄── chat tool: query change orders
  │   │   ├── rfi_detail.py            ◄── chat tool: query RFIs
  │   │   ├── what_if_margin.py        ◄── chat tool: margin scenarios
  │   │   └── send_email.py            ◄── chat tool: send email
  │   │
  │   ├── scripts/
  │   │   ├── seed_db.py               ◄── CSV → SQLite importer
  │   │   └── build_dossiers.py        ◄── full pipeline (seed + compute + reason)
  │   │
  │   ├── tests/
  │   │   ├── test_phase1.py           ◄── data integrity tests
  │   │   ├── test_phase2.py           ◄── math correctness tests
  │   │   ├── test_phase3.py           ◄── reasoning quality tests
  │   │   ├── test_phase4.py           ◄── API endpoint tests
  │   │   └── test_phase5.py           ◄── E2E tests
  │   │
  │   ├── main.py                      ◄── FastAPI app entry point
  │   ├── hvac.db                      ◄── SQLite database (generated)
  │   └── requirements.txt             ◄── Python dependencies
  │
  ├── frontend/                        ◄── NEXT.JS / TYPESCRIPT
  │   │
  │   ├── app/
  │   │   ├── page.tsx                 ◄── portfolio (STATE 1 & 2)
  │   │   ├── project/[id]/page.tsx    ◄── dossier (STATE 3 & 3b)
  │   │   └── layout.tsx               ◄── root layout
  │   │
  │   ├── components/
  │   │   ├── portfolio-grid.tsx       ◄── 5 card layout
  │   │   ├── project-card.tsx         ◄── single card, health color
  │   │   ├── dossier-header.tsx       ◄── financial summary bar
  │   │   ├── issue-card.tsx           ◄── collapsible issue + reasoning
  │   │   ├── reasoning-panel.tsx      ◄── timeline + root cause + actions
  │   │   ├── scoring-bars.tsx         ◄── severity/impact/recovery bars
  │   │   └── chat-panel.tsx           ◄── chat UI component
  │   │
  │   ├── lib/
  │   │   └── api.ts                   ◄── fetch helpers for FastAPI
  │   │
  │   ├── package.json
  │   └── next.config.js
  │
  ├── research.md                      ◄── research & architecture doc
  └── tasks.md                         ◄── this file
```

---

## Task Count Summary

```
  ┌──────────┬───────────────────────┬────────┬───────────────────────┐
  │  PHASE   │  DESCRIPTION          │  TASKS │  PRIMARY LANGUAGE     │
  ├──────────┼───────────────────────┼────────┼───────────────────────┤
  │  Phase 1 │  Data Foundation      │    6   │  Python (FastAPI+SQL) │
  │  Phase 2 │  Compute Engine       │    8   │  Python (pandas+SQL)  │
  │  Phase 3 │  Reasoning + Dossier  │    6   │  Python (Haiku+tmux)  │
  │  Phase 4 │  Frontend UI          │    7   │  TypeScript (Next.js) │
  │  Phase 5 │  Chat + Email + Deploy│   10   │  Both (API + UI)      │
  ├──────────┼───────────────────────┼────────┼───────────────────────┤
  │  TOTAL   │                       │   37   │                       │
  └──────────┴───────────────────────┴────────┴───────────────────────┘

  + 5 gate test scripts (one per phase, all in Python via pytest)
```

---

*Implementation plan for the HVAC Margin Rescue Challenge hackathon.*
