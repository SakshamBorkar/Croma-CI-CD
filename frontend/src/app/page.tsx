/**
 * frontend/src/app/page.tsx
 * ──────────────────────────
 * Root page — auth gate + Multi-Agent Workflow centerpiece.
 *   Tab 1: Architecture Workflow → AgentWorkflow (LangGraph 4-Agent Orchestrator)
 *   Tab 2: Competitor Reports     → ReportView
 *   Tab 3: Sources Audit          → SourcesTable
 *   Tab 4: System Health          → Status & Provider details
 */

"use client";

import React, { useState, useEffect } from "react";
import { getToken, clearToken, getHealth, type HealthResponse } from "@/lib/api";
import LoginPage from "@/components/LoginPage";
import AgentWorkflow from "@/components/AgentWorkflow";
import ReportView from "@/components/ReportView";
import SourcesTable from "@/components/SourcesTable";

type Tab = "workflow" | "report" | "sources" | "health";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "workflow", label: "Agent Architecture", icon: "⚡" },
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

  if (loading) return <p className="text-zinc-500 text-sm">Checking system status…</p>;
  if (!data) return <p className="text-red-400 text-sm">Could not reach backend.</p>;

  const isHealthy = data.status === "healthy";

  return (
    <div className="space-y-5 max-w-4xl mx-auto">
      <div
        className={`flex items-center gap-3 px-5 py-4 rounded-2xl border ${
          isHealthy
            ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
            : "bg-amber-950/30 border-amber-800/60 text-amber-300"
        }`}
      >
        <span className={`w-3 h-3 rounded-full ${isHealthy ? "bg-emerald-400" : "bg-amber-400"}`} />
        <span className="font-semibold text-sm">
          System {isHealthy ? "Healthy & Operational" : "Degraded"}
        </span>
        <span className="text-xs text-zinc-400 ml-auto">{data.timestamp}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Component cards */}
        {Object.entries(data.components).map(([name, comp]) => (
          <div key={name} className="p-5 rounded-2xl border border-zinc-800 bg-[#121216]">
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-2 h-2 rounded-full ${comp.ok ? "bg-emerald-400" : "bg-red-400"}`} />
              <span className="font-semibold text-zinc-100 text-sm capitalize">{name}</span>
              <span
                className={`ml-auto text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                  comp.ok
                    ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                    : "bg-red-500/10 border border-red-500/30 text-red-400"
                }`}
              >
                {comp.ok ? "ONLINE" : "UNAVAILABLE"}
              </span>
            </div>
            {comp.models && comp.models.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {comp.models.map((m) => (
                  <span key={m} className="text-[11px] px-2 py-0.5 bg-zinc-800 text-zinc-300 rounded font-mono">
                    {m}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Runtime info */}
        <div className="p-5 rounded-2xl border border-zinc-800 bg-[#121216]">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-blue-400" />
            <span className="font-semibold text-zinc-100 text-sm">LLM Runtime</span>
            <span className="ml-auto text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400">
              GROQ CLOUD
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-2">
            Model: <code className="bg-zinc-800 text-zinc-200 px-1.5 py-0.5 rounded font-mono">openai/gpt-oss-120b</code> (High-speed Llama-3 synthesis)
          </p>
        </div>

        <div className="p-5 rounded-2xl border border-zinc-800 bg-[#121216]">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-purple-400" />
            <span className="font-semibold text-zinc-100 text-sm">Vector Embeddings</span>
            <span className="ml-auto text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400">
              LOCAL ONNX
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-2">
            Model: <code className="bg-zinc-800 text-zinc-200 px-1.5 py-0.5 rounded font-mono">all-MiniLM-L6-v2</code> (384-dim local vector search)
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Root page ─────────────────────────────────────────────────────
export default function HomePage() {
  const [authed, setAuthed] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("workflow");

  // Check for existing token
  useEffect(() => {
    if (getToken()) setAuthed(true);
  }, []);

  if (!authed) {
    return <LoginPage onLogin={() => setAuthed(true)} />;
  }

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

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1.5 bg-[#141419] border border-zinc-800/90 rounded-xl p-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
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
        {/* Tab: Agent Architecture Workflow (Primary) */}
        {activeTab === "workflow" && (
          <section className="animate-fadeIn">
            <AgentWorkflow />
          </section>
        )}

        {/* Tab: Competitor Reports */}
        {activeTab === "report" && (
          <section className="space-y-6 animate-fadeIn">
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold text-white tracking-tight">Competitor Intelligence Dossiers</h1>
              <p className="text-zinc-400 text-xs">
                Deep multi-dimensional analysis compiled across all retail competitor entities.
              </p>
            </div>
            <div className="bg-[#0f0f13] rounded-3xl border border-zinc-800 p-6 md:p-8 shadow-xl">
              <ReportView />
            </div>
          </section>
        )}

        {/* Tab: Sources Audit Table */}
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

        {/* Tab: System Health */}
        {activeTab === "health" && (
          <section className="space-y-6 animate-fadeIn">
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold text-white tracking-tight">System Infrastructure Health</h1>
              <p className="text-zinc-400 text-xs">
                Status of Groq API, PostgreSQL 16, Redis Cache, and local ONNX vector engines.
              </p>
            </div>
            <div className="bg-[#0f0f13] rounded-3xl border border-zinc-800 p-6 md:p-8 shadow-xl">
              <HealthTab />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
