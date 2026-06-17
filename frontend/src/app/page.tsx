/**
 * frontend/src/app/page.tsx
 * ──────────────────────────
 * Root page — auth gate + tab shell wiring:
 *   Tab 1: Matrix    → CompetitorMatrix
 *   Tab 2: Search    → SearchBar
 *   Tab 3: Report    → ReportView
 *   Tab 4: Sources   → SourcesTable
 *   Tab 5: Health    → system status
 */

"use client";

import React, { useState, useEffect } from "react";
import { getToken, clearToken, getHealth, type HealthResponse } from "@/lib/api";
import LoginPage from "@/components/LoginPage";
import CompetitorMatrix from "@/components/CompetitorMatrix";
import SearchBar from "@/components/SearchBar";
import ReportView from "@/components/ReportView";
import SourcesTable from "@/components/SourcesTable";
import DrillDown from "@/components/DrillDown";
import type { DimensionResult } from "@/lib/api";
import { COMPETITORS, CI_DIMENSIONS } from "@/lib/api";

type Tab = "matrix" | "search" | "report" | "sources" | "health";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "matrix", label: "CI Matrix", icon: "⊞" },
  { id: "search", label: "Search", icon: "⌕" },
  { id: "report", label: "Reports", icon: "≡" },
  { id: "sources", label: "Sources", icon: "⊕" },
  { id: "health", label: "Health", icon: "♡" },
];

// ── Health tab ────────────────────────────────────────────────────
function HealthTab() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHealth().then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-slate-400 text-sm">Checking system status…</p>;
  if (!data) return <p className="text-red-500 text-sm">Could not reach backend.</p>;

  const isHealthy = data.status === "healthy";

  return (
    <div className="space-y-5">
      <div className={`flex items-center gap-3 px-5 py-4 rounded-xl border ${
        isHealthy ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"
      }`}>
        <span className={`w-3 h-3 rounded-full ${isHealthy ? "bg-emerald-500" : "bg-amber-400"}`} />
        <span className={`font-semibold text-sm ${isHealthy ? "text-emerald-700" : "text-amber-700"}`}>
          System {isHealthy ? "Healthy" : "Degraded"}
        </span>
        <span className="text-xs text-slate-400 ml-auto">{data.timestamp}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(data.components).map(([name, comp]) => (
          <div key={name} className="p-4 rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-2 h-2 rounded-full ${comp.ok ? "bg-emerald-500" : "bg-red-400"}`} />
              <span className="font-semibold text-slate-700 text-sm capitalize">{name}</span>
              <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full ${
                comp.ok ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
              }`}>
                {comp.ok ? "OK" : "DOWN"}
              </span>
            </div>
            {comp.models && comp.models.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {comp.models.map((m) => (
                  <span key={m} className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded font-mono">
                    {m}
                  </span>
                ))}
              </div>
            )}
            {name === "ollama" && !comp.ok && (
              <p className="text-xs text-red-500 mt-2">
                Run: <code className="bg-red-50 px-1 rounded">ollama serve</code> then{" "}
                <code className="bg-red-50 px-1 rounded">ollama pull mistral</code>
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Quick setup guide */}
      <div className="p-5 rounded-xl border border-slate-200 bg-slate-50">
        <h3 className="font-semibold text-slate-700 text-sm mb-3">Quick Setup (Ollama)</h3>
        <div className="space-y-2">
          {[
            "ollama pull mistral              # LLM model",
            "ollama pull nomic-embed-text     # Embedding model",
            "ollama serve                     # Start server (port 11434)",
          ].map((cmd) => (
            <code key={cmd} className="block text-xs bg-slate-900 text-slate-100 px-4 py-2 rounded-lg font-mono">
              {cmd}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Root page ─────────────────────────────────────────────────────
export default function HomePage() {
  const [authed, setAuthed] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("matrix");

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
    <div className="min-h-screen bg-slate-100">
      {/* ── Top nav ─────────────────────────────────────────────── */}
      <nav className="bg-slate-900 text-white shadow-xl sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-6 flex items-center h-14 gap-6">
          {/* Logo */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="w-7 h-7 bg-white/10 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <span className="font-bold text-sm">Croma CI</span>
            <span className="text-slate-500 text-xs hidden md:inline">· Powered by Ollama</span>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 flex-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === tab.id
                    ? "bg-white text-slate-900"
                    : "text-slate-400 hover:text-white hover:bg-white/10"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Logout */}
          <button
            onClick={() => { clearToken(); setAuthed(false); }}
            className="text-xs text-slate-400 hover:text-white transition-colors flex-shrink-0"
          >
            Sign out
          </button>
        </div>
      </nav>

      {/* ── Page body ───────────────────────────────────────────── */}
      <main className="max-w-[1400px] mx-auto px-6 py-8">

        {/* Tab: CI Matrix */}
        {activeTab === "matrix" && (
          <section>
            <div className="mb-5">
              <h1 className="text-xl font-bold text-slate-900">Competitive Intelligence Matrix</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Click any cell to drill into full context, citations, and metrics.
              </p>
            </div>
            <CompetitorMatrix
              onCellClick={(competitor, dimension, data) =>
                setDrilldown({ competitor, dimension, data })
              }
            />
          </section>
        )}

        {/* Tab: Search */}
        {activeTab === "search" && (
          <section>
            <div className="mb-5">
              <h1 className="text-xl font-bold text-slate-900">Intelligence Search</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Ask anything in natural language — the RAG pipeline retrieves and synthesises from all sources.
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <SearchBar />
            </div>
          </section>
        )}

        {/* Tab: Report */}
        {activeTab === "report" && (
          <section>
            <div className="mb-5">
              <h1 className="text-xl font-bold text-slate-900">Competitor Reports</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Full AI-generated report across all CI dimensions for each competitor.
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <ReportView />
            </div>
          </section>
        )}

        {/* Tab: Sources */}
        {activeTab === "sources" && (
          <section>
            <div className="mb-5">
              <h1 className="text-xl font-bold text-slate-900">Ingested Sources</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Full audit trail of all documents ingested into the knowledge base.
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <SourcesTable />
            </div>
          </section>
        )}

        {/* Tab: Health */}
        {activeTab === "health" && (
          <section>
            <div className="mb-5">
              <h1 className="text-xl font-bold text-slate-900">System Health</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Ollama model availability, database, Redis cache status.
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <HealthTab />
            </div>
          </section>
        )}
      </main>

      {/* ── Drilldown slide-over ───────────────────────────────── */}
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
