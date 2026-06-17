/**
 * frontend/src/components/SearchBar.tsx
 * ──────────────────────────────────────
 * Natural language search: calls /api/query and renders
 * the structured answer with inline citations.
 */

"use client";

import React, { useState, useRef } from "react";
import {
  freeFormQuery,
  type QueryResponse,
  COMPETITORS,
  CI_DIMENSIONS,
} from "@/lib/api";
import CitationBadge from "./CitationBadge";

const EXAMPLE_QUERIES = [
  "How does Vijay Sales compare to Reliance Digital on store expansion?",
  "What are Aditya Vision's revenue trends and profitability?",
  "Which competitor has the best customer ratings on Google?",
  "What are Reliance Digital's major strategic initiatives in 2024?",
  "Compare EMI and BNPL offerings across all competitors",
];

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [competitorFilter, setCompetitorFilter] = useState("");
  const [dimensionFilter, setDimensionFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await freeFormQuery(
        query.trim(),
        competitorFilter || undefined,
        dimensionFilter || undefined
      );
      setResult(resp);
    } catch (err: any) {
      setError(err.message || "Query failed");
    } finally {
      setLoading(false);
    }
  };

  const useExample = (q: string) => {
    setQuery(q);
    inputRef.current?.focus();
  };

  const score = result?.confidence_score ?? 0;

  return (
    <div className="space-y-5">
      {/* ── Input form ────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <textarea
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e as any);
              }
            }}
            rows={2}
            placeholder="Ask anything about competitors… (e.g. How does Vijay Sales compare on store expansion?)"
            className="w-full px-4 py-3 pr-14 border border-slate-300 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent resize-none shadow-sm"
          />
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="absolute right-3 bottom-3 p-2 rounded-lg bg-slate-900 text-white disabled:opacity-40 hover:bg-slate-700 transition-colors"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-3 flex-wrap">
          <select
            value={competitorFilter}
            onChange={(e) => setCompetitorFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg text-slate-600 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
          >
            <option value="">All competitors</option>
            {COMPETITORS.map((c) => (
              <option key={c.slug} value={c.slug}>{c.display}</option>
            ))}
          </select>
          <select
            value={dimensionFilter}
            onChange={(e) => setDimensionFilter(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg text-slate-600 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
          >
            <option value="">All dimensions</option>
            {CI_DIMENSIONS.map((d) => (
              <option key={d.slug} value={d.slug}>{d.display}</option>
            ))}
          </select>
        </div>
      </form>

      {/* ── Example queries ───────────────────────────────────── */}
      {!result && !loading && (
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-slate-400 self-center">Try:</span>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => useExample(q)}
              className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-slate-400 hover:text-slate-800 transition-colors bg-white"
            >
              {q.length > 55 ? q.slice(0, 52) + "…" : q}
            </button>
          ))}
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          ⚠ {error}
        </div>
      )}

      {/* ── Result ────────────────────────────────────────────── */}
      {result && (
        <div className="space-y-4 pt-2">
          {/* Confidence banner */}
          <div className={`flex items-center gap-2 text-xs font-medium px-3 py-2 rounded-lg border
            ${score >= 0.7
              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : score >= 0.4
              ? "bg-amber-50 text-amber-700 border-amber-200"
              : "bg-red-50 text-red-700 border-red-200"
            }`}
          >
            {score < 0.4 && <span>⚠</span>}
            <span>Confidence: {Math.round(score * 100)}%</span>
            <span className="text-slate-400 font-normal ml-2">
              • {result.sub_query_count} sub-queries processed
            </span>
          </div>

          {/* Summary */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Answer</h3>
            <p className="text-slate-800 leading-relaxed text-sm">{result.summary}</p>
          </div>

          {/* Key metrics */}
          {result.key_metrics.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Key Metrics</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {result.key_metrics.slice(0, 6).map((m, i) => (
                  <div key={i} className="p-3 rounded-lg border border-slate-200 bg-white">
                    <p className="text-xs text-slate-500">{m.metric}</p>
                    <p className="text-sm font-bold text-slate-900 mt-0.5">{m.value}</p>
                    {m.period && <p className="text-[10px] text-slate-400">{m.period}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Citations */}
          {result.citations.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">
                Sources ({result.citations.length})
              </h3>
              <div className="space-y-2">
                {result.citations.slice(0, 8).map((c, i) => (
                  <CitationBadge key={i} citation={c} index={i + 1} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
