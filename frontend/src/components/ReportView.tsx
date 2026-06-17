/**
 * frontend/src/components/ReportView.tsx
 * ────────────────────────────────────────
 * Full competitor report:
 *   - Dimension accordion cards
 *   - Export to PDF button
 *   - Overall confidence meter
 */

"use client";

import React, { useState, useEffect } from "react";
import {
  getCompetitorReport,
  exportReportPdf,
  type CompetitorReport,
  type DimensionResult,
  COMPETITORS,
  CI_DIMENSIONS,
} from "@/lib/api";
import CitationBadge from "./CitationBadge";

// ── Confidence ring ───────────────────────────────────────────────
function ConfidenceRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 70 ? "#10b981" : pct >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative inline-flex items-center justify-center w-16 h-16">
      <svg className="w-16 h-16 -rotate-90" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={r} fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle
          cx="36" cy="36" r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-sm font-bold text-slate-700">{pct}%</span>
    </div>
  );
}

// ── Dimension card ────────────────────────────────────────────────
function DimensionCard({ dimSlug, dimDisplay, data }: {
  dimSlug: string;
  dimDisplay: string;
  data: DimensionResult | null;
}) {
  const [open, setOpen] = useState(false);
  const score = data?.confidence_score ?? 0;
  const isEmpty = !data || score === 0;

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      {/* Accordion header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-4 px-5 py-4 bg-white hover:bg-slate-50 transition-colors text-left"
      >
        <ConfidenceRing score={score} />
        <div className="flex-1">
          <h3 className="font-semibold text-slate-800 text-sm">{dimDisplay}</h3>
          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
            {data?.summary?.slice(0, 90) ?? "No data available"}
            {(data?.summary?.length ?? 0) > 90 ? "…" : ""}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {!isEmpty && (
            <span className="text-[11px] text-slate-400">
              {data?.key_metrics?.length ?? 0} metrics · {data?.citations?.length ?? 0} sources
            </span>
          )}
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Accordion body */}
      {open && (
        <div className="border-t border-slate-100 px-5 py-5 bg-slate-50 space-y-5">
          {/* Summary */}
          <p className="text-sm text-slate-700 leading-relaxed">
            {data?.summary || "Insufficient public data available for this dimension."}
          </p>

          {/* Key metrics */}
          {data?.key_metrics && data.key_metrics.length > 0 && (
            <div>
              <h4 className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-2">
                Key Metrics
              </h4>
              <div className="overflow-hidden rounded-lg border border-slate-200">
                <table className="w-full text-xs">
                  <thead className="bg-white">
                    <tr>
                      <th className="px-3 py-2 text-left text-slate-500 font-semibold">Metric</th>
                      <th className="px-3 py-2 text-left text-slate-500 font-semibold">Value</th>
                      <th className="px-3 py-2 text-left text-slate-500 font-semibold">Period</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.key_metrics.map((m, i) => (
                      <tr key={i} className="border-t border-slate-100">
                        <td className="px-3 py-2 text-slate-600">{m.metric}</td>
                        <td className="px-3 py-2 font-semibold text-slate-800">{m.value}</td>
                        <td className="px-3 py-2 text-slate-400">{m.period}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Citations */}
          {data?.citations && data.citations.length > 0 && (
            <div>
              <h4 className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-2">
                Sources
              </h4>
              <div className="space-y-2">
                {data.citations.map((cit, i) => (
                  <CitationBadge key={i} citation={cit} index={i + 1} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main ReportView ───────────────────────────────────────────────
export default function ReportView() {
  const [selectedCompetitor, setSelectedCompetitor] = useState(COMPETITORS[0].slug);
  const [report, setReport] = useState<CompetitorReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = async (slug: string) => {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const r = await getCompetitorReport(slug);
      setReport(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport(selectedCompetitor);
  }, [selectedCompetitor]);

  const handleExport = async () => {
    if (!report) return;
    setExporting(true);
    try {
      const blob = await exportReportPdf(report.competitor);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `croma_ci_${report.competitor}_${report.generated_at}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert("Export failed: " + e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Competitor selector ──────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
        {COMPETITORS.map((c) => (
          <button
            key={c.slug}
            onClick={() => setSelectedCompetitor(c.slug)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all border ${
              selectedCompetitor === c.slug
                ? "bg-slate-900 text-white border-slate-900"
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"
            }`}
          >
            {c.display}
          </button>
        ))}
      </div>

      {/* ── Loading ──────────────────────────────────────────── */}
      {loading && (
        <div className="py-20 flex flex-col items-center gap-3 text-slate-500">
          <div className="w-8 h-8 border-2 border-slate-300 border-t-slate-700 rounded-full animate-spin" />
          <p className="text-sm">Generating report with Ollama…</p>
          <p className="text-xs text-slate-400">This may take 30–60s the first time</p>
        </div>
      )}

      {/* ── Error ────────────────────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          ⚠ {error}
        </div>
      )}

      {/* ── Report ───────────────────────────────────────────── */}
      {report && !loading && (
        <div className="space-y-4">
          {/* Report header */}
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-xl font-bold text-slate-900">
                {report.competitor_display}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Generated: {report.generated_at} · Overall confidence:{" "}
                <strong className="text-slate-600">{Math.round(report.overall_confidence * 100)}%</strong>
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => fetchReport(selectedCompetitor)}
                className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors"
              >
                ↺ Refresh
              </button>
              <button
                onClick={handleExport}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-900 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50 transition-colors"
              >
                {exporting ? (
                  <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                )}
                Export PDF
              </button>
            </div>
          </div>

          {/* Dimension cards */}
          <div className="space-y-3">
            {CI_DIMENSIONS.map((dim) => (
              <DimensionCard
                key={dim.slug}
                dimSlug={dim.slug}
                dimDisplay={dim.display}
                data={(report.dimensions?.[dim.slug] as DimensionResult) ?? null}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
