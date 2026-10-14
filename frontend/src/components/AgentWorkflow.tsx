"use client";

import React, { useState } from "react";
import { queryCI, type QueryResponse, COMPETITORS, CI_DIMENSIONS } from "@/lib/api";
import CitationBadge from "@/components/CitationBadge";

const SUGGESTED_QUERIES = [
  "Compare competitors, their products, pricing, and recent changes.",
  "How does Vijay Sales compare to Reliance Digital on store expansion?",
  "What are the pricing discounts and offers across Indian electronics retailers?",
  "Compare financial performance and revenue growth of all competitors.",
];

export default function AgentWorkflow() {
  const [query, setQuery] = useState(SUGGESTED_QUERIES[0]);
  const [selectedCompetitor, setSelectedCompetitor] = useState<string>("");
  const [selectedDimension, setSelectedDimension] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [activeStep, setActiveStep] = useState<number>(0); // 0: idle, 1: orchestrator, 2: parallel agents, 3: validation, 4: report
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunQuery = async (queryText?: string) => {
    const textToRun = queryText || query;
    if (!textToRun.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    // Step 1: Orchestrator planning
    setActiveStep(1);
    await new Promise((r) => setTimeout(r, 400));

    // Step 2: Research & RAG agents run
    setActiveStep(2);

    try {
      const response = await queryCI(
        textToRun,
        selectedCompetitor || undefined,
        selectedDimension || undefined,
        false
      );

      // Step 3: Analysis & Validation
      setActiveStep(3);
      await new Promise((r) => setTimeout(r, 400));

      // Step 4: Final report assembled
      setActiveStep(4);
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
          LangGraph 4-Agent Orchestration · Powered by Groq
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
          Competitive Intelligence Workflow
        </h1>
        <p className="text-zinc-400 text-sm max-w-xl mx-auto">
          Multi-agent architecture coordinating live web research, vector RAG retrieval, synthesis, and citation auditing.
        </p>
      </div>

      {/* ── Visual Architecture Diagram & Runner ──────────────── */}
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
                    Run Pipeline
                    <span>→</span>
                  </>
                )}
              </button>
            </div>

            {/* Quick Suggestions & Filters */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
              <span className="text-[11px] text-zinc-500">Quick queries:</span>
              {SUGGESTED_QUERIES.map((sq, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setQuery(sq);
                    handleRunQuery(sq);
                  }}
                  className="text-[11px] px-2.5 py-1 rounded-lg bg-zinc-900/90 text-zinc-400 hover:text-white border border-zinc-800 hover:border-zinc-700 transition"
                >
                  {sq.slice(0, 36)}...
                </button>
              ))}
            </div>

            <div className="flex items-center justify-center gap-3 pt-1 text-xs">
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
                {activeStep === 1 && (
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    Routing...
                  </span>
                )}
                {activeStep > 1 && (
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    State Compiled
                  </span>
                )}
              </div>
              <p className="text-zinc-400 text-xs md:text-sm mt-1">
                Maintains state, selects tasks, delegates work, and controls completion.
              </p>
            </div>

            {/* 2x2 Agent Grid Matching Diagram */}
            <div className="p-4 md:p-5 grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {/* Agent 1: Research Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  activeStep === 2
                    ? "border-blue-500/70 bg-blue-950/20 shadow-lg shadow-blue-500/5 ring-1 ring-blue-500/30"
                    : activeStep > 2
                    ? "border-zinc-800 bg-[#15151b]"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.8}
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-sm md:text-base text-white">Research agent</h3>
                <p className="text-zinc-400 text-xs mt-1">Web search and crawling</p>
                {activeStep === 2 && (
                  <span className="text-[10px] text-blue-400 font-mono mt-2 animate-pulse">searching web...</span>
                )}
                {result?.agent_traces?.research_agent?.findings_count !== undefined && (
                  <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-2 py-0.5 rounded mt-2">
                    {result.agent_traces.research_agent.findings_count} live web hits
                  </span>
                )}
              </div>

              {/* Agent 2: RAG Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  activeStep === 2
                    ? "border-purple-500/70 bg-purple-950/20 shadow-lg shadow-purple-500/5 ring-1 ring-purple-500/30"
                    : activeStep > 2
                    ? "border-zinc-800 bg-[#15151b]"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.8}
                      d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-sm md:text-base text-white">RAG agent</h3>
                <p className="text-zinc-400 text-xs mt-1">Hybrid retrieval and reranking</p>
                {activeStep === 2 && (
                  <span className="text-[10px] text-purple-400 font-mono mt-2 animate-pulse">retrieving Chroma+BM25...</span>
                )}
                {result?.agent_traces?.rag_agent?.chunks_count !== undefined && (
                  <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-2 py-0.5 rounded mt-2">
                    {result.agent_traces.rag_agent.chunks_count} vector chunks
                  </span>
                )}
              </div>

              {/* Agent 3: Analysis Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  activeStep === 3
                    ? "border-amber-500/70 bg-amber-950/20 shadow-lg shadow-amber-500/5 ring-1 ring-amber-500/30"
                    : activeStep > 3
                    ? "border-zinc-800 bg-[#15151b]"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.8}
                      d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-sm md:text-base text-white">Analysis agent</h3>
                <p className="text-zinc-400 text-xs mt-1">Trends and comparisons</p>
                {activeStep === 3 && (
                  <span className="text-[10px] text-amber-400 font-mono mt-2 animate-pulse">synthesizing with Groq...</span>
                )}
                {result && (
                  <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800 px-2 py-0.5 rounded mt-2">
                    Groq 120B Synthesized
                  </span>
                )}
              </div>

              {/* Agent 4: Validation Agent */}
              <div
                className={`p-6 rounded-xl border flex flex-col items-center text-center transition-all ${
                  activeStep === 3
                    ? "border-emerald-500/70 bg-emerald-950/20 shadow-lg shadow-emerald-500/5 ring-1 ring-emerald-500/30"
                    : activeStep > 3
                    ? "border-zinc-800 bg-[#15151b]"
                    : "border-zinc-800/80 bg-[#131317] hover:border-zinc-700"
                }`}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-300 mb-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.8}
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-sm md:text-base text-white">Validation agent</h3>
                <p className="text-zinc-400 text-xs mt-1">Evidence and quality checks</p>
                {activeStep === 3 && (
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
                activeStep >= 4 ? "text-emerald-400 animate-bounce" : "text-zinc-500"
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
            {/* Downward indicator */}
            <div className="py-2 flex justify-center text-zinc-500">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
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
          {/* Executive Summary Card */}
          <div className="p-6 md:p-8 rounded-3xl bg-[#0f0f13] border border-zinc-800 shadow-xl space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800/80 pb-4">
              <div>
                <h2 className="text-lg font-bold text-white">Executive Synthesis</h2>
                <p className="text-xs text-zinc-400">Validated response for: &ldquo;{result.query}&rdquo;</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold text-xs flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Calibrated Confidence: {Math.round(result.confidence_score * 100)}%
                </div>
              </div>
            </div>

            <p className="text-sm md:text-base text-zinc-200 leading-relaxed">
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

          {/* Evidence & Citations */}
          {result.citations && result.citations.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#0f0f13] border border-zinc-800 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>🔗</span> Verified Source Evidence & Citations
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {result.citations.map((c, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-blue-400 truncate max-w-[240px]">
                        {c.source}
                      </span>
                      <span className="text-zinc-500">{c.date || "2024"}</span>
                    </div>
                    {c.excerpt && (
                      <p className="text-xs text-zinc-400 italic">
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
    </div>
  );
}
