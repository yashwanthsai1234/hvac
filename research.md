# HVAC Construction AI Agent — Research & Architecture

---

## Table of Contents

1. [HVAC Performance Metrics](#hvac-performance-metrics)
2. [The Margin Erosion Problem](#the-margin-erosion-problem)
3. [The Dataset](#the-dataset)
4. [Key Formulas](#key-formulas)
5. [Signal Classification: Deterministic vs LLM](#signal-classification-deterministic-vs-llm)
6. [System Architecture — Overview](#system-architecture--overview)
7. [Backend — Pre-Computation Pipeline](#backend--pre-computation-pipeline)
8. [The Dossier JSON — Per Project Output](#the-dossier-json--per-project-output)
9. [Health Scoring — Deterministic](#health-scoring--deterministic)
10. [Frontend — State by State](#frontend--state-by-state)
11. [Chat Architecture — Direct Context Injection](#chat-architecture--direct-context-injection)
12. [Backend Reasoning — Haiku via Claude Code tmux](#backend-reasoning--haiku-via-claude-code-tmux)
13. [Data Flow — Full Journey](#data-flow--full-journey)
14. [File / Module Structure](#file--module-structure)
15. [Cost Summary](#cost-summary)

---

## HVAC Performance Metrics

### Engineering / Operational Metrics

```
  ┌─────────────────────┬───────────────────────────────────────┐
  │ METRIC              │ WHAT IT TELLS YOU                     │
  ├─────────────────────┼───────────────────────────────────────┤
  │ COP / EER / SEER    │ Energy efficiency of cooling equip.   │
  │                     │ COP = Cooling Output / Power Input    │
  │                     │ Good chiller COP: 5.0-7.0            │
  ├─────────────────────┼───────────────────────────────────────┤
  │ kW/ton              │ Energy per ton of cooling             │
  │                     │ Target: < 0.6 kW/ton (full system)   │
  ├─────────────────────┼───────────────────────────────────────┤
  │ CFM/ton             │ Airflow per ton of cooling            │
  │                     │ Typical: 350-450 CFM/ton              │
  ├─────────────────────┼───────────────────────────────────────┤
  │ Delta-T             │ Temperature difference across coil    │
  │                     │ Chilled water: 10-14°F delta          │
  ├─────────────────────┼───────────────────────────────────────┤
  │ Static Pressure     │ Duct system resistance (in. w.g.)     │
  │                     │ High = clogged filters or bad design  │
  ├─────────────────────┼───────────────────────────────────────┤
  │ IAQ Score           │ CO2 ppm, particulate count, humidity  │
  │                     │ CO2 < 1000 ppm = good ventilation     │
  ├─────────────────────┼───────────────────────────────────────┤
  │ TAB Results         │ Test & Balance — actual vs design     │
  │                     │ airflow/water flow per zone           │
  └─────────────────────┴───────────────────────────────────────┘
```

### Construction / Business Metrics (Our Hackathon Domain)

We're not operating HVAC systems — we're **building them as a contractor** and tracking the **financial health** of that construction process.

```
  ┌──────────────────────┬───────────────────────────────────────────┐
  │ METRIC               │ FORMULA / MEANING                        │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ BID MARGIN           │ (Contract - Estimated Cost) / Contract   │
  │                      │ What you PLANNED to make (e.g., 15.2%)   │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ REALIZED MARGIN      │ (Contract - Actual Cost) / Contract      │
  │                      │ What you ACTUALLY made (e.g., 6.8%)      │
  │                      │ THE GAP IS YOUR PROBLEM                  │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ MARGIN EROSION       │ Bid Margin - Realized Margin             │
  │                      │ 15.2% - 6.8% = 8.4% LOST                │
  │                      │ On $50M revenue = $4.2M VANISHED         │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ COST-TO-COMPLETE     │ Estimated remaining cost to finish       │
  │                      │ If this grows faster than billing, ALARM │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ EARNED VALUE         │ % Complete x Contract Value              │
  │                      │ What you SHOULD have billed for          │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ BILLING LAG          │ Earned Value - Cumulative Billed         │
  │                      │ Money you EARNED but HAVEN'T BILLED      │
  │                      │ = free loan to the customer              │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ LABOR PRODUCTIVITY   │ Actual Hours / Estimated Hours           │
  │                      │ > 1.0 means OVERRUN                      │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ LABOR COST VARIANCE  │ Actual Labor $ - Budgeted Labor $        │
  │                      │ Positive = over budget                   │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ CHANGE ORDER RATIO   │ Approved COs / Original Contract         │
  │                      │ > 10% = scope is drifting dangerously    │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ PENDING CO EXPOSURE  │ Sum of unapproved change orders          │
  │                      │ Work done but NOT YET PAID FOR           │
  ├──────────────────────┼───────────────────────────────────────────┤
  │ RETENTION BALANCE    │ % held back until project close          │
  │                      │ Typically 10% — cash flow killer         │
  └──────────────────────┴───────────────────────────────────────────┘
```

---

## The Margin Erosion Problem

This is the central problem the hackathon challenge is about:

```
   MARGIN OVER TIME — THE SILENT BLEED

   Margin %
    18% │
        │  ████  Bid Margin (what we planned)
    15% │──████─────────────────────────────────────── Target: 15.2%
        │  ████ ██
    12% │  ████ ████
        │  ████ ████ ██
     9% │  ████ ████ ████ ██
        │  ████ ████ ████ ████ ██
     6% │  ████ ████ ████ ████ ████ ██ ◄──── Realized: 6.8%
        │  ████ ████ ████ ████ ████ ████
     3% │  ████ ████ ████ ████ ████ ████
        │  ████ ████ ████ ████ ████ ████
     0% └──────────────────────────────────────────
          Month Month Month Month Month Month
            1     2     3     4     5     6

        WHERE DID THE 8.4% GO?
        ─────────────────────
        ▓▓▓▓▓▓▓▓  3.1%  Labor overruns (OT, low productivity)
        ▒▒▒▒▒▒    2.2%  Unapproved change orders (work done, not paid)
        ░░░░      1.5%  Material cost escalation
        ████      0.9%  Billing lag (earned but not invoiced)
        ▓▓        0.7%  Scope creep from verbal approvals
```

---

## The Dataset

5 projects worth **$100.9M total**, with **18,312 records** of interlinked data:

```
   YOUR PORTFOLIO AT A GLANCE
   ══════════════════════════

   PRJ-2024-001  Mercy General Hospital     $35.2M  ████████████████████████
   PRJ-2024-002  Riverside Office Tower     $30.3M  ████████████████████
   PRJ-2024-003  Greenfield Elementary       $5.5M  ████
   PRJ-2024-004  Summit Data Center         $16.3M  ███████████
   PRJ-2024-005  (5th project)              $13.6M  █████████
                                           ────────
                                Total:     $100.9M
```

### Data Files

| File | Records | Description |
|------|---------|-------------|
| `contracts.csv` | 5 | Base contract information (5 projects) |
| `sov.csv` | 75 | Schedule of Values line items (15 per project) |
| `sov_budget.csv` | 75 | Original bid estimates for variance analysis |
| `labor_logs.csv` | 16,445 | Daily crew time entries (largest file) |
| `material_deliveries.csv` | 269 | Material receipt records |
| `billing_history.csv` | 83 | Monthly pay application headers |
| `billing_line_items.csv` | 1,163 | Pay application line item details |
| `change_orders.csv` | 64 | Change order requests (various approval states) |
| `rfis.csv` | 317 | RFI (Request for Information) log |
| `field_notes.csv` | 1,328 | Unstructured daily field reports |

### How the Data Connects

```
                          ┌──────────────┐
                          │  CONTRACTS   │  5 projects
                          │  (The Deal)  │  contract value, dates,
                          └──────┬───────┘  retention, parties
                                 │
           ┌────────┬────────┬───┴───┬────────┬────────┬────────┐
           │        │        │       │        │        │        │
           ▼        ▼        ▼       ▼        ▼        ▼        ▼
      ┌────────┐┌───────┐┌──────┐┌──────┐┌──────┐┌───────┐┌────────┐
      │  SOV   ││LABOR  ││MATER-││CHANGE││ RFIs ││FIELD  ││BILLING │
      │        ││LOGS   ││IALS  ││ORDERS││      ││NOTES  ││HISTORY │
      │75 lines││16,445 ││269   ││64    ││317   ││1,328  ││83 apps │
      │        ││entries││deliv.││      ││      ││       ││1,163   │
      │Planned ││       ││      ││      ││      ││       ││line    │
      │breakdwn││Actual ││Actual││Scope ││Quest-││Ground ││items   │
      │of $$$  ││labor  ││mat'l ││chang-││ions &││truth  ││        │
      │by work ││cost   ││cost  ││es    ││delays││human  ││What we │
      │type    ││burned ││spent ││$$$   ││$$$   ││notes  ││billed  │
      └───┬────┘└───┬───┘└──┬───┘└──┬───┘└──┬───┘└───────┘└───┬────┘
          │         │       │       │       │                  │
          │         │       │       └───────┘                  │
          │         │       │       COs link                   │
          │         │       │       to RFIs                    │
          │         │       │                                  │
          └─────────┴───────┴────────── ALL LINK VIA ──────────┘
                                    sov_line_id
                            (THE ROSETTA STONE OF
                             CONSTRUCTION FINANCE)
```

### The SOV — Why It's The Key to Everything

The **Schedule of Values** is the financial backbone. Every dollar flows through it:

```
   SOV LINE STRUCTURE (per project, 15 lines each)
   ════════════════════════════════════════════════

   Line │ Category                        │ What Goes Wrong Here
   ─────┼─────────────────────────────────┼─────────────────────────────
    01  │ General Conditions / PM         │ Dragging schedule = PM cost
    02  │ Submittals & Engineering        │ Rework from bad submittals
   ─────┼─────────────────────────────────┼─────────────────────────────
    03  │ Ductwork Fabrication            │ Material waste, shop errors
    04  │ Ductwork Installation           │ Low labor productivity
   ─────┼─────────────────────────────────┼─────────────────────────────
    05  │ Hydronic Piping                 │ Overtime on complex runs
    06  │ Refrigerant Piping              │ Specialist labor shortages
   ─────┼─────────────────────────────────┼─────────────────────────────
    07  │ RTU / AHU Equipment             │ Delivery delays, price hikes
    08  │ Chillers / Boilers              │ Long lead items
    09  │ Terminal Units (VAV, FCU)       │ Design changes mid-install
   ─────┼─────────────────────────────────┼─────────────────────────────
    10  │ Controls Installation           │ Integration headaches
    11  │ Controls Commissioning          │ Debugging eats schedule
   ─────┼─────────────────────────────────┼─────────────────────────────
    12  │ Insulation                      │ Often under-bid
   ─────┼─────────────────────────────────┼─────────────────────────────
    13  │ TAB (Test & Balance)            │ Failed TAB = redo work
    14  │ Startup & Commissioning         │ Punchlist surprises
    15  │ Closeout & Documentation        │ Retention trapped here
```

### Cross-Table Signal Detection

The dataset has **embedded signals** — problems hidden across multiple tables that only emerge when you cross-reference:

```
   SIGNAL DETECTION — CROSS-TABLE FORENSICS
   ═════════════════════════════════════════

   SIGNAL 1: LABOR OVERRUN
   ┌──────────┐    Compare    ┌──────────┐
   │sov_budget│ ────────────► │labor_logs│   Actual hrs > Estimated hrs?
   │est_hours │    Actual     │ hours_st │   By how much? Which SOV lines?
   │          │    vs Est     │ hours_ot │   Is OT climbing?
   └──────────┘               └──────────┘

   SIGNAL 2: UNAPPROVED WORK
   ┌──────────┐    Cross-ref  ┌──────────┐
   │change_   │ ────────────► │field_    │   Field notes say "GC told us
   │orders    │    Match      │notes     │   to go ahead" but CO is still
   │status:   │    text       │content:  │   "Pending"? = UNBILLED RISK
   │Pending   │               │"verbal"  │
   └──────────┘               └──────────┘

   SIGNAL 3: BILLING LAG
   ┌──────────┐    Compare    ┌──────────┐
   │billing_  │ ────────────► │labor_logs│   We spent $X on labor this
   │line_items│    Billed     │+ material│   month but only billed $Y.
   │this_period│   vs Spent   │deliveries│   Lag = free financing to GC.
   └──────────┘               └──────────┘

   SIGNAL 4: RFI COST CREEP
   ┌──────────┐    Chain      ┌──────────┐
   │  rfis    │ ────────────► │change_   │   RFI says "cost_impact: true"
   │cost_     │   RFI ──►    │orders    │   but no corresponding CO filed?
   │impact:   │   CO?        │related_  │   = MONEY LEFT ON TABLE
   │true      │              │rfi       │
   └──────────┘              └──────────┘

   SIGNAL 5: SCOPE DRIFT
   ┌──────────┐    NLP scan   ┌──────────┐
   │field_    │ ────────────► │change_   │   Field notes mention "extra
   │notes     │   Sentiment   │orders    │   work", "added scope",
   │content   │   + keyword   │          │   "owner requested" but no
   │(free     │   analysis    │          │   matching CO exists.
   │ text)    │               │          │
   └──────────┘               └──────────┘
```

---

## Key Formulas

```
   CRITICAL CALCULATIONS
   ═════════════════════

   LABOR COST (per log entry):
   ┌─────────────────────────────────────────────────────────┐
   │ cost = (hours_st + hours_ot * 1.5) * rate * burden_mult│
   │                                                         │
   │ Example: (8 + 2*1.5) * $45 * 1.42 = $702.90           │
   │          ──────────    ───   ────                       │
   │          11 eff.hrs   base  burden                      │
   └─────────────────────────────────────────────────────────┘

   MARGIN:
   ┌─────────────────────────────────────────────────────────┐
   │ bid_margin = (contract_value - estimated_cost)          │
   │              ─────────────────────────────────          │
   │                     contract_value                      │
   │                                                         │
   │ realized_margin = (contract_value - actual_cost)        │
   │                   ──────────────────────────────        │
   │                        contract_value                   │
   │                                                         │
   │ actual_cost = labor_actual + material_actual            │
   │             + sub_costs - approved_COs                  │
   └─────────────────────────────────────────────────────────┘

   BILLING HEALTH:
   ┌─────────────────────────────────────────────────────────┐
   │ billing_lag = earned_value - cumulative_billed          │
   │                                                         │
   │ If positive:  you did the work but didn't bill ──► BAD  │
   │ If negative:  you over-billed ──► risky, GC will notice │
   └─────────────────────────────────────────────────────────┘
```

---

## Signal Classification: Deterministic vs LLM

### Architecture Principle

**Compute first, reason second.** Give the LLM pre-computed numbers, not raw CSVs. It should never be doing arithmetic.

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │                    AGENT'S TWO-BRAIN ARCHITECTURE                    │
  │                                                                      │
  │         STRUCTURED DATA                    UNSTRUCTURED DATA         │
  │         (Numbers, Dates, IDs)              (Free Text, Narrative)    │
  │                │                                    │                │
  │                ▼                                    ▼                │
  │   ┌────────────────────────┐          ┌────────────────────────┐    │
  │   │   DETERMINISTIC BRAIN  │          │     LLM BRAIN          │    │
  │   │   ══════════════════   │          │     ═════════          │    │
  │   │                        │          │                        │    │
  │   │   Pandas / SQL / Code  │          │   GPT-4 / Claude /    │    │
  │   │   Pure math            │          │   Language model       │    │
  │   │   Always correct       │          │   Probabilistic        │    │
  │   │   Microseconds         │          │   Seconds              │    │
  │   │   Free (no API cost)   │          │   $$$ per call         │    │
  │   │   No hallucination     │          │   Can hallucinate      │    │
  │   └────────────┬───────────┘          └────────────┬───────────┘    │
  │                │                                    │                │
  │                └──────────────┬─────────────────────┘                │
  │                               ▼                                      │
  │                    ┌─────────────────────┐                           │
  │                    │   SYNTHESIS LAYER   │ ◄── LLM combines both     │
  │                    │   (LLM assembles    │     into a coherent       │
  │                    │    the final story) │     human narrative       │
  │                    └─────────────────────┘                           │
  └──────────────────────────────────────────────────────────────────────┘
```

### TIER 1: Pure Deterministic — No LLM Needed

These are **math problems**. They have exact answers. An LLM doing this is like hiring a poet to balance your checkbook.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │   SIGNAL                    │ WHY DETERMINISTIC     │ DATA SOURCE   │
  │   ═════════════════════════ │ ════════════════════  │ ════════════  │
  │                             │                       │               │
  │   1. LABOR COST PER LINE   │ Formula:              │ labor_logs    │
  │                             │ (ST + OT*1.5)        │               │
  │                             │  * rate * burden      │               │
  │                             │ Pure multiplication   │               │
  │                             │                       │               │
  │   2. LABOR OVERRUN         │ SUM(actual_hrs)       │ labor_logs    │
  │                             │ - estimated_hrs       │ + sov_budget  │
  │                             │ Group by sov_line     │               │
  │                             │ Subtraction           │               │
  │                             │                       │               │
  │   3. MARGIN CALCULATION    │ (contract - actual)   │ contracts     │
  │                             │ / contract            │ + labor_logs  │
  │                             │ Division              │ + materials   │
  │                             │                       │               │
  │   4. BILLING LAG           │ earned_value          │ billing_*     │
  │                             │ - cumulative_billed   │ + sov         │
  │                             │ Subtraction           │               │
  │                             │                       │               │
  │   5. MATERIAL VARIANCE     │ actual_spend          │ material_del. │
  │                             │ - budgeted_spend      │ + sov_budget  │
  │                             │ Subtraction           │               │
  │                             │                       │               │
  │   6. OVERTIME TREND        │ SUM(hours_ot)         │ labor_logs    │
  │                             │ GROUP BY week         │               │
  │                             │ Aggregation           │               │
  │                             │                       │               │
  │   7. CHANGE ORDER TOTALS   │ SUM(amount)           │ change_orders │
  │                             │ WHERE status = X      │               │
  │                             │ Conditional sum       │               │
  │                             │                       │               │
  │   8. PENDING CO EXPOSURE   │ SUM(amount)           │ change_orders │
  │                             │ WHERE status IN       │               │
  │                             │ (Pending, Under Rev.) │               │
  │                             │ Filter + sum          │               │
  │                             │                       │               │
  │   9. RFI RESPONSE TIME     │ date_responded        │ rfis          │
  │                             │ - date_submitted      │               │
  │                             │ Date arithmetic       │               │
  │                             │                       │               │
  │  10. RETENTION BALANCE     │ cumulative_billed     │ billing_hist  │
  │                             │ * retention_pct       │ + contracts   │
  │                             │ Multiplication        │               │
  │                             │                       │               │
  │  11. % COMPLETE vs BILLED  │ pct_complete from     │ billing_line  │
  │                             │ billing vs actual     │ + labor_logs  │
  │                             │ cost ratio            │ + materials   │
  │                             │                       │               │
  │  12. PRODUCTIVITY FACTOR   │ actual_hrs /          │ labor_logs    │
  │                             │ estimated_hrs         │ + sov_budget  │
  │                             │ per SOV line          │               │
  │                             │                       │               │
  └─────────────────────────────────────────────────────────────────────┘

  IMPLEMENTATION: These are TOOL FUNCTIONS the agent calls.
  They return NUMBERS, not prose. Written in Python/JS. Tested. Exact.
```

### TIER 2: LLM Required — Language Understanding

These signals live in **free text**, **ambiguity**, or require **judgment** that no formula can capture.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │   SIGNAL                    │ WHY LLM NEEDED        │ DATA SOURCE   │
  │   ═════════════════════════ │ ════════════════════  │ ════════════  │
  │                             │                       │               │
  │   1. VERBAL APPROVAL       │ Field notes say:      │ field_notes   │
  │      DETECTION             │ "GC told us to go     │ .content      │
  │                             │ ahead with the extra  │ (FREE TEXT)   │
  │                             │ exhaust ductwork"     │               │
  │                             │                       │               │
  │                             │ Only an LLM can read  │               │
  │                             │ this and understand:  │               │
  │                             │ "this = unapproved    │               │
  │                             │  scope change"        │               │
  │                             │                       │               │
  │   2. SCOPE DRIFT BURIED    │ "Added 6 diffusers    │ field_notes   │
  │      IN FIELD NOTES        │ per architect walkthru │ .content      │
  │                             │ last Tuesday"         │               │
  │                             │                       │               │
  │                             │ No CO exists for this.│               │
  │                             │ LLM must flag the gap.│               │
  │                             │                       │               │
  │   3. SAFETY / DELAY        │ "Crew stood down 3hrs │ field_notes   │
  │      SIGNALS               │ waiting for steel     │ .content      │
  │                             │ deck above us"        │               │
  │                             │                       │               │
  │                             │ This explains WHY     │               │
  │                             │ productivity dropped. │               │
  │                             │ LLM connects cause    │               │
  │                             │ to numeric effect.    │               │
  │                             │                       │               │
  │   4. RFI SUBJECT TRIAGE    │ Subject lines like:   │ rfis          │
  │                             │ "Conflict between     │ .subject      │
  │                             │ structural beam and   │               │
  │                             │ 24in supply duct at   │               │
  │                             │ grid D-7"             │               │
  │                             │                       │               │
  │                             │ LLM judges severity   │               │
  │                             │ and cost implication  │               │
  │                             │ from description.     │               │
  │                             │                       │               │
  │   5. CHANGE ORDER          │ "Reroute chilled      │ change_orders │
  │      DESCRIPTION ANALYSIS  │ water around new       │ .description  │
  │                             │ tenant wall added in  │               │
  │                             │ revision 4"           │               │
  │                             │                       │               │
  │                             │ LLM infers: this is   │               │
  │                             │ a design change, not  │               │
  │                             │ contractor error.     │               │
  │                             │ Affects negotiation.  │               │
  │                             │                       │               │
  │   6. CROSS-SIGNAL          │ Combine:              │ ALL tables    │
  │      NARRATIVE SYNTHESIS   │  - Numeric overrun    │               │
  │                             │  - Field note cause   │               │
  │                             │  - RFI delay          │               │
  │                             │  - Missing CO         │               │
  │                             │ Into ONE coherent     │               │
  │                             │ explanation a CFO     │               │
  │                             │ can act on.           │               │
  │                             │                       │               │
  │   7. ACTIONABLE            │ "You should escalate  │ Derived from  │
  │      RECOMMENDATIONS       │ CO-017 because..."    │ all signals   │
  │                             │                       │               │
  │                             │ Requires judgment,    │               │
  │                             │ prioritization,       │               │
  │                             │ domain knowledge.     │               │
  │                             │                       │               │
  │   8. CONVERSATIONAL        │ User asks: "What's    │ Agent memory  │
  │      FOLLOW-UP             │ going on with the     │ + tools       │
  │                             │ hospital project?"    │               │
  │                             │                       │               │
  │                             │ LLM decides which     │               │
  │                             │ tools to call and     │               │
  │                             │ how to respond.       │               │
  └─────────────────────────────────────────────────────────────────────┘
```

### TIER 3: Hybrid Signals — Code Detects, LLM Explains

These need **deterministic detection** but **LLM interpretation**.

```
  ┌───────────────────────────────────────────────────────────────┐
  │                                                               │
  │  SIGNAL: "RFI has cost_impact=true but no matching CO"       │
  │                                                               │
  │  DETECTION (deterministic):                                   │
  │    SELECT r.rfi_number FROM rfis r                            │
  │    LEFT JOIN change_orders co ON co.related_rfi = r.rfi_num  │
  │    WHERE r.cost_impact = true AND co.co_number IS NULL;      │
  │                                                               │
  │  INTERPRETATION (LLM):                                       │
  │    "RFI-089 identified a conflict requiring pipe rerouting.  │
  │     The engineer confirmed cost impact but no CO has been    │
  │     filed in 23 days. Based on similar RFIs in this project, │
  │     estimated exposure is $35K-$55K."                        │
  │                                                               │
  └───────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │                                                               │
  │  SIGNAL: "Productivity factor > 1.3 on a specific SOV line"  │
  │                                                               │
  │  DETECTION (deterministic):                                   │
  │    actual_hours / estimated_hours = 1.47                     │
  │                                                               │
  │  ROOT CAUSE (LLM reads field_notes):                         │
  │    "Field notes from Nov 12-18 mention 'waiting on ceiling   │
  │     grid install by others' 4 times. Crew was on-site but   │
  │     couldn't install terminal units. This is a coordination  │
  │     issue, not a labor efficiency problem — and it's         │
  │     potentially back-chargeable to the GC."                  │
  │                                                               │
  └───────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────┐
  │                                                               │
  │  SIGNAL: "Billing lag exceeds 15% of earned value"           │
  │                                                               │
  │  DETECTION (deterministic):                                   │
  │    earned_value = $4.2M, billed = $3.4M, lag = $800K        │
  │                                                               │
  │  EXPLANATION (LLM cross-references):                         │
  │    "The lag is concentrated in SOV lines 10-11 (Controls).   │
  │     Field notes show commissioning work is 60% complete but  │
  │     billing shows 0% — the PM likely hasn't submitted       │
  │     because the GC is disputing the controls spec change.   │
  │     Recommend: resolve RFI-142 first, then bill."           │
  │                                                               │
  └───────────────────────────────────────────────────────────────┘
```

### Token Budget Allocation

```
   ┌────────────────────────────────────────────────────────────┐
   │                                                            │
   │  WITHOUT this separation:                                  │
   │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  100% LLM   │
   │  Feeding 16K labor_logs rows to the LLM                   │
   │  It hallucinates math. Costs $$$. Slow.                   │
   │                                                            │
   │                                                            │
   │  WITH this separation:                                     │
   │  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░             │
   │  ^^^^^^^^                                                  │
   │  ~20% LLM   ~80% deterministic code                       │
   │                                                            │
   │  LLM only touches:                                         │
   │   - field_notes.content (text)    ~1,328 notes             │
   │   - Descriptions from COs/RFIs   ~381 text fields          │
   │   - Pre-computed numbers          ~50 values per project   │
   │   - Synthesis & recommendations                            │
   │                                                            │
   │  Code handles:                                             │
   │   - 16,445 labor calculations                              │
   │   - 269 material cost sums                                 │
   │   - 1,163 billing line comparisons                         │
   │   - All joins, filters, aggregations                       │
   │                                                            │
   └────────────────────────────────────────────────────────────┘
```

### The Cheat Sheet

```
   ┌────────────────────────┬─────────────────┬───────────────────────┐
   │       QUESTION         │  WHO ANSWERS?   │       WHY?            │
   ├────────────────────────┼─────────────────┼───────────────────────┤
   │ What is the margin?    │  CODE           │ Math                  │
   │ How many OT hours?     │  CODE           │ Aggregation           │
   │ Which COs are pending? │  CODE           │ Filter                │
   │ What's the billing lag?│  CODE           │ Subtraction           │
   │ How fast are RFI       │  CODE           │ Date math             │
   │   responses?           │                 │                       │
   ├────────────────────────┼─────────────────┼───────────────────────┤
   │ WHY did ductwork       │  LLM            │ Reads field notes     │
   │   overrun?             │                 │                       │
   │ Is this extra work     │  LLM            │ Interprets text       │
   │   a verbal approval?   │                 │                       │
   │ Should we escalate     │  LLM            │ Judgment call         │
   │   this CO?             │                 │                       │
   │ What's the root cause? │  LLM            │ Connects dots across  │
   │                        │                 │   multiple signals    │
   │ Summarize project      │  LLM            │ Narrative generation  │
   │   health for the CFO   │                 │                       │
   ├────────────────────────┼─────────────────┼───────────────────────┤
   │ RFI has cost_impact    │  CODE detects   │ Code finds the gap,   │
   │   but no CO filed?     │  LLM explains   │ LLM explains meaning │
   │ Productivity > 1.3x?   │  CODE detects   │ Code flags anomaly,   │
   │                        │  LLM diagnoses  │ LLM reads notes for   │
   │                        │                 │ root cause            │
   │ Billing lag on a       │  CODE detects   │ Code measures gap,    │
   │   specific SOV line?   │  LLM explains   │ LLM explains WHY     │
   └────────────────────────┴─────────────────┴───────────────────────┘
```

The rule of thumb: **if the answer is a number, code computes it. If the answer is a "because", the LLM reasons it.** The hybrid signals follow a pattern — code raises the flag, LLM reads the story behind it.

---

## System Architecture — Overview

All computation happens **once at build/startup**. The frontend serves pre-computed JSON. The only live LLM cost is the chat.

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │                        HVAC MARGIN RESCUE AGENT                           │
  │                                                                          │
  │  ┌───────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────┐   │
  │  │           │   │              │   │              │   │           │   │
  │  │  DATA     │──►│  COMPUTE     │──►│   REASONING  │──►│ FRONTEND  │   │
  │  │  LAYER    │   │  ENGINE      │   │   ENGINE     │   │ + CHAT    │   │
  │  │           │   │              │   │              │   │           │   │
  │  │  10 CSVs  │   │  All metrics │   │  Backend LLM │   │ Live UI   │   │
  │  │  parsed   │   │  All flags   │   │  per flag    │   │ + v0      │   │
  │  │  indexed  │   │  Trigger days│   │  reasoning   │   │ scaffolded│   │
  │  │           │   │  Health score│   │  JSON build  │   │ + Vercel  │   │
  │  │           │   │              │   │              │   │ AI SDK    │   │
  │  │           │   │              │   │              │   │ chat      │   │
  │  └───────────┘   └──────────────┘   └──────────────┘   └───────────┘   │
  │                                                                          │
  │  No LLM            No LLM              Haiku (batch)    LLM (chat only) │
  │  One-time load      Runs once           10-15 calls      Per user msg    │
  │                                         via tmux         Direct context  │
  │                                         ~$0.02 total     injection       │
  └──────────────────────────────────────────────────────────────────────────┘
```

### The User Journey — Three Clicks Deep

```
  STATE 1: COLD                STATE 2: ANALYZED           STATE 3: DEEP DIVE
  (page load)                  (after "Analyze")           (click "Insights")

  ┌─────────────────┐         ┌─────────────────┐         ┌──────────────────┐
  │                 │         │                 │         │                  │
  │  5 dossier      │  click  │  5 dossier      │  click  │  Full breakdown  │
  │  cards          │ ──────► │  cards NOW      │ ──────► │  Root causes     │
  │                 │ "Run    │  WITH colors    │ "View   │  Bad days list   │
  │  Basic info     │ Real-   │  RED/YEL/GRN   │ Insight"│  Action items    │
  │  only           │ Time    │  Health scores  │  on a   │  Evidence        │
  │                 │ Analy-  │  Quick summary  │  card   │  + Chat          │
  │  No colors yet  │ sis"    │                 │         │                  │
  │                 │         │  Insights btn   │         │                  │
  │                 │         │  on each card   │         │                  │
  └─────────────────┘         └─────────────────┘         └──────────────────┘

  Backend work:   $0            Pre-computed JSON           LLM chat only
                                served instantly            on demand
```

---

## Backend — Pre-Computation Pipeline

Everything happens once. The output is static JSON per project.

```
  BACKEND PRE-COMPUTATION (runs once at startup)
  ═══════════════════════════════════════════════

  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │          │    │              │    │              │    │              │
  │ A. LOAD  │───►│ B. COMPUTE   │───►│ C. DETECT    │───►│ D. REASON    │
  │          │    │              │    │              │    │              │
  │ Parse    │    │ Per project: │    │ Find trigger │    │ For each     │
  │ 10 CSVs  │    │  labor cost  │    │ points:      │    │ trigger:     │
  │ into     │    │  mat cost    │    │              │    │              │
  │ memory   │    │  margins     │    │ When did     │    │ Pull field   │
  │          │    │  overruns    │    │ burn cross   │    │ notes, COs,  │
  │          │    │  billing lag │    │ threshold?   │    │ RFIs for     │
  │          │    │  CO totals   │    │              │    │ that period  │
  │          │    │  RFI metrics │    │ Which SOV    │    │              │
  │          │    │  health score│    │ lines broke? │    │ Send to LLM  │
  │          │    │  per SOV line│    │              │    │ Get root     │
  │          │    │             │    │ Orphan RFIs? │    │ cause +      │
  │          │    │             │    │ Pending COs? │    │ actions      │
  │          │    │             │    │              │    │              │
  │ NO LLM   │    │ NO LLM      │    │ NO LLM       │    │ HAIKU x10-15│
  └──────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                 │
                                                                 ▼
                                                    ┌────────────────────┐
                                                    │ E. DOSSIER STORE   │
                                                    │                    │
                                                    │ portfolio.json     │
                                                    │ prj-001.json       │
                                                    │ prj-002.json       │
                                                    │ prj-003.json       │
                                                    │ prj-004.json       │
                                                    │ prj-005.json       │
                                                    │                    │
                                                    │ ALL pre-computed   │
                                                    │ Ready to serve     │
                                                    └────────────────────┘
```

### What Each Step Computes

```
  STEP A: LOAD
  ─────────────
  Parse all 10 CSVs into memory.
  Sort everything by date.
  Index by project_id.

  STEP B: COMPUTE (per project, per SOV line)
  ────────────────
  - actual_labor_cost = SUM((hrs_st + hrs_ot*1.5) * rate * burden)
  - actual_material_cost = SUM(material_deliveries.total_cost)
  - estimated costs from sov_budget
  - margins (bid vs realized)
  - billing lag (earned - billed)
  - CO totals by status
  - RFI metrics (open, overdue, cost impact)
  - health_score (0-100, threshold-based)
  - RED / YELLOW / GREEN status

  STEP C: DETECT (find the bad days)
  ─────────────
  Scan the timeline to find when each threshold was crossed.
  Which SOV lines broke first.
  Which COs are pending. Which RFIs are orphaned.

  triggers: [
    { date: "2025-03-19", type: "LABOR_OVERRUN",   value: 1.15 }
    { date: "2025-04-02", type: "PENDING_CO",       value: 287000 }
    { date: "2025-04-15", type: "BILLING_LAG",      value: 193000 }
  ]

  STEP D: REASON (Haiku via Claude Code tmux, only for triggers)
  ─────────────
  For each trigger:
    - Pull field notes for the relevant date range + SOV lines
    - Pull CO/RFI descriptions
    - Send evidence bundle to Haiku (via Claude Code tmux)
    - Get back: root cause, contributing factors, actions, confidence
    - Model: Claude Haiku (~$0.001 per call, 2-5 sec response)

  STEP E: ASSEMBLE
  ─────────────
  Package everything into one JSON per project.
  This JSON is the ONLY thing the frontend ever reads.
```

---

## The Dossier JSON — Per Project Output

```json
{
  "project_id": "PRJ-2024-001",
  "name": "Mercy General Hospital",
  "contract_value": 35194000,
  "start_date": "2024-03-27",
  "end_date": "2025-09-01",
  "health_score": 33,
  "status": "RED",

  "financials": {
    "estimated_cost": 29850000,
    "actual_cost": 34280000,
    "approved_cos": 1715700,
    "adjusted_contract": 36909700,
    "bid_margin_pct": 15.2,
    "realized_margin_pct": 7.1,
    "margin_erosion_pct": 8.1
  },

  "triggers": [
    {
      "trigger_id": "F-001",
      "date": "2025-03-19",
      "type": "LABOR_OVERRUN",
      "severity": "HIGH",
      "headline": "Burn ratio crossed 1.15x",

      "metrics": {
        "burn_ratio": 1.15,
        "worst_sov": "SOV-001-04",
        "overrun_pct": 17.9,
        "overrun_cost": 98200,
        "ot_ratio_during_period": 0.31
      },

      "evidence": {
        "field_notes": [
          {
            "note_id": "FN-2025-03-14-007",
            "date": "2025-03-14",
            "author": "M. Chen",
            "content": "Crew stood down 3 hrs AM waiting for spiral duct delivery. GC asked us to proceed with corridor grilles per owner walkthrough — no paperwork yet."
          },
          {
            "note_id": "FN-2025-03-18-003",
            "date": "2025-03-18",
            "author": "J. Martinez",
            "content": "DEL-044 finally arrived. Shifted 6 guys back to ductwork from piping. Running OT rest of week to recover schedule."
          }
        ],
        "related_cos": [
          { "co_number": "CO-009", "amount": 326200, "status": "Approved" }
        ],
        "related_rfis": [
          { "rfi_number": "RFI-089", "subject": "Conflict at grid D-7", "days_open": 23 }
        ],
        "material_issues": [
          { "delivery_id": "DEL-044", "delay_days": 8, "condition": "Partial shipment" }
        ]
      },

      "reasoning": {
        "root_cause": "Crew mobilized March 10 but spiral duct shipment (DEL-044) arrived 8 days late...",
        "contributing_factors": [
          "Material delivery delay (DEL-044, 8 days)",
          "OT recovery push (31% OT ratio vs 12% baseline)",
          "Verbal scope addition (6 corridor grilles, no CO)",
          "RFI-089 unresolved for 23 days"
        ],
        "recovery_actions": [
          "File CO for corridor grille addition (~$8,500)",
          "Back-charge GC for idle time ($14,200)",
          "Bill OT premium against CO-009 ($29,300)"
        ],
        "recoverable_amount": 52000,
        "confidence": "HIGH"
      },

      "scoring": {
        "overrun_severity": 17.9,
        "financial_impact": 98200,
        "recoverability_pct": 53,
        "schedule_risk_days": 5
      }
    }
  ]
}
```

---

## Health Scoring — Deterministic

```
  HEALTH SCORE: 0-100 (code computes, NOT the LLM)
  ═════════════════════════════════════════════════

  Start at 100, deduct points:

  ┌──────────────────────────────────┬──────────┬──────────────┐
  │  FACTOR                          │ WEIGHT   │ DEDUCTION    │
  ├──────────────────────────────────┼──────────┼──────────────┤
  │  Margin erosion > 2%             │  -25 max │ -5 per 1%    │
  │  Labor overrun (worst SOV line)  │  -20 max │ -2 per 1%    │
  │  Billing lag > 3%                │  -15 max │ -3 per 1%    │
  │  Pending CO exposure > 1%        │  -15 max │ -3 per 1%    │
  │  Orphan RFIs (cost impact, no CO)│  -10 max │ -3 per RFI   │
  │  Overdue RFIs                    │  -10 max │ -2 per RFI   │
  │  Material variance > 5%          │  -5 max  │ -1 per 1%    │
  └──────────────────────────────────┴──────────┴──────────────┘

  STATUS BANDS:
    80-100  GREEN   "On track"
    50-79   YELLOW  "Needs attention"
    0-49    RED     "At risk"
```

---

## Frontend — State by State

### STATE 1: Page Load (Cold)

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  HVAC Portfolio Monitor                                                  │
  │                                                                          │
  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
  │  │                 │  │                 │  │                 │         │
  │  │  Mercy General  │  │  Riverside      │  │  Greenfield     │         │
  │  │  Hospital       │  │  Office Tower   │  │  Elementary     │         │
  │  │                 │  │                 │  │                 │         │
  │  │  $35.2M         │  │  $30.3M         │  │  $5.5M          │         │
  │  │  Mar 2024 —     │  │  Feb 2024 —     │  │  Feb 2024 —     │         │
  │  │  Sep 2025       │  │  Jan 2026       │  │  Apr 2025       │         │
  │  │                 │  │                 │  │                 │         │
  │  │  GC: Turner     │  │  GC: DPR        │  │  GC: DPR        │         │
  │  │                 │  │                 │  │                 │         │
  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
  │                                                                          │
  │  ┌─────────────────┐  ┌─────────────────┐                               │
  │  │                 │  │                 │                               │
  │  │  Summit Data    │  │  Harbor View    │   No colors yet.             │
  │  │  Center         │  │  Condominiums   │   No scores.                 │
  │  │                 │  │                 │   Just basic contract        │
  │  │  $16.3M         │  │  $13.7M         │   info from contracts.csv    │
  │  │  Feb 2024 —     │  │  Mar 2024 —     │                               │
  │  │  Nov 2024       │  │  Nov 2025       │                               │
  │  │                 │  │                 │                               │
  │  │  GC: DPR        │  │  GC: Skanska    │                               │
  │  │                 │  │                 │                               │
  │  └─────────────────┘  └─────────────────┘                               │
  │                                                                          │
  │  ┌────────────────────────────────────────────────────────────────────┐  │
  │  │                                                                    │  │
  │  │                    [ Run Real-Time Analysis ]                       │  │
  │  │                                                                    │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘

  Data source: contracts.csv only (5 rows, served at page load)
  LLM calls: 0
```

### STATE 2: After "Run Real-Time Analysis"

```
  User clicks [ Run Real-Time Analysis ]
       │
       ▼
  Frontend calls /api/portfolio
       │
       ▼
  Backend returns pre-computed portfolio summary
  (already computed at startup — just serves JSON)
       │
       ▼
  Cards animate and refresh with colors + scores

  ┌──────────────────────────────────────────────────────────────────────────┐
  │  HVAC Portfolio Monitor                        Analysis: Complete        │
  │                                                                          │
  │  Portfolio Health: 58/100  │  At Risk: 2  │  Watch: 2  │  Healthy: 1   │
  │                                                                          │
  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐  │
  │  │ ██████████████████  │  │ ██████████████████  │  │ ████████████████│  │
  │  │ RED                 │  │ YELLOW              │  │ GREEN           │  │
  │  │                     │  │                     │  │                 │  │
  │  │ Mercy General       │  │ Riverside Office    │  │ Greenfield      │  │
  │  │ Hospital            │  │ Tower               │  │ Elementary      │  │
  │  │                     │  │                     │  │                 │  │
  │  │ Health: 33/100      │  │ Health: 62/100      │  │ Health: 87/100  │  │
  │  │ Margin: 7.1%        │  │ Margin: 11.2%       │  │ Margin: 14.1%   │  │
  │  │ (bid was 15.2%)     │  │ (bid was 14.0%)     │  │ (bid was 15.0%) │  │
  │  │                     │  │                     │  │                 │  │
  │  │ 3 issues detected   │  │ 1 issue detected    │  │ On track        │  │
  │  │                     │  │                     │  │                 │  │
  │  │ [ View Insights ]   │  │ [ View Insights ]   │  │ [ View Insights]│  │
  │  └─────────────────────┘  └─────────────────────┘  └─────────────────┘  │
  │                                                                          │
  │  ┌─────────────────────┐  ┌─────────────────────┐                       │
  │  │ ██████████████████  │  │ ██████████████████  │                       │
  │  │ RED                 │  │ YELLOW              │                       │
  │  │                     │  │                     │                       │
  │  │ Summit Data         │  │ Harbor View         │                       │
  │  │ Center              │  │ Condominiums        │                       │
  │  │                     │  │                     │                       │
  │  │ Health: 41/100      │  │ Health: 58/100      │                       │
  │  │ Margin: 9.2%        │  │ Margin: 11.4%       │                       │
  │  │ (bid was 14.5%)     │  │ (bid was 13.8%)     │                       │
  │  │                     │  │                     │                       │
  │  │ 2 issues detected   │  │ 1 issue detected    │                       │
  │  │                     │  │                     │                       │
  │  │ [ View Insights ]   │  │ [ View Insights ]   │                       │
  │  └─────────────────────┘  └─────────────────────┘                       │
  │                                                                          │
  │  ┌────────────────────────────────────────────────────────────────────┐  │
  │  │  Chat: "2 projects are at critical risk. Mercy Hospital has the   │  │
  │  │  highest margin erosion at 8.1%. Click any card for details."     │  │
  │  │  [──────────────────────────────────────────────── Send]          │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘

  Data source: /api/portfolio (pre-computed JSON, served instantly)
  LLM calls: 0
```

### STATE 3: Insights Panel (per project)

```
  User clicks [ View Insights ] on Mercy Hospital
       │
       ▼
  Frontend calls /api/dossier/PRJ-2024-001
       │
       ▼
  Returns full dossier JSON (pre-computed)

  ┌──────────────────────────────────────────────────────────────────────────┐
  │  ◄ Back to Portfolio                                                     │
  │                                                                          │
  │  Mercy General Hospital — HVAC Modernization            ██ RED  33/100  │
  │  $35.2M  │  Turner Construction  │  Mar 2024 — Sep 2025                 │
  │                                                                          │
  │  ┌─── FINANCIAL SUMMARY ─────────────────────────────────────────────┐  │
  │  │                                                                    │  │
  │  │   Bid Margin       Realized       Erosion        At Stake         │  │
  │  │   ┌───────┐        ┌───────┐      ┌───────┐     ┌──────────┐    │  │
  │  │   │ 15.2% │   →    │  7.1% │   =  │  8.1% │  =  │  $2.7M   │    │  │
  │  │   └───────┘        └───────┘      └───────┘     └──────────┘    │  │
  │  │                                                                    │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  │  ┌─── ISSUES DETECTED ───────────────────────────────────────────────┐  │
  │  │                                                                    │  │
  │  │  ┌──────────────────────────────────────────────────────────────┐ │  │
  │  │  │  #1  LABOR OVERRUN                          Severity: HIGH  │ │  │
  │  │  │      Ductwork Install (SOV-04)                              │ │  │
  │  │  │      17.9% over estimate  │  $98K overrun                   │ │  │
  │  │  │                                                              │ │  │
  │  │  │  First detected: Mar 19, 2025                                │ │  │
  │  │  │  Worst day: Apr 3, 2025 (OT hit 31%)                        │ │  │
  │  │  │                                                              │ │  │
  │  │  │  [ View Reasoning ]                                          │ │  │
  │  │  └──────────────────────────────────────────────────────────────┘ │  │
  │  │                                                                    │  │
  │  │  ┌──────────────────────────────────────────────────────────────┐ │  │
  │  │  │  #2  PENDING CO EXPOSURE                    Severity: HIGH  │ │  │
  │  │  │      3 unapproved change orders                              │ │  │
  │  │  │      $287K at risk  │  Avg 34 days pending                   │ │  │
  │  │  │                                                              │ │  │
  │  │  │  First detected: Apr 2, 2025                                 │ │  │
  │  │  │  Worst exposure: CO-017 ($142K, 41 days)                     │ │  │
  │  │  │                                                              │ │  │
  │  │  │  [ View Reasoning ]                                          │ │  │
  │  │  └──────────────────────────────────────────────────────────────┘ │  │
  │  │                                                                    │  │
  │  │  ┌──────────────────────────────────────────────────────────────┐ │  │
  │  │  │  #3  ORPHAN RFI                           Severity: MEDIUM  │ │  │
  │  │  │      RFI-089 — Duct conflict at grid D-7                     │ │  │
  │  │  │      23 days open  │  10 days overdue                        │ │  │
  │  │  │      Estimated exposure: $35K-$55K                           │ │  │
  │  │  │                                                              │ │  │
  │  │  │  [ View Reasoning ]                                          │ │  │
  │  │  └──────────────────────────────────────────────────────────────┘ │  │
  │  │                                                                    │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  │  ┌─── CHAT ──────────────────────────────────────────────────────────┐  │
  │  │  Ask anything about this project...                                │  │
  │  │  [──────────────────────────────────────────────── Send]           │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘

  Data source: /api/dossier/PRJ-2024-001 (pre-computed JSON)
  LLM calls: 0
```

### STATE 3b: "View Reasoning" Expanded

```
  User clicks [ View Reasoning ] on Issue #1

  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │  #1  LABOR OVERRUN — Ductwork Install (SOV-04)                          │
  │                                                                          │
  │  ┌─── TIMELINE OF IMPACT ────────────────────────────────────────────┐  │
  │  │                                                                    │  │
  │  │  Mar 10  Crew mobilized for ductwork install                       │  │
  │  │     ●───                                                           │  │
  │  │  Mar 12  DEL-044 (spiral duct) expected — DID NOT ARRIVE           │  │
  │  │     ●─── Field note: "Waiting on duct delivery, crew              │  │
  │  │          reassigned to piping"                                     │  │
  │  │  Mar 14  Verbal scope add documented                               │  │
  │  │     ●─── Field note: "GC asked us to add 6 grilles               │  │
  │  │          in corridor per owner walkthrough — no paperwork"        │  │
  │  │  Mar 18  DEL-044 arrives (8 days late)                             │  │
  │  │     ●─── Field note: "Shifted 6 guys back to ductwork.           │  │
  │  │          Running OT rest of week to recover schedule"             │  │
  │  │  Mar 19  TRIGGER: Burn ratio crosses 1.15x                        │  │
  │  │     ●───                                                           │  │
  │  │  Apr 3   Worst day: OT ratio hits 31%                              │  │
  │  │     ●───                                                           │  │
  │  │                                                                    │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  │  ┌─── ROOT CAUSE (AI Analysis) ──────────────────────────────────────┐  │
  │  │                                                                    │  │
  │  │  Crew was mobilized March 10 but spiral duct shipment (DEL-044)   │  │
  │  │  arrived 8 days late. During the wait, crew was reassigned to     │  │
  │  │  piping but returned to ductwork on overtime to recover schedule. │  │
  │  │  Additionally, a verbal scope addition (6 corridor grilles) was   │  │
  │  │  documented in field notes on March 14 with no change order       │  │
  │  │  filed. This represents unbilled scope change.                    │  │
  │  │                                                                    │  │
  │  │  Confidence: HIGH                                                  │  │
  │  │  Basis: Multiple field notes corroborate. Material delay in       │  │
  │  │  delivery records. OT spike visible in labor logs.                │  │
  │  │                                                                    │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  │  ┌─── ACTION ITEMS ──────────────────────────────────────────────────┐  │
  │  │                                                                    │  │
  │  │  1. [URGENT] File CO for corridor grille addition        ~$8,500  │  │
  │  │     Evidence: Field note FN-2025-03-14-007                        │  │
  │  │                                                                    │  │
  │  │  2. [URGENT] Back-charge GC for idle crew time          ~$14,200  │  │
  │  │     8 days x crew cost, caused by site coordination               │  │
  │  │                                                                    │  │
  │  │  3. [THIS WEEK] Bill OT premium against CO-009          ~$29,300  │  │
  │  │     OT was driven by schedule recovery from delays                │  │
  │  │                                                                    │  │
  │  │  Total recovery potential: $52,000                                │  │
  │  │                                                                    │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  │  ┌─── SCORING ───────────────────────────────────────────────────────┐  │
  │  │                                                                    │  │
  │  │  Overrun Severity   ████████████████████░░░░░  17.9%  HIGH        │  │
  │  │  Financial Impact   ████████████████░░░░░░░░░  $98K   HIGH        │  │
  │  │  Recoverability     ████████████░░░░░░░░░░░░░  53%    MEDIUM      │  │
  │  │  Schedule Risk      ██████████████████░░░░░░░  5 days HIGH        │  │
  │  │                                                                    │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘

  ALL of this is from the pre-computed dossier JSON.
  LLM calls: 0
```

---

## Chat Architecture — Direct Context Injection

**No RAG needed.** The dossier JSON is small enough (~5-8K tokens per project) to inject directly into the LLM system prompt. This is simpler, faster, and avoids the complexity of embedding + vector search for structured data that fits in a single context window.

```
  WHY NOT RAG?
  ════════════

  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                 │
  │  RAG approach (OVERKILL for this problem):                      │
  │  ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
  │  │Dossier │──►│Chunk &   │──►│Embed in  │──►│Retrieve  │     │
  │  │  JSON  │   │Tokenize  │   │Vector DB │   │Top-K     │     │
  │  └────────┘   └──────────┘   └──────────┘   └──────────┘     │
  │                                                                 │
  │  Problems:                                                      │
  │    - 5-8K tokens per project = FITS IN CONTEXT DIRECTLY         │
  │    - Chunking structured JSON loses relationships               │
  │    - Embedding financial data poorly captures numeric thresholds│
  │    - Extra infra (vector DB) for zero benefit                   │
  │    - Retrieval might miss critical cross-references             │
  │                                                                 │
  │                                                                 │
  │  Direct injection (WHAT WE DO):                                 │
  │  ┌────────┐   ┌──────────┐                                     │
  │  │Dossier │──►│Paste into│──► LLM sees EVERYTHING. Done.       │
  │  │  JSON  │   │sys prompt│                                     │
  │  └────────┘   └──────────┘                                     │
  │                                                                 │
  │  Why this works:                                                │
  │    - Total portfolio context: ~25-30K tokens (all 5 dossiers)  │
  │    - Single project context: ~5-8K tokens                      │
  │    - Modern context windows: 128K-200K tokens                  │
  │    - We use < 5% of available context                          │
  │    - LLM sees ALL data, no retrieval gaps                      │
  │    - Zero extra infrastructure                                  │
  │                                                                 │
  └─────────────────────────────────────────────────────────────────┘
```

Chat exists at two levels: portfolio-wide and per-project. Both use **direct context injection** — the dossier JSON is pasted into the system prompt.

```
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  User types in chat                                          │
  │       │                                                      │
  │       ▼                                                      │
  │  POST /api/chat                                              │
  │  {                                                           │
  │    message: "What if CO-017 gets rejected?",                 │
  │    project_id: "PRJ-2024-001",      ◄── which project        │
  │    conversation_id: "abc123"        ◄── memory across turns  │
  │  }                                                           │
  │       │                                                      │
  │       ▼                                                      │
  │  ┌─────────────────────────────────────────────────┐        │
  │  │  VERCEL AI SDK — streamText()                   │        │
  │  │                                                 │        │
  │  │  MODEL: v0 / frontend LLM (via Vercel)          │        │
  │  │                                                 │        │
  │  │  SYSTEM PROMPT:                                 │        │
  │  │  "You are an HVAC construction financial        │        │
  │  │   analyst. Below is the complete dossier for    │        │
  │  │   this project including health scores,         │        │
  │  │   detected issues, root causes, and evidence.   │        │
  │  │   Answer the user's question using this data.   │        │
  │  │   Be specific. Cite evidence. Suggest actions." │        │
  │  │                                                 │        │
  │  │  CONTEXT = DIRECT INJECTION (no RAG):           │        │
  │  │  ┌─────────────────────────────────────┐        │        │
  │  │  │ If project-level chat:              │        │        │
  │  │  │   → that project's dossier JSON     │        │        │
  │  │  │     (~5-8K tokens)                  │        │        │
  │  │  │   → pasted directly in sys prompt   │        │        │
  │  │  │                                     │        │        │
  │  │  │ If portfolio-level chat:            │        │        │
  │  │  │   → portfolio summary               │        │        │
  │  │  │   + all 5 dossier summaries         │        │        │
  │  │  │     (~12-15K tokens)                │        │        │
  │  │  │   → all pasted directly             │        │        │
  │  │  └─────────────────────────────────────┘        │        │
  │  │                                                 │        │
  │  │  TOOLS (escape hatches for deep queries):       │        │
  │  │  ┌─────────────────────────────────────┐        │        │
  │  │  │  get_field_notes(prj, date, keyword)│        │        │
  │  │  │  get_labor_detail(prj, sov_line)    │        │        │
  │  │  │  get_co_detail(co_number)           │        │        │
  │  │  │  get_rfi_detail(rfi_number)         │        │        │
  │  │  │  what_if_margin(prj, scenario)      │        │        │
  │  │  │  send_email(to, subject, body)      │        │        │
  │  │  └─────────────────────────────────────┘        │        │
  │  │                                                 │        │
  │  │  maxSteps: 8                                    │        │
  │  │  (agent can chain tools autonomously)           │        │
  │  │                                                 │        │
  │  └─────────────────────────────────────────────────┘        │
  │       │                                                      │
  │       ▼                                                      │
  │  Streamed response back to frontend                          │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

---

## Backend Reasoning — Haiku via Claude Code tmux

The backend reasoning (Step D in the pipeline) uses **Claude Haiku** model invoked through **Claude Code running in a tmux session**. This is the cheapest, fastest approach for generating root-cause analysis from evidence bundles.

```
  WHY HAIKU + CLAUDE CODE tmux?
  ═════════════════════════════

  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  Option A: API calls to Claude ($$)                          │
  │    - Need API key management                                │
  │    - Need HTTP client setup                                  │
  │    - Need retry/error handling                               │
  │    - Need billing account                                    │
  │                                                              │
  │  Option B: Claude Code tmux (what we do) ✓                  │
  │    - Already authenticated (your Claude Code session)        │
  │    - Run in background tmux pane                             │
  │    - Feed prompt + evidence → get JSON back                  │
  │    - Haiku model for speed + low cost                       │
  │    - No extra infrastructure                                 │
  │    - Perfect for batch pre-computation                       │
  │                                                              │
  │  Haiku stats:                                                │
  │    - Input: $0.25 / million tokens                           │
  │    - Output: $1.25 / million tokens                          │
  │    - Speed: ~50 tokens/sec                                   │
  │    - Per trigger reasoning: ~2K tokens in, ~500 tokens out   │
  │    - 5 projects × 2-3 triggers = 10-15 calls                │
  │    - Total cost: ~$0.01-0.02 (essentially free)             │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

### The Reasoning Prompt Architecture

For each trigger detected in Step C, we build an evidence bundle and send it to Haiku with a carefully crafted prompt.

```
  REASONING GENERATION FLOW (per trigger)
  ════════════════════════════════════════

  ┌──────────────────┐
  │ TRIGGER           │
  │ type: LABOR_OVERRUN│
  │ date: 2025-03-19  │
  │ sov_line: SOV-04  │
  │ burn_ratio: 1.15  │
  └────────┬─────────┘
           │
           │  evidence-puller grabs:
           ▼
  ┌──────────────────────────────────────────────────────────┐
  │  EVIDENCE BUNDLE (assembled by code, NOT LLM)            │
  │                                                          │
  │  metrics: {                                              │
  │    burn_ratio: 1.15,                                     │
  │    overrun_pct: 17.9,                                    │
  │    overrun_cost: 98200,                                  │
  │    ot_ratio: 0.31,                                       │
  │    estimated_hours: 3850,                                │
  │    actual_hours: 4540                                    │
  │  }                                                       │
  │                                                          │
  │  field_notes: [                                          │
  │    { date: "2025-03-12", content: "Waiting on duct..." }│
  │    { date: "2025-03-14", content: "GC asked us to..." } │
  │    { date: "2025-03-18", content: "Shifted 6 guys..." } │
  │  ]                                                       │
  │                                                          │
  │  related_cos: [                                          │
  │    { co_number: "CO-009", amount: 326200, status: "..." }│
  │  ]                                                       │
  │                                                          │
  │  related_rfis: [                                         │
  │    { rfi_number: "RFI-089", subject: "...", days: 23 }  │
  │  ]                                                       │
  │                                                          │
  │  material_issues: [                                      │
  │    { delivery_id: "DEL-044", delay_days: 8, ... }       │
  │  ]                                                       │
  │                                                          │
  └───────────────────────────┬──────────────────────────────┘
                              │
                              │  sent to Haiku via Claude Code tmux
                              ▼
  ┌──────────────────────────────────────────────────────────┐
  │  HAIKU REASONING PROMPT                                  │
  │                                                          │
  │  "You are an HVAC construction cost analyst.             │
  │   A {trigger_type} was detected on {date} for           │
  │   {project_name}, SOV line: {sov_description}.          │
  │                                                          │
  │   Below is the evidence. Analyze it and respond          │
  │   in STRICT JSON format:                                 │
  │                                                          │
  │   {                                                      │
  │     root_cause: string (2-4 sentences),                  │
  │     contributing_factors: string[] (3-5 bullet points),  │
  │     recovery_actions: [                                  │
  │       { action: string, est_recovery: number,            │
  │         urgency: HIGH|MEDIUM|LOW, evidence_ref: string } │
  │     ],                                                   │
  │     recoverable_amount: number,                          │
  │     confidence: HIGH|MEDIUM|LOW,                         │
  │     confidence_basis: string (why this confidence level) │
  │   }                                                      │
  │                                                          │
  │   Rules:                                                 │
  │   - Only cite evidence actually present above            │
  │   - Root cause must connect timeline events              │
  │   - Recovery actions must reference specific COs/RFIs   │
  │   - Amounts must be plausible given the metrics          │
  │   - If evidence is thin, say confidence: LOW"            │
  │                                                          │
  │   EVIDENCE:                                              │
  │   {evidence_bundle_json}                                 │
  │                                                          │
  └───────────────────────────┬──────────────────────────────┘
                              │
                              │  Haiku responds with JSON
                              ▼
  ┌──────────────────────────────────────────────────────────┐
  │  HAIKU OUTPUT (parsed into dossier.triggers[].reasoning) │
  │                                                          │
  │  {                                                       │
  │    "root_cause": "Crew mobilized March 10 but spiral...",│
  │    "contributing_factors": [                              │
  │      "Material delivery delay (DEL-044, 8 days)",        │
  │      "OT recovery push (31% OT ratio vs 12% baseline)", │
  │      "Verbal scope addition (6 corridor grilles, no CO)",│
  │      "RFI-089 unresolved for 23 days"                    │
  │    ],                                                    │
  │    "recovery_actions": [                                 │
  │      { "action": "File CO for corridor grille add...",   │
  │        "est_recovery": 8500,                             │
  │        "urgency": "HIGH",                                │
  │        "evidence_ref": "FN-2025-03-14-007" },           │
  │      { "action": "Back-charge GC for idle crew...",      │
  │        "est_recovery": 14200,                            │
  │        "urgency": "HIGH",                                │
  │        "evidence_ref": "DEL-044 delay" },               │
  │      { "action": "Bill OT premium against CO-009...",    │
  │        "est_recovery": 29300,                            │
  │        "urgency": "MEDIUM",                              │
  │        "evidence_ref": "CO-009" }                        │
  │    ],                                                    │
  │    "recoverable_amount": 52000,                          │
  │    "confidence": "HIGH",                                 │
  │    "confidence_basis": "Multiple field notes corr..."    │
  │  }                                                       │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### tmux Operation Flow

```
  HOW THE CLAUDE CODE tmux OPERATION WORKS
  ═════════════════════════════════════════

  Main process (our build script)
       │
       │  For each project's triggers:
       │
       ├──► tmux new-session -d -s reasoning
       │
       │    Inside tmux:
       │    ┌───────────────────────────────────────────┐
       │    │  claude --model haiku --print              │
       │    │    --system "HVAC cost analyst prompt"     │
       │    │    --message "{evidence_bundle_json}"      │
       │    │                                            │
       │    │  → Haiku processes and returns JSON        │
       │    │  → Output captured to file                 │
       │    └───────────────────────────────────────────┘
       │
       ├──► Read output file, parse JSON
       │
       ├──► Inject into dossier.triggers[i].reasoning
       │
       └──► Next trigger (repeat)

  Total triggers across 5 projects: ~10-15
  Time per trigger: ~2-5 seconds (Haiku is fast)
  Total reasoning generation: ~30-75 seconds
  Total cost: ~$0.01-0.02
```

---

## Data Flow — Full Journey

```
  FROM CSV TO USER'S SCREEN — THE FULL JOURNEY
  ═════════════════════════════════════════════

  ┌──────────┐
  │ 10 CSVs  │
  │ 18,312   │
  │ records  │
  └────┬─────┘
       │
       │ STARTUP (once)
       ▼
  ┌──────────────────────┐
  │ Parse + compute      │
  │ all metrics          │
  │ all trigger days     │
  │ all evidence bundles │
  └──────────┬───────────┘
             │
             │ 5-10 LLM calls (one-time)
             ▼
  ┌──────────────────────┐
  │ LLM generates        │
  │ reasoning per trigger│
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ 6 JSON files stored  │
  │ portfolio.json       │
  │ prj-001 thru 005.json│
  └──────────┬───────────┘
             │
             │  READY TO SERVE
             │
  ═══════════╪══════════════════════════════════
             │
             │  USER ARRIVES
             ▼
  ┌──────────────────────┐
  │ Page loads           │◄── contracts.csv basics only
  │ 5 dossier cards      │    (name, value, dates)
  │ No colors yet        │
  └──────────┬───────────┘
             │
             │  USER CLICKS "Run Real-Time Analysis"
             ▼
  ┌──────────────────────┐
  │ /api/portfolio       │◄── serves portfolio.json
  │ returns instantly    │    LLM calls: 0
  └──────────┬───────────┘
             │
             │  Cards turn RED/YELLOW/GREEN
             │  Scores appear
             │
             │  USER CLICKS "View Insights" on PRJ-001
             ▼
  ┌──────────────────────┐
  │ /api/dossier/001     │◄── serves prj-001.json
  │ returns instantly    │    LLM calls: 0
  └──────────┬───────────┘
             │
             │  Issues listed with dates + metrics
             │
             │  USER CLICKS "View Reasoning" on Issue #1
             ▼
  ┌──────────────────────┐
  │ Expand reasoning     │◄── already in the JSON
  │ panel in-place       │    timeline, root cause,
  │ No API call needed   │    actions, scoring
  │                      │    LLM calls: 0
  └──────────┬───────────┘
             │
             │  USER TYPES IN CHAT
             │  "What should I tell the GC about CO-017?"
             ▼
  ┌──────────────────────┐
  │ /api/chat            │◄── LLM call with dossier
  │ streamText()         │    as context (~5-8K tokens)
  │ Vercel AI SDK        │    THIS is where LLM cost lives
  │                      │
  │ Response streamed    │    Tools available if LLM needs
  │ back in real-time    │    to dig deeper
  └──────────────────────┘
```

---

## File / Module Structure

```
  PROJECT STRUCTURE
  ═════════════════

  hvac-margin-agent/
  │
  ├── data/
  │   ├── contracts.csv
  │   ├── sov.csv
  │   ├── sov_budget.csv
  │   ├── labor_logs.csv
  │   ├── material_deliveries.csv
  │   ├── billing_history.csv
  │   ├── billing_line_items.csv
  │   ├── change_orders.csv
  │   ├── rfis.csv
  │   └── field_notes.csv
  │
  ├── lib/
  │   ├── data-loader.ts          ◄── A: parse CSVs, index by project
  │   ├── compute-engine.ts       ◄── B: all deterministic calculations
  │   ├── trigger-detector.ts     ◄── C: find threshold crossings
  │   ├── evidence-puller.ts      ◄── D: pull field notes/COs/RFIs per trigger
  │   ├── reasoning-engine.ts     ◄── E: Haiku calls via Claude Code tmux
  │   ├── dossier-builder.ts      ◄── F: assemble final JSON per project
  │   └── tools/
  │       ├── get-field-notes.ts      ◄── chat escape hatch
  │       ├── get-labor-detail.ts     ◄── chat escape hatch
  │       ├── get-co-detail.ts        ◄── chat escape hatch
  │       ├── get-rfi-detail.ts       ◄── chat escape hatch
  │       ├── what-if-margin.ts       ◄── chat escape hatch
  │       └── send-email.ts           ◄── hackathon requirement
  │
  ├── app/
  │   ├── page.tsx                ◄── portfolio page (STATE 1 & 2)
  │   ├── project/[id]/page.tsx   ◄── dossier page (STATE 3)
  │   ├── api/
  │   │   ├── portfolio/
  │   │   │   └── route.ts        ◄── serves portfolio.json
  │   │   ├── dossier/[id]/
  │   │   │   └── route.ts        ◄── serves prj-xxx.json
  │   │   ├── chat/
  │   │   │   └── route.ts        ◄── Vercel AI SDK chat endpoint
  │   │   └── email/
  │   │       └── route.ts        ◄── email sending endpoint
  │   └── components/
  │       ├── portfolio-grid.tsx       ◄── 5 project cards
  │       ├── project-card.tsx         ◄── single card with health color
  │       ├── dossier-header.tsx       ◄── financial summary bar
  │       ├── issue-card.tsx           ◄── collapsible issue with reasoning
  │       ├── reasoning-panel.tsx      ◄── timeline + root cause + actions
  │       ├── scoring-bars.tsx         ◄── severity/impact/recovery bars
  │       └── chat-panel.tsx           ◄── Vercel AI SDK useChat hook
  │
  └── research.md                 ◄── this document
```

---

## Cost Summary

```
  ┌────────────────────────────────┬─────────────┬──────────────────────────┐
  │  USER ACTION                   │  LLM COST   │  DATA SOURCE             │
  ├────────────────────────────────┼─────────────┼──────────────────────────┤
  │  Page load                     │  $0         │  contracts.csv (5 rows)  │
  │  Click "Run Analysis"          │  $0         │  portfolio.json          │
  │  See health colors/scores      │  $0         │  portfolio.json          │
  │  Click "View Insights"         │  $0         │  prj-xxx.json            │
  │  See issues + metrics          │  $0         │  prj-xxx.json            │
  │  Click "View Reasoning"        │  $0         │  prj-xxx.json            │
  │  See root cause + actions      │  $0         │  prj-xxx.json            │
  │  Type in chat                  │  ~$0.01/msg │  LLM + dossier context   │
  │  Agent sends email             │  ~$0.01     │  LLM tool call           │
  ├────────────────────────────────┼─────────────┼──────────────────────────┤
  │  ONE-TIME: Reasoning gen       │  ~$0.02     │  Haiku, Claude Code tmux │
  │  (10-15 triggers × Haiku)      │             │  ~30-75 seconds total    │
  │                                │             │                          │
  │  PER VISIT (no chat)           │  $0         │  Pure JSON serving       │
  │  PER CHAT MESSAGE              │  ~$0.01     │  Direct context injection│
  │                                │             │  ~5-8K token context     │
  │                                │             │  NO RAG, NO vector DB    │
  └────────────────────────────────┴─────────────┴──────────────────────────┘

  INFRASTRUCTURE REQUIRED:
  ════════════════════════
  ┌───────────────────────────────────────────────────────────┐
  │  ✓  Claude Code CLI (already installed)                  │
  │  ✓  tmux (already available on most systems)             │
  │  ✓  Haiku model ($0.25/$1.25 per million tokens)         │
  │  ✓  Vercel + AI SDK (for frontend chat)                  │
  │  ✗  NO vector database needed                            │
  │  ✗  NO embedding pipeline needed                         │
  │  ✗  NO RAG infrastructure needed                         │
  │  ✗  NO separate API key management for reasoning         │
  └───────────────────────────────────────────────────────────┘
```

---

*Research compiled for the HVAC Margin Rescue Challenge hackathon.*
