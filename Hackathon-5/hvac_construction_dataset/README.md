# HVAC Construction Project Dataset

A synthetic dataset representing 5 commercial HVAC contracting projects with realistic interrelationships across all standard construction project management data categories.

## Dataset Overview

| Metric | Value |
|--------|-------|
| **Projects** | 5 |
| **Total Contract Value** | $100,988,000 |
| **Record Count** | 18,312 total records |
| **Time Period** | 2024-2026 |


---

## Data Files

### Flat Tables (CSV)

| File | Records | Description |
|------|---------|-------------|
| `contracts.csv` | 5 | Base contract information |
| `sov.csv` | 75 | Schedule of Values line items (15 per project) |
| `labor_logs.csv` | 16,195 | Daily crew time entries |
| `material_deliveries.csv` | 269 | Material receipt records |
| `change_orders.csv` | 64 | Change order requests |
| `rfis.csv` | 317 | RFI log |
| `field_notes.csv` | 1,304 | Unstructured daily field reports |
| `billing_history.csv` | 83 | Monthly pay applications (summary) |
| `billing_line_items.csv` | 964 | Pay application line item detail |

### Complete Dataset (JSON)

`hvac_construction_dataset.json` - All data in a single nested JSON file including bid estimates (not available as CSV due to nested structure).

---

## Schema Reference

### 1. Contracts (`contracts.csv`)

```
project_id                  - Unique project identifier (PRJ-YYYY-NNN)
project_name                - Full project name
original_contract_value     - Base contract amount (USD)
contract_date               - Contract execution date
substantial_completion_date - Target completion date
retention_pct               - Retention percentage (typically 10%)
payment_terms               - Payment terms (e.g., "Net 30")
gc_name                     - General Contractor name
architect                   - Architect of record
engineer_of_record          - MEP Engineer
```

### 2. Schedule of Values (`sov.csv`)

```
project_id      - Links to contracts.project_id
sov_line_id     - Unique SOV line identifier
line_number     - SOV line number (1-15)
description     - Work description
scheduled_value - Dollar value for this line
labor_pct       - Estimated labor percentage (0.0-1.0)
material_pct    - Estimated material percentage (0.0-1.0)
```

**SOV Categories:**
| Line | Category |
|------|----------|
| 01 | General Conditions & Project Management |
| 02 | Submittals & Engineering |
| 03-04 | Ductwork (Fab & Install) |
| 05-06 | Piping (Hydronic & Refrigerant) |
| 07-09 | Equipment (RTUs, Chillers, Terminal Units) |
| 10-11 | Controls (Install & Commissioning) |
| 12 | Insulation |
| 13-15 | TAB, Startup, Closeout |

### 3. Labor Logs (`labor_logs.csv`)

```
project_id        - Links to project
log_id            - Unique entry ID
date              - Work date
employee_id       - Worker identifier
role              - Job classification (Foreman, Journeyman, Apprentice, etc.)
sov_line_id       - Cost-coded to SOV line
hours_st          - Straight time hours
hours_ot          - Overtime hours
hourly_rate       - Base hourly rate (USD)
burden_multiplier - Burden rate (taxes, benefits, insurance)
work_area         - Physical location on site
cost_code         - Numeric cost code (maps to SOV line_number)
```

### 4. Material Deliveries (`material_deliveries.csv`)

```
project_id        - Links to project
delivery_id       - Unique delivery ID
date              - Delivery date
sov_line_id       - Cost-coded to SOV line
material_category - Category (Ductwork, Piping, Equipment, Controls, Insulation)
item_description  - Specific material item
quantity          - Quantity received
unit              - Unit of measure (EA, LF, SHEET, etc.)
unit_cost         - Cost per unit (USD)
total_cost        - Total delivery cost (USD)
po_number         - Purchase order reference
vendor            - Supplier name
received_by       - Person who received delivery
condition_notes   - Receiving notes
```

### 5. Change Orders (`change_orders.csv`)

```
project_id          - Links to project
co_number           - Change order number (CO-NNN)
date_submitted      - Submission date
reason_category     - Category (Owner Request, Design Error, Unforeseen Condition, etc.)
description         - Detailed description
amount              - Dollar amount (positive=add, negative=credit)
status              - Status (Pending, Under Review, Approved, Rejected)
related_rfi         - Associated RFI number (if any)
affected_sov_lines  - List of impacted SOV lines
labor_hours_impact  - Estimated labor hour change
schedule_impact_days - Schedule impact in days
submitted_by        - Person who submitted
approved_by         - Approver (if approved)
```

### 6. RFI Log (`rfis.csv`)

```
project_id       - Links to project
rfi_number       - RFI number (RFI-NNN)
date_submitted   - Submission date
subject          - Question/issue description
submitted_by     - Person who submitted
assigned_to      - Party responsible for response
priority         - Priority level (Low, Medium, High, Critical)
status           - Status (Open, Pending Response, Closed)
date_required    - Date response needed
date_responded   - Actual response date
response_summary - Summary of response
cost_impact      - Boolean - has cost impact
schedule_impact  - Boolean - has schedule impact
```

### 7. Field Notes (`field_notes.csv`)

**Unstructured text field** - represents actual daily reports from superintendents/foremen.

```
project_id      - Links to project
note_id         - Unique note ID
date            - Report date
author          - Author name
note_type       - Type (Daily Report, Safety Log, Coordination Note, Issue Log, etc.)
content         - FREE TEXT - unstructured field note content
photos_attached - Number of photos attached
weather         - Weather conditions
temp_high       - High temperature (°F)
temp_low        - Low temperature (°F)
```

### 8. Billing History (`billing_history.csv` + `billing_line_items.csv`)

**Summary level:**
```
project_id         - Links to project
application_number - Pay app number (sequential)
period_end         - Billing period end date
period_total       - Total billed this period
cumulative_billed  - Total billed to date
retention_held     - Retention amount held
net_payment_due    - Net amount payable
status             - Status (Pending, Approved, Paid)
payment_date       - Date payment received
line_item_count    - Number of SOV lines billed
```

**Line item detail:**
```
sov_line_id       - SOV line reference
description       - Line description
scheduled_value   - Total scheduled value
previous_billed   - Previously billed amount
this_period       - Current period billing
total_billed      - Cumulative billed
pct_complete      - Percentage complete
balance_to_finish - Remaining value
```

### 9. Bid Estimates (JSON only)

Complex nested structure containing:
- `labor_assumptions` - Hours, rates, productivity factors, crew mix
- `material_assumptions` - Escalation, waste factors, key quotes
- `subcontractor_assumptions` - Sub quotes (insulation, TAB, controls)
- `general_conditions` - Project management, equipment, consumables
- `markup` - Overhead, profit, bond, insurance percentages
- `risk_allowances` - Contingencies
- `key_assumptions` - List of bid assumptions
- `exclusions` - What's not included
- `clarifications` - Bid clarifications

---

## Data Relationships

```
contracts (1) ──────┬──── (N) sov
                    │
                    ├──── (N) labor_logs ────── (1) sov
                    │
                    ├──── (N) material_deliveries ── (1) sov
                    │
                    ├──── (N) change_orders ──── (N) sov
                    │          │
                    │          └──── (0-1) rfis
                    │
                    ├──── (N) rfis
                    │
                    ├──── (N) field_notes
                    │
                    ├──── (N) billing_history ── (N) billing_line_items
                    │                                    │
                    │                                    └──── (1) sov
                    │
                    └──── (1) bid_estimates
```

---

## Realistic Data Characteristics

### Temporal Patterns
- Labor logs follow S-curve staffing (ramp up → peak → ramp down)
- Material deliveries precede installation phases
- RFIs cluster in early-mid project
- Billing follows earned value progression

### Financial Integrity
- SOV lines sum exactly to contract value
- Billing never exceeds scheduled values
- Change orders affect contract totals realistically
- Labor costs match burden rates × hours × rates

### Construction Realism
- Crew composition matches trade work (pipefitters for piping, sheet metal workers for duct)
- Field notes reference actual construction activities
- RFI subjects reflect real coordination issues
- Change order reasons match industry patterns

---

## Usage Examples

### Python - Load and Analyze
```python
import pandas as pd
import json

# Load CSVs
labor = pd.read_csv('labor_logs.csv')
sov = pd.read_csv('sov.csv')

# Labor cost by SOV line
labor['total_cost'] = (labor['hours_st'] + labor['hours_ot'] * 1.5) * labor['hourly_rate'] * labor['burden_multiplier']
labor_by_sov = labor.groupby('sov_line_id')['total_cost'].sum()

# Load full dataset with bid estimates
with open('hvac_construction_dataset.json') as f:
    data = json.load(f)
    
bid = data['bid_estimates'][0]
print(f"Estimated hours: {bid['labor_assumptions']['total_hours_estimated']:,}")
```

### SQL - Example Queries
```sql
-- Change order impact by project
SELECT 
    project_id,
    COUNT(*) as co_count,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as additions,
    SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as credits
FROM change_orders
WHERE status = 'Approved'
GROUP BY project_id;

-- RFI response time analysis
SELECT 
    assigned_to,
    AVG(JULIANDAY(date_responded) - JULIANDAY(date_submitted)) as avg_days
FROM rfis
WHERE date_responded IS NOT NULL
GROUP BY assigned_to;
```

---

## License

This is synthetic data generated for development, testing, and demonstration purposes. No real project data is included.

---
