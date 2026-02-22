const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchContracts() {
  const res = await fetch(`${API_BASE}/api/contracts`);
  if (!res.ok) throw new Error("Failed to fetch contracts");
  return res.json();
}

export async function fetchPortfolio() {
  const res = await fetch(`${API_BASE}/api/portfolio`);
  if (!res.ok) throw new Error("Failed to fetch portfolio");
  return res.json();
}

export async function fetchDossier(projectId: string) {
  const res = await fetch(`${API_BASE}/api/dossier/${projectId}`);
  if (!res.ok) throw new Error(`Failed to fetch dossier for ${projectId}`);
  return res.json();
}

export interface Contract {
  project_id: string;
  project_name: string;
  original_contract_value: number;
  contract_date: string;
  substantial_completion_date: string;
  gc_name: string;
  architect: string;
  retention_pct: number;
  payment_terms: string;
}

export interface ProjectSummary {
  project_id: string;
  name: string;
  contract_value: number;
  start_date: string;
  end_date: string;
  gc_name: string;
  health_score: number;
  status: string;
  bid_margin_pct: number;
  realized_margin_pct: number;
  margin_erosion_pct: number;
  approved_cos: number;
  pending_cos: number;
  billing_lag_pct: number;
  trigger_count: number;
  high_trigger_count: number;
}

export interface Portfolio {
  portfolio_health: number;
  total_contract_value: number;
  total_at_risk: number;
  project_count: number;
  at_risk_count: number;
  watch_count: number;
  healthy_count: number;
  projects: ProjectSummary[];
}

export interface TriggerReasoning {
  root_cause: string;
  contributing_factors: string[];
  recovery_actions: string[];
  recoverable_amount: number;
  confidence: string;
  scoring: {
    financial_impact: number;
    recoverability_pct: number;
    schedule_risk_days: number;
  };
}

export interface Trigger {
  trigger_id: string;
  date: string;
  type: string;
  severity: string;
  headline: string;
  value: number;
  affected_sov_lines: string;
  metrics: Record<string, number>;
  evidence: {
    field_notes: { note_id: string; date: string; author: string; content: string }[];
    related_cos: { co_number: string; amount: number; status: string; description: string | null }[];
    related_rfis: { rfi_number: string; subject: string; days_open: number; priority: string }[];
    material_issues: { delivery_id: string; date: string; material_type: string; total_cost: number }[];
  };
  reasoning: TriggerReasoning;
}

export interface Dossier {
  project_id: string;
  name: string;
  contract_value: number;
  start_date: string;
  end_date: string;
  gc_name: string;
  architect: string;
  retention_pct: number;
  health_score: number;
  status: string;
  financials: {
    estimated_cost: number;
    actual_cost: number;
    bid_margin_pct: number;
    realized_margin_pct: number;
    margin_erosion_pct: number;
    approved_cos: number;
    pending_cos: number;
    rejected_cos: number;
    adjusted_contract: number;
    cumulative_billed: number;
    earned_value: number;
    billing_lag: number;
    billing_lag_pct: number;
  };
  triggers: Trigger[];
  trigger_summary: {
    total: number;
    high: number;
    medium: number;
    by_type: Record<string, number>;
  };
}

export function formatCurrency(n: number): string {
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

export function statusColor(status: string): string {
  switch (status) {
    case "RED": return "text-red-600";
    case "YELLOW": return "text-yellow-600";
    case "GREEN": return "text-green-600";
    default: return "text-gray-400";
  }
}

export function statusBg(status: string): string {
  switch (status) {
    case "RED": return "bg-red-500";
    case "YELLOW": return "bg-yellow-500";
    case "GREEN": return "bg-green-500";
    default: return "bg-gray-300";
  }
}

export function statusBorder(status: string): string {
  switch (status) {
    case "RED": return "border-red-500";
    case "YELLOW": return "border-yellow-500";
    case "GREEN": return "border-green-500";
    default: return "border-gray-300";
  }
}
