"use client";

import React, { useState } from "react";
import {
  queryCI,
  type QueryResponse,
  COMPETITORS,
  CI_DIMENSIONS,
  DocumentPreview,
} from "@/lib/api";
import DocumentUploader from "@/components/DocumentUploader";

type AgentMode = "auto" | "research" | "rag" | "analysis" | "validation";
type SourceScope = "uploaded_only" | "croma_kb" | "uploaded_and_croma" | "all_sources";

const AGENT_MODES: { id: AgentMode; label: string; icon: string; desc: string; badge: string }[] = [
  {
    id: "auto",
    label: "Auto Mode",
    icon: "⚡",
    desc: "LangGraph orchestrator coordinates required agents dynamically with parallel execution.",
    badge: "Recommended",
  },
  {
    id: "research",
    label: "Research Agent",
    icon: "🔍",
    desc: "Live web search & crawling for competitor announcements, current pricing, and fresh news.",
    badge: "Live Web",
  },
  {
    id: "rag",
    label: "RAG Agent",
    icon: "🗄️",
    desc: "Hybrid retrieval (dense + BM25) across Croma KB and uploaded documents with page citations.",
    badge: "Internal + Docs",
  },
  {
    id: "analysis",
    label: "Analysis Agent",
    icon: "📈",
    desc: "Synthesizes multi-source comparisons, pricing tables, trends, and clearly notes missing data.",
    badge: "Synthesis",
  },
  {
    id: "validation",
    label: "Validation Agent",
    icon: "🛡️",
    desc: "Audits factual claims against available sources, detects conflicts, and calibrates confidence.",
    badge: "Fact Audit",
  },
];

const SOURCE_SCOPES: { id: SourceScope; label: string; icon: string; desc: string }[] = [
  { id: "all_sources", label: "All Available Sources", icon: "🌐", desc: "Uploaded docs, Croma KB, and live web research" },
  { id: "uploaded_and_croma", label: "Uploaded + Croma KB", icon: "🔀", desc: "User documents combined with existing retailer knowledge base" },
  { id: "uploaded_only", label: "Uploaded Documents Only", icon: "📄", desc: "Strictly answer from user-uploaded files without external filler" },
  { id: "croma_kb", label: "Croma Knowledge Base", icon: "🏢", desc: "Existing competitor intelligence and indexed market data" },
];

export default function AgentWorkflow() {
  const [query, setQuery] = useState("Compare competitors, their products, pricing, and recent changes.");
  const [selectedMode, setSelectedMode] = useState<AgentMode>("auto");
  const [sourceScope, setSourceScope] = useState<SourceScope>("all_sources");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [selectedCompetitor, setSelectedCompetitor] = useState<string>("");
  const [selectedDimension, setSelectedDimension] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [activeStep, setActiveStep] = useState<number>(0); // 0: idle, 1: orchestrator, 2: agents, 3: report
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<DocumentPreview | null>(null);

  const handleRunQuery = async (queryText?: string) => {
    const textToRun = queryText || query;
    if (!textToRun.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    // Step 1: Orchestrator planning
    setActiveStep(1);
    await new Promise((r) => setTimeout(r, 350));

    // Step 2: Agent execution
    setActiveStep(2);

    try {
      const response = await queryCI(
        textToRun,
        selectedCompetitor || undefined,
        selectedDimension || undefined,
        false, // bypass cache for immediate testing
        selectedMode,
        sourceScope,
        selectedDocIds
      );

      // Step 3: Final report
      setActiveStep(3);
      setResult(response);
    } catch (err: any) {
      console.error("Agent workflow error:", err);
      setError(err?.message || "Failed to execute agent workflow. Check backend status.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-8">
      {/* ── Top Header ─────────────────────────────────────────── */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-800/80 border border-zinc-700 text-xs text-zinc-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          LangGraph Dynamic Multi-Agent Orchestration · Groq LLM
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
          Competitive Intelligence Platform
        </h1>
        <p className="text-zinc-400 text-sm max-w-xl mx-auto">
          User-controlled agent modes, custom document ingestion, and hybrid vector RAG retrieval with citation auditing.
        </p>
      </div>

      {/* ── Control Bar: Agent Mode Selector ─────────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-400">
            1. Select Agent Execution Mode
          </label>
          <span className="text-[11px] text-zinc-500">
            Selected: <strong className="text-white capitalize">{selectedMode}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {AGENT_MODES.map((mode) => {
            const isSelected = selectedMode === mode.id;
            return (
              <button
                key={mode.id}
                onClick={() => setSelectedMode(mode.id)}
                type="button"
                className={`p-3 rounded-2xl border text-left transition-all relative flex flex-col justify-between ${
                  isSelected
                    ? "bg-[#181822] border-blue-500/80 shadow-lg shadow-blue-500/10 ring-1 ring-blue-500/50"
                    : "bg-[#0f0f14] border-zinc-800/80 hover:border-zinc-700 hover:bg-[#131319]"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-base">{mode.icon}</span>
                    <span className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded ${
                      isSelected ? "bg-blue-500/20 text-blue-300" : "bg-zinc-800 text-zinc-400"
                    }`}>
                      {mode.badge}
                    </span>
                  </div>
                  <h3 className={`text-xs font-bold ${isSelected ? "text-white" : "text-zinc-200"}`}>
                    {mode.label}
                  </h3>
                  <p className="text-[11px] text-zinc-400 mt-1 leading-snug line-clamp-2">
                    {mode.desc}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Control Bar: Source Scope Selector ───────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-400">
            2. Choose Knowledge & Source Scope
          </label>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {SOURCE_SCOPES.map((scope) => {
            const isSelected = sourceScope === scope.id;
            return (
              <button
                key={scope.id}
                onClick={() => setSourceScope(scope.id)}
                type="button"
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  isSelected
                    ? "bg-[#181822] border-emerald-500/80 shadow-md shadow-emerald-500/5 ring-1 ring-emerald-500/40 text-white"
                    : "bg-[#0f0f14] border-zinc-800/80 hover:border-zinc-700 hover:bg-[#131319] text-zinc-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm">{scope.icon}</span>
                  <span className="text-xs font-semibold">{scope.label}</span>
                </div>
                <p className="text-[10px] text-zinc-400 mt-1 leading-snug">
                  {scope.desc}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Document Upload Component ───────────────────────────── */}
      <div className="space-y-1.5">
        <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 px-1">
          3. Upload Custom Documents (PDF, Word, Excel, CSV, Text)
        </label>
        <DocumentUploader
          selectedDocIds={selectedDocIds}
          onSelectedDocsChange={setSelectedDocIds}
          onPreviewDoc={setPreviewDoc}
        />
      </div>

      {/* ── Visual Architecture Diagram & Query Runner ─────────── */}
      <div className="p-6 md:p-8 rounded-3xl bg-[#09090b] border border-zinc-800/80 shadow-2xl relative overflow-hidden">
        {/* Subtle decorative glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-32 bg-blue-500/10 blur-[90px] pointer-events-none rounded-full" />

        <div className="relative z-10 flex flex-col items-center">
          {/* ── Node 1: User Query ──────────────────────────────── */}
          <div className="w-full max-w-2xl text-center space-y-2">
            <div className="flex flex-col items-center justify-center gap-1.5">
              <svg className="w-6 h-6 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.8}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <h2 className="text-base md:text-lg font-semibold text-white">User query</h2>
              <p className="text-zinc-400 text-sm max-w-lg">
                &ldquo;Compare competitors, their products, pricing, and recent changes.&rdquo;
              </p>
            </div>

            {/* Input / Query Bar */}
            <div className="mt-4 relative flex items-center bg-[#111115] border border-zinc-700/80 rounded-2xl p-1.5 focus-within:border-zinc-500 transition-all shadow-lg">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Compare competitors, their products, pricing, and recent changes."
                className="w-full bg-transparent px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none"
                onKeyDown={(e) => e.key === "Enter" && handleRunQuery()}
              />
              <button
                onClick={() => handleRunQuery()}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-zinc-900 font-semibold text-xs hover:bg-zinc-200 disabled:opacity-50 transition-all shadow"
              >
                {loading ? (
                  <>
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Running...
                  </>
                ) : (
                  <>
                    Run {selectedMode === "auto" ? "Workflow" : AGENT_MODES.find(m => m.id === selectedMode)?.label}
                    <span>→</span>
                  </>
                )}
              </button>
            </div>

            <div className="flex items-center justify-center gap-3 pt-3 text-xs">
              <select
                value={selectedCompetitor}
                onChange={(e) => setSelectedCompetitor(e.target.value)}
                className="bg-zinc-900 border border-zinc-800 text-zinc-300 rounded-lg px-2.5 py-1 focus:outline-none"
              >
                <option value="">All Competitors</option>
                {COMPETITORS.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.display}
                  </option>
                ))}
              </select>
              <select
                value={selectedDimension}
                onChange={(e) => setSelectedDimension(e.target.value)}
                className="bg-zinc-900 border border-zinc-800 text-zinc-300 rounded-lg px-2.5 py-1 focus:outline-none"
              >
                <option value="">All Dimensions</option>
                {CI_DIMENSIONS.map((d) => (
                  <option key={d.slug} value={d.slug}>
                    {d.display}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* ── Downward Connector Arrow ────────────────────────── */}
          <div className="py-4 flex flex-col items-center">
            <svg
              className={`w-4 h-4 transition-all duration-300 ${
                activeStep >= 1 ? "text-emerald-400 animate-bounce" : "text-zinc-500"
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>

          {/* ── Node 2: Orchestrator — LangGraph ───────────────── */}
          <div
            className={`w-full max-w-3xl rounded-2xl border transition-all duration-300 ${
              activeStep >= 1
                ? "border-zinc-700 bg-gradient-to-b from-[#141418] to-[#0c0c0e] shadow-xl"
                : "border-zinc-800/90 bg-[#101014]"
            }`}
          >
            {/* Orchestrator Header */}
            <div className="p-5 text-center border-b border-zinc-800/70">
              <div className="flex items-center justify-center gap-2">
                <span className="font-bold text-white text-base md:text-lg">Orchestrator — LangGraph</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
                  Mode: {selectedMode.toUpperCase()}
                </span>
                {sourceScope === "uploaded_only" && (
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30">
                    Uploaded Docs Only
                  </span>
                )}
              </div>
              <p className="text-zinc-400 text-xs md:text-sm mt-1">
                Maintains state, selects tasks, delegates work, and controls completion.
              </p>
              {(result?.plan_rationale || result?.agent_traces?.plan_rationale) && (
                <div className="mt-3 mx-auto max-w-xl px-3.5 py-2.5 rounded-lg bg-blue-950/40 border border-blue-800/50 text-left">
                  <div className="text-[10px] uppercase font-mono tracking-wider text-blue-400 font-bold mb-0.5 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                    Orchestrator Decision Rationale
                  </div>
                  <p className="text-xs text-blue-200/90 leading-relaxed">
                    {result?.plan_rationale || result?.agent_traces?.plan_rationale}
                  </p>
                </div>
              )}
            </div>

            {/* 2x2 Agent Grid Matching Reference Architecture */}
            <div className="p-4 md:p-5 grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {/* Agent 1: Research Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  selectedMode === "research"
                    ? "border-blue-500 bg-blue-950/30 shadow-lg shadow-blue-500/10 ring-1 ring-blue-500/50"
                    : (result?.selected_agents?.includes("research_agent") || result?.agent_traces?.selected_agents?.includes("research_agent"))
                    ? "border-blue-500/80 bg-blue-950/25 ring-1 ring-blue-500/40"
                    : activeStep >= 2 && (selectedMode === "auto")
                    ? "border-blue-500/70 bg-blue-950/20"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="font-semibold text-sm md:text-base text-white">Research agent</h3>
                  {selectedMode === "research" && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-400 font-mono">PRIMARY</span>
                  )}
                  {((result?.selected_agents?.includes("research_agent") || result?.agent_traces?.selected_agents?.includes("research_agent")) && selectedMode === "auto") && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-mono border border-emerald-500/30">SELECTED</span>
                  )}
                </div>
                <p className="text-zinc-400 text-xs mt-1">Web search and crawling</p>
                {loading && (selectedMode === "research" || selectedMode === "auto") && (
                  <span className="text-[10px] text-blue-400 font-mono mt-2 animate-pulse">searching web...</span>
                )}
                {result?.agent_traces?.research_agent?.findings_count !== undefined && result.agent_traces.research_agent.findings_count > 0 && (
                  <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-2 py-0.5 rounded mt-2">
                    {result.agent_traces.research_agent.findings_count} live web hits
                  </span>
                )}
              </div>

              {/* Agent 2: RAG Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  selectedMode === "rag"
                    ? "border-purple-500 bg-purple-950/30 shadow-lg shadow-purple-500/10 ring-1 ring-purple-500/50"
                    : (result?.selected_agents?.includes("rag_agent") || result?.agent_traces?.selected_agents?.includes("rag_agent"))
                    ? "border-purple-500/80 bg-purple-950/25 ring-1 ring-purple-500/40"
                    : activeStep >= 2 && (selectedMode === "auto" || selectedMode === "analysis" || selectedMode === "validation")
                    ? "border-purple-500/70 bg-purple-950/20"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="font-semibold text-sm md:text-base text-white">RAG agent</h3>
                  {selectedMode === "rag" && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-400 font-mono">PRIMARY</span>
                  )}
                  {((result?.selected_agents?.includes("rag_agent") || result?.agent_traces?.selected_agents?.includes("rag_agent")) && selectedMode === "auto") && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-mono border border-emerald-500/30">SELECTED</span>
                  )}
                </div>
                <p className="text-zinc-400 text-xs mt-1">Hybrid retrieval and reranking</p>
                {loading && (selectedMode === "rag" || selectedMode === "auto") && (
                  <span className="text-[10px] text-purple-400 font-mono mt-2 animate-pulse">retrieving Chroma+BM25...</span>
                )}
                {result?.agent_traces?.rag_agent?.chunks_count !== undefined && (
                  <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-2 py-0.5 rounded mt-2">
                    {result.agent_traces.rag_agent.chunks_count} chunks
                    {result.agent_traces.rag_agent.uploaded_chunks_count ? ` (${result.agent_traces.rag_agent.uploaded_chunks_count} user docs)` : ""}
                  </span>
                )}
              </div>

              {/* Agent 3: Analysis Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  selectedMode === "analysis"
                    ? "border-amber-500 bg-amber-950/30 shadow-lg shadow-amber-500/10 ring-1 ring-amber-500/50"
                    : (result?.selected_agents?.includes("analysis_agent") || result?.agent_traces?.selected_agents?.includes("analysis_agent"))
                    ? "border-amber-500/80 bg-amber-950/25 ring-1 ring-amber-500/40"
                    : activeStep >= 2 && (selectedMode === "auto")
                    ? "border-amber-500/70 bg-amber-950/20"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                  </svg>
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="font-semibold text-sm md:text-base text-white">Analysis agent</h3>
                  {selectedMode === "analysis" && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-400 font-mono">PRIMARY</span>
                  )}
                  {((result?.selected_agents?.includes("analysis_agent") || result?.agent_traces?.selected_agents?.includes("analysis_agent")) && selectedMode === "auto") && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-mono border border-emerald-500/30">SELECTED</span>
                  )}
                </div>
                <p className="text-zinc-400 text-xs mt-1">Trends and comparisons</p>
                {loading && (selectedMode === "analysis" || selectedMode === "auto") && (
                  <span className="text-[10px] text-amber-400 font-mono mt-2 animate-pulse">synthesizing with Groq...</span>
                )}
                {result && (selectedMode === "analysis" || selectedMode === "auto") && (
                  <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-2 py-0.5 rounded mt-2">
                    Groq 120B Synthesized
                  </span>
                )}
              </div>

              {/* Agent 4: Validation Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  selectedMode === "validation"
                    ? "border-emerald-500 bg-emerald-950/30 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/50"
                    : (result?.selected_agents?.includes("validation_agent") || result?.agent_traces?.selected_agents?.includes("validation_agent"))
                    ? "border-emerald-500/80 bg-emerald-950/25 ring-1 ring-emerald-500/40"
                    : activeStep >= 2 && (selectedMode === "auto")
                    ? "border-emerald-500/70 bg-emerald-950/20"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="font-semibold text-sm md:text-base text-white">Validation agent</h3>
                  {selectedMode === "validation" && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-mono">PRIMARY</span>
                  )}
                  {((result?.selected_agents?.includes("validation_agent") || result?.agent_traces?.selected_agents?.includes("validation_agent")) && selectedMode === "auto") && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-mono border border-emerald-500/30">SELECTED</span>
                  )}
                </div>
                <p className="text-zinc-400 text-xs mt-1">Evidence and quality checks</p>
                {loading && (selectedMode === "validation" || selectedMode === "auto") && (
                  <span className="text-[10px] text-emerald-400 font-mono mt-2 animate-pulse">verifying citations...</span>
                )}
                {result && (
                  <span className="text-[10px] text-emerald-400 font-mono bg-emerald-950/40 border border-emerald-800/50 px-2 py-0.5 rounded mt-2">
                    Confidence {Math.round(result.confidence_score * 100)}%
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* ── Downward Connector Arrow ────────────────────────── */}
          <div className="py-4 flex flex-col items-center">
            <svg
              className={`w-4 h-4 transition-all duration-300 ${
                activeStep >= 3 ? "text-emerald-400 animate-bounce" : "text-zinc-500"
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>

          {/* ── Node 3: Final Report Header ────────────────────── */}
          <div className="w-full max-w-2xl text-center space-y-1">
            <div className="flex flex-col items-center justify-center gap-1.5">
              <svg className="w-6 h-6 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.8}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <h2 className="text-base md:text-lg font-semibold text-white">Final report</h2>
              <p className="text-zinc-400 text-sm max-w-md">
                Evidence-backed findings, citations, comparisons, and confidence indicators.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Error Display ───────────────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Live Generated Final Report Content ─────────────────── */}
      {result && (
        <div className="space-y-6 pt-2 animate-fadeIn">
          {/* Missing Information Notice if present */}
          {result.missing_information && result.missing_information.length > 0 && (
            <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-800/60 text-amber-200 text-xs space-y-1">
              <div className="flex items-center gap-2 font-semibold text-amber-300">
                <span>⚠️</span> Information Gaps Identified
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-zinc-300">
                {result.missing_information.map((m, idx) => (
                  <li key={idx}>{m}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Conflicting Evidence Notice if present */}
          {result.conflicts && result.conflicts.length > 0 && (
            <div className="p-4 rounded-2xl bg-rose-950/30 border border-rose-800/60 text-rose-200 text-xs space-y-1">
              <div className="flex items-center gap-2 font-semibold text-rose-300">
                <span>⚡</span> Conflicting Evidence Detected Across Sources
              </div>
              <div className="space-y-1 text-zinc-300">
                {result.conflicts.map((c, idx) => (
                  <p key={idx}>{c.description || JSON.stringify(c)}</p>
                ))}
              </div>
            </div>
          )}

          {/* Executive Summary Card */}
          <div className="p-6 md:p-8 rounded-3xl bg-[#0f0f13] border border-zinc-800 shadow-xl space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800/80 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-white">Executive Synthesis</h2>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-400">
                    {result.primary_agent || "Orchestrator"}
                  </span>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                    Scope: {result.source_scope?.replace(/_/g, " ")}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">Validated response for: &ldquo;{result.query}&rdquo;</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold text-xs flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Calibrated Confidence: {Math.round(result.confidence_score * 100)}%
                </div>
              </div>
            </div>

            <p className="text-sm md:text-base text-zinc-200 leading-relaxed whitespace-pre-line">
              {result.summary}
            </p>
          </div>

          {/* Competitors Detailed Breakdown if available */}
          {result.competitors && Object.keys(result.competitors).length > 0 && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 px-1">
                Competitor Comparison Breakdown
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(result.competitors).map(([compSlug, compData]) => (
                  <div key={compSlug} className="p-5 rounded-2xl bg-[#111115] border border-zinc-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-sm capitalize">
                        {compSlug.replace(/_/g, " ")}
                      </span>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono">
                        {Math.round(compData.confidence_score * 100)}% conf
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300 leading-relaxed">
                      {compData.summary}
                    </p>
                    {compData.key_metrics && compData.key_metrics.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {compData.key_metrics.slice(0, 3).map((m, idx) => (
                          <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-zinc-800/80 text-zinc-300 border border-zinc-700/50">
                            <strong>{m.metric}:</strong> {m.value}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key Metrics Comparison Table */}
          {result.key_metrics && result.key_metrics.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#0f0f13] border border-zinc-800 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>📊</span> Key Quantitative Metrics Extracted
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-900/60 text-zinc-400 border-b border-zinc-800">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">Metric</th>
                      <th className="py-2.5 px-4 font-semibold">Value</th>
                      <th className="py-2.5 px-4 font-semibold">Period / Scope</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60 text-zinc-200">
                    {result.key_metrics.map((m, idx) => (
                      <tr key={idx} className="hover:bg-zinc-900/40 transition">
                        <td className="py-2.5 px-4 font-medium text-white">{m.metric}</td>
                        <td className="py-2.5 px-4 font-semibold text-emerald-400">{m.value}</td>
                        <td className="py-2.5 px-4 text-zinc-400">{m.period || "Recent"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Evidence & Clickable Citations */}
          {result.citations && result.citations.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#0f0f13] border border-zinc-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>🔗</span> Verified Source Evidence & Citations
                </h3>
                <span className="text-[11px] text-zinc-500">Click a citation to inspect excerpt & provenance</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {result.citations.map((c, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      setPreviewDoc({
                        document_id: `cit_${idx}`,
                        filename: c.source,
                        file_type: "document",
                        file_size: 0,
                        page_count: 1,
                        sections: [],
                        preview_text: c.excerpt || "Full source passage cited directly from retrieved index.",
                      });
                    }}
                    className="p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800 hover:border-zinc-700 transition cursor-pointer space-y-1.5 hover:bg-zinc-900"
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-blue-400 truncate max-w-[240px]">
                        {c.source}
                      </span>
                      <span className="text-zinc-500">{c.date || "2024"}</span>
                    </div>
                    {c.excerpt && (
                      <p className="text-xs text-zinc-300 italic line-clamp-3">
                        &ldquo;{c.excerpt}&rdquo;
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Document Preview Modal / Drawer ─────────────────────── */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121217] border border-zinc-800 rounded-3xl max-w-2xl w-full p-6 space-y-4 shadow-2xl animate-scaleIn max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">📄</span>
                <div>
                  <h3 className="font-bold text-sm text-white">{previewDoc.filename}</h3>
                  <p className="text-[11px] text-zinc-400 font-mono">
                    {previewDoc.file_type.toUpperCase()} · {previewDoc.page_count} page(s)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="w-8 h-8 rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white flex items-center justify-center text-sm font-bold transition"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-3">
              {previewDoc.sections && previewDoc.sections.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pb-2 border-b border-zinc-800/60">
                  <span className="text-[10px] text-zinc-500 self-center">Sections:</span>
                  {previewDoc.sections.map((sec, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-zinc-800/80 text-zinc-300">
                      {sec}
                    </span>
                  ))}
                </div>
              )}
              <div className="p-4 rounded-xl bg-[#09090c] border border-zinc-800/80 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">
                {previewDoc.preview_text}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setPreviewDoc(null)}
                className="px-4 py-2 rounded-xl bg-zinc-800 text-zinc-200 hover:text-white text-xs font-semibold hover:bg-zinc-700 transition"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
