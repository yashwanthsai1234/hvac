"use client";

import Link from "next/link";
import { Contract, ProjectSummary, formatCurrency, statusBorder, statusBg, statusColor } from "@/lib/api";

interface ProjectCardProps {
  contract: Contract;
  analysis?: ProjectSummary;
}

export function ProjectCard({ contract, analysis }: ProjectCardProps) {
  const isAnalyzed = !!analysis;
  const borderClass = isAnalyzed ? statusBorder(analysis.status) : "border-gray-800";

  return (
    <div
      className={`bg-gray-900 rounded-xl border-2 ${borderClass} p-5 transition-all duration-500 hover:shadow-lg`}
    >
      {/* Status badge */}
      {isAnalyzed && (
        <div className="flex items-center justify-between mb-3">
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusBg(analysis.status)} text-white`}
          >
            {analysis.status}
          </span>
          <span className={`text-sm font-bold ${statusColor(analysis.status)}`}>
            {analysis.health_score}/100
          </span>
        </div>
      )}

      {/* Project name + value */}
      <h3 className="font-semibold text-base mb-1 leading-tight">{contract.project_name}</h3>
      <div className="text-xl font-bold text-white mb-3">
        {formatCurrency(contract.original_contract_value)}
      </div>

      {/* Basic info */}
      <div className="text-xs text-gray-400 space-y-1 mb-4">
        <div>
          {contract.contract_date} — {contract.substantial_completion_date}
        </div>
        <div>GC: {contract.gc_name}</div>
      </div>

      {/* Analysis metrics */}
      {isAnalyzed && (
        <div className="space-y-2 mb-4">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Margin</span>
            <span>
              <span className="text-gray-500">{analysis.bid_margin_pct.toFixed(1)}%</span>
              {" → "}
              <span className={analysis.margin_erosion_pct > 0 ? "text-red-400" : "text-green-400"}>
                {analysis.realized_margin_pct.toFixed(1)}%
              </span>
            </span>
          </div>
          {analysis.margin_erosion_pct > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Erosion</span>
              <span className="text-red-400">{analysis.margin_erosion_pct.toFixed(1)}%</span>
            </div>
          )}
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Issues</span>
            <span>
              {analysis.high_trigger_count > 0 && (
                <span className="text-red-400">{analysis.high_trigger_count} HIGH</span>
              )}
              {analysis.trigger_count > analysis.high_trigger_count && (
                <span className="text-gray-400 ml-1">
                  +{analysis.trigger_count - analysis.high_trigger_count}
                </span>
              )}
              {analysis.trigger_count === 0 && <span className="text-green-400">None</span>}
            </span>
          </div>
        </div>
      )}

      {/* View insights link */}
      {isAnalyzed && (
        <Link
          href={`/project/${contract.project_id}`}
          className="block w-full text-center py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm font-medium transition-colors"
        >
          View Insights
        </Link>
      )}
    </div>
  );
}
