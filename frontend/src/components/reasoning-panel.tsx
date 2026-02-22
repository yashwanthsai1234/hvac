"use client";

import { Trigger, formatCurrency } from "@/lib/api";

interface ReasoningPanelProps {
  trigger: Trigger;
}

export function ReasoningPanel({ trigger }: ReasoningPanelProps) {
  const { reasoning, evidence } = trigger;

  return (
    <div className="border-t border-gray-800 p-5 bg-gray-950/50">
      {/* Scoring bars */}
      {reasoning.scoring && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <ScoreBar
            label="Financial Impact"
            value={formatCurrency(reasoning.scoring.financial_impact || 0)}
            pct={Math.min(100, (reasoning.scoring.financial_impact || 0) / 1000)}
            color="red"
          />
          <ScoreBar
            label="Recoverability"
            value={`${reasoning.scoring.recoverability_pct || 0}%`}
            pct={reasoning.scoring.recoverability_pct || 0}
            color="green"
          />
          <ScoreBar
            label="Schedule Risk"
            value={`${reasoning.scoring.schedule_risk_days || 0} days`}
            pct={Math.min(100, ((reasoning.scoring.schedule_risk_days || 0) / 30) * 100)}
            color="yellow"
          />
        </div>
      )}

      {/* Root cause */}
      <div className="mb-5">
        <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Root Cause Analysis
        </h4>
        <p className="text-sm leading-relaxed">{reasoning.root_cause}</p>
        <span
          className={`inline-block mt-2 px-2 py-0.5 rounded text-xs ${
            reasoning.confidence === "HIGH"
              ? "bg-green-500/20 text-green-400"
              : reasoning.confidence === "MEDIUM"
              ? "bg-yellow-500/20 text-yellow-400"
              : "bg-gray-500/20 text-gray-400"
          }`}
        >
          Confidence: {reasoning.confidence}
        </span>
      </div>

      {/* Contributing factors */}
      <div className="mb-5">
        <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Contributing Factors
        </h4>
        <ul className="space-y-1">
          {reasoning.contributing_factors.map((f, i) => (
            <li key={i} className="text-sm text-gray-300 flex gap-2">
              <span className="text-gray-600">•</span>
              {f}
            </li>
          ))}
        </ul>
      </div>

      {/* Recovery actions */}
      <div className="mb-5">
        <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Recovery Actions
        </h4>
        <ul className="space-y-2">
          {reasoning.recovery_actions.map((a, i) => (
            <li key={i} className="text-sm text-gray-300 flex gap-2 items-start">
              <span className="text-blue-400 font-mono text-xs mt-0.5">{i + 1}.</span>
              {a}
            </li>
          ))}
        </ul>
        {reasoning.recoverable_amount > 0 && (
          <div className="mt-3 text-sm">
            <span className="text-gray-500">Estimated recoverable: </span>
            <span className="text-green-400 font-semibold">
              {formatCurrency(reasoning.recoverable_amount)}
            </span>
          </div>
        )}
      </div>

      {/* Evidence section */}
      {evidence.field_notes.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Field Notes Evidence
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {evidence.field_notes.map((note) => (
              <div key={note.note_id} className="bg-gray-900 rounded p-3 text-xs">
                <div className="flex justify-between text-gray-500 mb-1">
                  <span>{note.author}</span>
                  <span>{note.date}</span>
                </div>
                <p className="text-gray-300">{note.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related COs */}
      {evidence.related_cos.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Related Change Orders
          </h4>
          <div className="space-y-1">
            {evidence.related_cos.map((co) => (
              <div key={co.co_number} className="flex justify-between text-sm">
                <span>
                  {co.co_number}{" "}
                  <span
                    className={
                      co.status === "Approved"
                        ? "text-green-400"
                        : co.status === "Rejected"
                        ? "text-red-400"
                        : "text-yellow-400"
                    }
                  >
                    ({co.status})
                  </span>
                </span>
                <span>{formatCurrency(co.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related RFIs */}
      {evidence.related_rfis.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Related RFIs
          </h4>
          <div className="space-y-1">
            {evidence.related_rfis.map((rfi) => (
              <div key={rfi.rfi_number} className="text-sm">
                <span className="text-blue-400">{rfi.rfi_number}</span>: {rfi.subject}
                <span className="text-gray-500 ml-2">({rfi.days_open}d open)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreBar({
  label,
  value,
  pct,
  color,
}: {
  label: string;
  value: string;
  pct: number;
  color: "red" | "green" | "yellow";
}) {
  const colors = {
    red: "bg-red-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
  };

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="font-medium text-gray-300">{value}</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${colors[color]} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(100, Math.max(2, pct))}%` }}
        />
      </div>
    </div>
  );
}
