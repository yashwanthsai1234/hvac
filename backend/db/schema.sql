-- HVAC Margin Rescue Agent — SQLite Schema
-- All 10 raw CSV tables + computed tables + dossier storage

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ============================================================
-- RAW DATA TABLES (imported from CSV)
-- ============================================================

CREATE TABLE IF NOT EXISTS contracts (
    project_id                  TEXT PRIMARY KEY,
    project_name                TEXT NOT NULL,
    original_contract_value     REAL NOT NULL,
    contract_date               TEXT NOT NULL,
    substantial_completion_date TEXT NOT NULL,
    retention_pct               REAL NOT NULL,
    payment_terms               TEXT,
    gc_name                     TEXT,
    architect                   TEXT,
    engineer_of_record          TEXT
);

CREATE TABLE IF NOT EXISTS sov (
    sov_line_id     TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES contracts(project_id),
    line_number     INTEGER NOT NULL,
    description     TEXT NOT NULL,
    scheduled_value REAL NOT NULL,
    labor_pct       REAL,
    material_pct    REAL
);
CREATE INDEX IF NOT EXISTS idx_sov_project ON sov(project_id);

CREATE TABLE IF NOT EXISTS sov_budget (
    sov_line_id             TEXT PRIMARY KEY REFERENCES sov(sov_line_id),
    project_id              TEXT NOT NULL REFERENCES contracts(project_id),
    estimated_labor_hours   REAL,
    estimated_labor_cost    REAL,
    estimated_material_cost REAL,
    estimated_equipment_cost REAL,
    estimated_sub_cost      REAL,
    productivity_factor     REAL,
    key_assumptions         TEXT
);
CREATE INDEX IF NOT EXISTS idx_sov_budget_project ON sov_budget(project_id);

CREATE TABLE IF NOT EXISTS labor_logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id            TEXT NOT NULL,
    project_id        TEXT NOT NULL REFERENCES contracts(project_id),
    date              TEXT NOT NULL,
    employee_id       TEXT,
    role              TEXT,
    sov_line_id       TEXT REFERENCES sov(sov_line_id),
    hours_st          REAL NOT NULL DEFAULT 0,
    hours_ot          REAL NOT NULL DEFAULT 0,
    hourly_rate       REAL NOT NULL,
    burden_multiplier REAL NOT NULL DEFAULT 1.0,
    work_area         TEXT,
    cost_code         TEXT
);
CREATE INDEX IF NOT EXISTS idx_labor_project_date ON labor_logs(project_id, date);
CREATE INDEX IF NOT EXISTS idx_labor_sov ON labor_logs(sov_line_id);

CREATE TABLE IF NOT EXISTS material_deliveries (
    delivery_id      TEXT PRIMARY KEY,
    project_id       TEXT NOT NULL REFERENCES contracts(project_id),
    date             TEXT NOT NULL,
    sov_line_id      TEXT REFERENCES sov(sov_line_id),
    material_category TEXT,
    item_description TEXT,
    quantity         REAL,
    unit             TEXT,
    unit_cost        REAL,
    total_cost       REAL NOT NULL,
    po_number        TEXT,
    vendor           TEXT,
    received_by      TEXT,
    condition_notes  TEXT
);
CREATE INDEX IF NOT EXISTS idx_material_project ON material_deliveries(project_id);
CREATE INDEX IF NOT EXISTS idx_material_sov ON material_deliveries(sov_line_id);

CREATE TABLE IF NOT EXISTS billing_history (
    project_id         TEXT NOT NULL REFERENCES contracts(project_id),
    application_number INTEGER NOT NULL,
    period_end         TEXT NOT NULL,
    period_total       REAL,
    cumulative_billed  REAL,
    retention_held     REAL,
    net_payment_due    REAL,
    status             TEXT,
    payment_date       TEXT,
    line_item_count    INTEGER,
    PRIMARY KEY (project_id, application_number)
);
CREATE INDEX IF NOT EXISTS idx_billing_project ON billing_history(project_id);

CREATE TABLE IF NOT EXISTS billing_line_items (
    sov_line_id       TEXT NOT NULL REFERENCES sov(sov_line_id),
    project_id        TEXT NOT NULL REFERENCES contracts(project_id),
    application_number INTEGER NOT NULL,
    description       TEXT,
    scheduled_value   REAL,
    previous_billed   REAL,
    this_period       REAL,
    total_billed      REAL,
    pct_complete      REAL,
    balance_to_finish REAL,
    PRIMARY KEY (sov_line_id, project_id, application_number),
    FOREIGN KEY (project_id, application_number) REFERENCES billing_history(project_id, application_number)
);
CREATE INDEX IF NOT EXISTS idx_billing_items_sov ON billing_line_items(sov_line_id);
CREATE INDEX IF NOT EXISTS idx_billing_items_project ON billing_line_items(project_id);

CREATE TABLE IF NOT EXISTS change_orders (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    co_number            TEXT NOT NULL,
    project_id           TEXT NOT NULL REFERENCES contracts(project_id),
    date_submitted       TEXT NOT NULL,
    reason_category      TEXT,
    description          TEXT,
    amount               REAL NOT NULL,
    status               TEXT NOT NULL,
    related_rfi          TEXT,
    affected_sov_lines   TEXT,
    labor_hours_impact   REAL,
    schedule_impact_days REAL,
    submitted_by         TEXT,
    approved_by          TEXT
);
CREATE INDEX IF NOT EXISTS idx_co_project ON change_orders(project_id);
CREATE INDEX IF NOT EXISTS idx_co_status ON change_orders(status);
CREATE INDEX IF NOT EXISTS idx_co_number ON change_orders(co_number);

CREATE TABLE IF NOT EXISTS rfis (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    rfi_number       TEXT NOT NULL,
    project_id       TEXT NOT NULL REFERENCES contracts(project_id),
    date_submitted   TEXT NOT NULL,
    subject          TEXT,
    submitted_by     TEXT,
    assigned_to      TEXT,
    priority         TEXT,
    status           TEXT NOT NULL,
    date_required    TEXT,
    date_responded   TEXT,
    response_summary TEXT,
    cost_impact      TEXT,
    schedule_impact  TEXT
);
CREATE INDEX IF NOT EXISTS idx_rfi_project ON rfis(project_id);
CREATE INDEX IF NOT EXISTS idx_rfi_status ON rfis(status);
CREATE INDEX IF NOT EXISTS idx_rfi_number ON rfis(rfi_number);

CREATE TABLE IF NOT EXISTS field_notes (
    note_id         TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES contracts(project_id),
    date            TEXT NOT NULL,
    author          TEXT,
    note_type       TEXT,
    content         TEXT,
    photos_attached INTEGER,
    weather         TEXT,
    temp_high       REAL,
    temp_low        REAL
);
CREATE INDEX IF NOT EXISTS idx_notes_project_date ON field_notes(project_id, date);

-- ============================================================
-- COMPUTED TABLES (populated by compute engine)
-- ============================================================

CREATE TABLE IF NOT EXISTS computed_sov_metrics (
    sov_line_id            TEXT PRIMARY KEY REFERENCES sov(sov_line_id),
    project_id             TEXT NOT NULL REFERENCES contracts(project_id),
    actual_labor_cost      REAL DEFAULT 0,
    actual_labor_hours     REAL DEFAULT 0,
    actual_labor_hours_ot  REAL DEFAULT 0,
    estimated_labor_cost   REAL DEFAULT 0,
    estimated_labor_hours  REAL DEFAULT 0,
    labor_overrun_pct      REAL DEFAULT 0,
    actual_material_cost   REAL DEFAULT 0,
    estimated_material_cost REAL DEFAULT 0,
    material_variance_pct  REAL DEFAULT 0,
    total_billed           REAL DEFAULT 0,
    pct_complete           REAL DEFAULT 0,
    billing_lag            REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_comp_sov_project ON computed_sov_metrics(project_id);

CREATE TABLE IF NOT EXISTS computed_project_metrics (
    project_id              TEXT PRIMARY KEY REFERENCES contracts(project_id),
    contract_value          REAL,
    total_estimated_cost    REAL,
    total_actual_cost       REAL,
    actual_labor_cost       REAL,
    actual_material_cost    REAL,
    estimated_labor_cost    REAL,
    estimated_material_cost REAL,
    estimated_sub_cost      REAL,
    approved_co_total       REAL DEFAULT 0,
    pending_co_total        REAL DEFAULT 0,
    rejected_co_total       REAL DEFAULT 0,
    adjusted_contract_value REAL,
    bid_margin_pct          REAL,
    realized_margin_pct     REAL,
    margin_erosion_pct      REAL,
    cumulative_billed       REAL DEFAULT 0,
    earned_value            REAL DEFAULT 0,
    billing_lag             REAL DEFAULT 0,
    billing_lag_pct         REAL DEFAULT 0,
    rfi_total               INTEGER DEFAULT 0,
    rfi_open                INTEGER DEFAULT 0,
    rfi_overdue             INTEGER DEFAULT 0,
    rfi_orphan_count        INTEGER DEFAULT 0,
    rfi_avg_response_days   REAL DEFAULT 0,
    health_score            INTEGER DEFAULT 100,
    status                  TEXT DEFAULT 'GREEN'
);

CREATE TABLE IF NOT EXISTS triggers (
    trigger_id       TEXT PRIMARY KEY,
    project_id       TEXT NOT NULL REFERENCES contracts(project_id),
    date             TEXT NOT NULL,
    type             TEXT NOT NULL,
    severity         TEXT NOT NULL,
    value            REAL,
    headline         TEXT,
    affected_sov_lines TEXT,
    metrics_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_triggers_project ON triggers(project_id);

-- ============================================================
-- DOSSIER STORAGE (final output JSONs)
-- ============================================================

CREATE TABLE IF NOT EXISTS dossiers (
    project_id   TEXT PRIMARY KEY,
    dossier_json TEXT NOT NULL,
    created_at   TEXT DEFAULT (datetime('now'))
);
