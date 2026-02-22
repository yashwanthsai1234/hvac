"use client";

import { Contract, Portfolio, ProjectSummary, formatCurrency, statusBorder } from "@/lib/api";
import { ProjectCard } from "./project-card";

interface PortfolioGridProps {
  contracts: Contract[];
  portfolio: Portfolio | null;
}

export function PortfolioGrid({ contracts, portfolio }: PortfolioGridProps) {
  // Merge contract data with portfolio analysis
  const cards = contracts.map((c) => {
    const analysis = portfolio?.projects.find((p) => p.project_id === c.project_id);
    return { contract: c, analysis };
  });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {cards.map(({ contract, analysis }) => (
        <ProjectCard key={contract.project_id} contract={contract} analysis={analysis} />
      ))}
    </div>
  );
}
