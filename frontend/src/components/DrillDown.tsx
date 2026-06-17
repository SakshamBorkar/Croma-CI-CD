/**
 * frontend/src/components/DrillDown.tsx
 * ──────────────────────────────────────
 * Slide-over panel: full drilldown for one competitor × dimension.
 * Shows summary, key metrics table, and expandable citation list.
 * Each citation has source URL + date + excerpt.
 */

"use client";

import React, { useEffect, useRef } from "react";
import type { DimensionResult, Citation, KeyMetric } from "@/lib/api";
import CitationBadge from "./CitationBadge";

interface Props {
  competitor: string;
  competitorDisplay: string;
  dimension: string;
  dimensionDisplay: string;
  data: DimensionResult;
  onClose: () => void;
}

export default function DrillDown({
  competitor,
  competitorDisplay,
  dimension,
  dimensionDisplay,
  data,
  onClose,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Close on backdrop click
  const handleBackdrop = (e: React.MouseEvent) => {
    if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
      onClose();
    }
  };

  const score = data.confidence_score ?? 0;
  const isLow = score < 0.4;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm"
      onClick={handleBackdrop}
    >
      <div
        ref={panelRef}
        className="relative h-full w-full max-w-2xl bg-white shadow-2xl flex flex-col overflow-hidden"
        style={{ animation: "slideIn 0.22s ease-out" }}
      >
        {/* ── Header ─────────────────────────────────────────── */}
        <div className="flex items-start justify-between p-6 border-b border-slate-200 bg-slate-900 text-white">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">
              {dimensionDisplay}
            </p>
            <h2 className="text-xl font-bold">{competitorDisplay}</h2>
          </div>
          <button
            onClick={onClose}
            className="ml-4 mt-1 p-1.5 rounded-full hover:bg-slate-700 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* ── Scrollable body ─────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Confidence indicator */}
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border
            ${isLow
              ? "bg-red-50 text-red-700 border-red-200"
              : score < 0.7
              ? "bg-amber-50 text-amber-700 border-amber-200"
              : "bg-emerald-50 text-emerald-700 border-emerald-200"
            }`}
          >
            {isLow && <span>⚠</span>}
            <span>Confidence: {Math.round(score * 100)}%</span>
            {isLow && (
              <span className="ml-2 font-normal text-xs">
                Limited public data available — treat with caution.
              </span>
            )}
          </div>

          {/* Summary */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">
              Summary
            </h3>
            <p className="text-slate-700 leading-relaxed">
              {data.summary || "Insufficient public data available for this dimension."}
            </p>
          </section>

          {/* Key metrics */}
          {data.key_metrics && data.key_metrics.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">
                Key Metrics
              </h3>
              <div className="overflow-hidden rounded-lg border border-slate-200">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-semibold text-slate-600 text-xs">Metric</th>
                      <th className="px-4 py-2 text-left font-semibold text-slate-600 text-xs">Value</th>
                      <th className="px-4 py-2 text-left font-semibold text-slate-600 text-xs">Period</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.key_metrics.map((m: KeyMetric, i: number) => (
                      <tr
                        key={i}
                        className={`border-t border-slate-100 ${i % 2 === 0 ? "bg-white" : "bg-slate-50/60"}`}
                      >
                        <td className="px-4 py-2 text-slate-700 font-medium">{m.metric}</td>
                        <td className="px-4 py-2 text-slate-900 font-semibold">{m.value}</td>
                        <td className="px-4 py-2 text-slate-500 text-xs">{m.period}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Citations */}
          {data.citations && data.citations.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">
                Source Citations ({data.citations.length})
              </h3>
              <div className="space-y-2">
                {data.citations.map((cit: Citation, i: number) => (
                  <CitationBadge key={i} citation={cit} index={i + 1} />
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0.6; }
          to   { transform: translateX(0);    opacity: 1; }
        }
      `}</style>
    </div>
  );
}
