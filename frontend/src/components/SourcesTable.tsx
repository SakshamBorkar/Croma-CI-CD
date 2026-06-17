/**
 * frontend/src/components/SourcesTable.tsx
 * ──────────────────────────────────────────
 * Shows all ingested documents with:
 *   - Competitor + type filters
 *   - Chunk count, status badge, CI dimensions
 *   - Click source URL to open
 */

"use client";

import React, { useState, useEffect, useCallback } from "react";
import { listSources, type SourceRecord, COMPETITORS } from "@/lib/api";

const SOURCE_TYPES = ["website", "news", "annual_report", "review"];

const STATUS_COLOURS: Record<string, string> = {
  ok: "bg-emerald-100 text-emerald-700",
  error: "bg-red-100 text-red-700",
  skipped: "bg-slate-100 text-slate-500",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${STATUS_COLOURS[status] ?? "bg-slate-100 text-slate-500"}`}>
      {status}
    </span>
  );
}

function DimPills({ dims }: { dims: string[] }) {
  if (!dims || dims.length === 0) return <span className="text-slate-300">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {dims.slice(0, 3).map((d) => (
        <span key={d} className="px-1.5 py-0.5 rounded text-[9px] bg-slate-100 text-slate-600 font-medium">
          {d.replace("_", " ")}
        </span>
      ))}
      {dims.length > 3 && (
        <span className="text-[9px] text-slate-400">+{dims.length - 3}</span>
      )}
    </div>
  );
}

export default function SourcesTable() {
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [competitorFilter, setCompetitorFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 30;

  const fetchSources = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listSources(
        competitorFilter || undefined,
        typeFilter || undefined,
        PAGE_SIZE
      );
      setSources(resp.sources);
      setTotal(resp.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [competitorFilter, typeFilter, page]);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  return (
    <div className="space-y-4">
      {/* ── Filters ────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={competitorFilter}
          onChange={(e) => { setCompetitorFilter(e.target.value); setPage(0); }}
          className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white text-slate-600 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">All competitors</option>
          {COMPETITORS.map((c) => (
            <option key={c.slug} value={c.slug}>{c.display}</option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }}
          className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white text-slate-600 focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          <option value="">All source types</option>
          {SOURCE_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <button
          onClick={fetchSources}
          className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white text-slate-600 hover:bg-slate-50 transition-colors"
        >
          ↺ Refresh
        </button>
        <span className="ml-auto text-xs text-slate-400">{total} sources</span>
      </div>

      {/* ── Error ─────────────────────────────────────────────── */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          ⚠ {error}
        </div>
      )}

      {/* ── Table ─────────────────────────────────────────────── */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-slate-900 text-white">
              {["Competitor", "Type", "Source URL", "Published", "Ingested", "Chunks", "Dimensions", "Status"].map((h) => (
                <th key={h} className="px-3 py-2.5 text-left font-semibold uppercase tracking-wider text-[10px] border-r border-slate-700 last:border-r-0">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="text-center py-12 text-slate-400">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
                    Loading…
                  </div>
                </td>
              </tr>
            ) : sources.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-12 text-slate-400">
                  No sources found. Run the Airflow DAG to start ingestion.
                </td>
              </tr>
            ) : (
              sources.map((src, i) => (
                <tr
                  key={i}
                  className={`border-b border-slate-100 ${i % 2 === 0 ? "bg-white" : "bg-slate-50/40"}`}
                >
                  <td className="px-3 py-2 font-medium text-slate-700">
                    {src.competitor.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </td>
                  <td className="px-3 py-2">
                    <span className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-600 text-[10px] font-medium">
                      {src.source_type}
                    </span>
                  </td>
                  <td className="px-3 py-2 max-w-[200px]">
                    <a
                      href={src.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline truncate block max-w-[190px]"
                      title={src.source_url}
                    >
                      {src.source_url.replace(/^https?:\/\/(www\.)?/, "").slice(0, 45)}
                      {src.source_url.length > 55 ? "…" : ""}
                    </a>
                  </td>
                  <td className="px-3 py-2 text-slate-500">{src.publication_date || "—"}</td>
                  <td className="px-3 py-2 text-slate-500">{src.ingestion_date}</td>
                  <td className="px-3 py-2 text-center font-semibold text-slate-700">{src.chunk_count}</td>
                  <td className="px-3 py-2">
                    <DimPills dims={src.ci_dimensions} />
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge status={src.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
