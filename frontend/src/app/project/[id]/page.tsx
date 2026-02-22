"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchDossier, Dossier, formatCurrency, statusBg, statusColor } from "@/lib/api";
import { DossierHeader } from "@/components/dossier-header";
import { IssueCard } from "@/components/issue-card";
import { ChatPanel } from "@/components/chat-panel";

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDossier(projectId)
      .then(setDossier)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!dossier) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400">Dossier not found for {projectId}</p>
        <Link href="/" className="text-blue-400 hover:underline mt-4 inline-block">
          Back to Portfolio
        </Link>
      </div>
    );
  }

  // Sort triggers: HIGH first, then by type
  const sortedTriggers = [...dossier.triggers].sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === "HIGH" ? -1 : 1;
    return a.type.localeCompare(b.type);
  });

  return (
    <div>
      <Link href="/" className="text-sm text-gray-400 hover:text-white mb-4 inline-block">
        &larr; Back to Portfolio
      </Link>

      {/* Project header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">{dossier.name}</h2>
          <div className="text-sm text-gray-400 mt-1">
            {formatCurrency(dossier.contract_value)} &middot; {dossier.gc_name} &middot;{" "}
            {dossier.start_date} — {dossier.end_date}
          </div>
        </div>
        <div className="text-right">
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${statusBg(dossier.status)} text-white`}>
            {dossier.status}
          </span>
          <div className={`text-2xl font-bold mt-1 ${statusColor(dossier.status)}`}>
            {dossier.health_score}/100
          </div>
        </div>
      </div>

      {/* Financial summary */}
      <DossierHeader financials={dossier.financials} contractValue={dossier.contract_value} />

      {/* Trigger summary */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">
          Issues Detected ({dossier.trigger_summary.total})
        </h3>
        <div className="flex gap-3 text-sm mb-4">
          {Object.entries(dossier.trigger_summary.by_type).map(([type, count]) => (
            <span key={type} className="px-3 py-1 bg-gray-800 rounded-full text-gray-300">
              {type.replace(/_/g, " ")}: {count}
            </span>
          ))}
        </div>
      </div>

      {/* Issue cards */}
      <div className="space-y-4">
        {sortedTriggers.map((trigger) => (
          <IssueCard key={trigger.trigger_id} trigger={trigger} />
        ))}
      </div>

      <ChatPanel projectId={projectId} />
    </div>
  );
}
