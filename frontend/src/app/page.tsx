/**
 * frontend/src/app/page.tsx
 * ──────────────────────────
 * Root page — auth gate + Top Navigation Shell:
 *   Option 1: Reports    → ReportView (Competitor dossiers)
 *   Option 2: RAG mode   → AgentWorkflow (LangGraph Dynamic Multi-Agent System)
 *   Option 3: Competitor → CompetitorMatrix (6x5 CI Matrix & Retail Landscape)
 *   Option 4: Sources    → SourcesTable (Verified Audit Trail)
 */

"use client";

import React, { useState, useEffect } from "react";
import { getToken, clearToken, type DimensionResult, COMPETITORS, CI_DIMENSIONS } from "@/lib/api";
import LoginPage from "@/components/LoginPage";
import AgentWorkflow from "@/components/AgentWorkflow";
import ReportView from "@/components/ReportView";
import CompetitorMatrix from "@/components/CompetitorMatrix";
import SourcesTable from "@/components/SourcesTable";
import DrillDown from "@/components/DrillDown";

type Tab = "reports" | "rag_mode" | "competitor" | "sources";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "reports", label: "Reports", icon: "≡" },
  { id: "rag_mode", label: "RAG mode", icon: "⚡" },
  { id: "competitor", label: "Competitor", icon: "⊞" },
  { id: "sources", label: "Sources", icon: "⊕" },
];

export default function HomePage() {
  const [authed, setAuthed] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("reports");

  // Drilldown state (from matrix click)
  const [drilldown, setDrilldown] = useState<{
    competitor: string;
    dimension: string;
    data: DimensionResult;
  } | null>(null);

  // Check for existing token
  useEffect(() => {
    if (getToken()) setAuthed(true);
  }, []);

  if (!authed) {
    return <LoginPage onLogin={() => setAuthed(true)} />;
  }

  const competitorDisplay = (slug: string) =>
    COMPETITORS.find((c) => c.slug === slug)?.display ?? slug;
  const dimensionDisplay = (slug: string) =>
    CI_DIMENSIONS.find((d) => d.slug === slug)?.display ?? slug;

  return (
    <div className="min-h-screen bg-[#070709] text-zinc-100 antialiased selection:bg-zinc-800 selection:text-white">
      {/* ── Top Navigation Bar ──────────────────────────────────── */}
      <nav className="bg-[#0e0e12]/90 backdrop-blur-md border-b border-zinc-800/80 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-zinc-800 border border-zinc-700/80 rounded-xl flex items-center justify-center text-white font-bold text-sm shadow-inner">
              C
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm tracking-tight text-white">Croma CI</span>
                <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/50">
                  LangGraph
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs: Reports, RAG mode, Competitor, Sources */}
          <div className="flex items-center gap-1.5 bg-[#141419] border border-zinc-800/90 rounded-xl p-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === tab.id
                    ? "bg-white text-zinc-900 shadow-sm"
                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Sign out */}
          <button
            onClick={() => {
              clearToken();
              setAuthed(false);
            }}
            className="text-xs text-zinc-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-zinc-800/60"
          >
            Sign out
          </button>
        </div>
      </nav>

      {/* ── Main Content Area ───────────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Tab 1: Reports */}
        {activeTab === "reports" && (
          <section className="space-y-6 animate-fadeIn">
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold text-white tracking-tight">Competitor Intelligence Reports</h1>
              <p className="text-zinc-400 text-xs">
                Comprehensive multi-dimensional intelligence dossiers compiled across all retail competitor entities.
              </p>
            </div>
            <div className="bg-[#0f0f13] rounded-3xl border border-zinc-800 p-6 md:p-8 shadow-xl">
              <ReportView />
            </div>
          </section>
        )}

        {/* Tab 2: RAG mode (LangGraph Orchestrator & Dynamic Multi-Agent Workflow) */}
        {activeTab === "rag_mode" && (
          <section className="animate-fadeIn">
            <AgentWorkflow />
          </section>
        )}

        {/* Tab 3: Competitor (Competitor Landscape & 6x5 Intelligence Matrix) */}
        {activeTab === "competitor" && (
          <section className="animate-fadeIn">
            <CompetitorMatrix
              onCellClick={(competitor, dimension, data) =>
                setDrilldown({ competitor, dimension, data })
              }
            />
          </section>
        )}

        {/* Tab 4: Sources Audit Table */}
        {activeTab === "sources" && (
          <section className="space-y-6 animate-fadeIn">
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold text-white tracking-tight">Ingested Knowledge Base Audit</h1>
              <p className="text-zinc-400 text-xs">
                Verifiable audit trail of all indexed documents, financial filings, and crawl URLs.
              </p>
            </div>
            <div className="bg-[#0f0f13] rounded-3xl border border-zinc-800 p-6 md:p-8 shadow-xl">
              <SourcesTable />
            </div>
          </section>
        )}
      </main>

      {/* ── DrillDown Slide-over ───────────────────────────────── */}
      {drilldown && (
        <DrillDown
          competitor={drilldown.competitor}
          competitorDisplay={competitorDisplay(drilldown.competitor)}
          dimension={drilldown.dimension}
          dimensionDisplay={dimensionDisplay(drilldown.dimension)}
          data={drilldown.data}
          onClose={() => setDrilldown(null)}
        />
      )}
    </div>
  );
}
