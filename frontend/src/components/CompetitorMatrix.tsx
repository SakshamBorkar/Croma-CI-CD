/**
 * frontend/src/components/CompetitorMatrix.tsx
 * ──────────────────────────────────────────────
 * The main dashboard grid:
 *   Rows    = CI dimensions
 *   Columns = 5 competitors
 *   Cell    = confidence badge + 1-line summary + click-to-drilldown
 */

"use client";

import React, { useState, useEffect } from "react";
import {
  CI_DIMENSIONS,
  COMPETITORS,
  compareCompetitors,
  type CompareResponse,
  type DimensionResult,
} from "@/lib/api";

// ── Confidence badge colour ───────────────────────────────────────
function confidenceClass(score: number): string {
  if (score >= 0.7) return "bg-emerald-100 text-emerald-800 border-emerald-300";
  if (score >= 0.4) return "bg-amber-100 text-amber-800 border-amber-300";
  return "bg-red-100 text-red-700 border-red-300";
}

function confidenceLabel(score: number): string {
  if (score >= 0.7) return "High";
  if (score >= 0.4) return "Medium";
  return "Low";
}

// ── Individual matrix cell ────────────────────────────────────────
interface CellProps {
  data: DimensionResult | null;
  loading: boolean;
  onClick: () => void;
}

function MatrixCell({ data, loading, onClick }: CellProps) {
  if (loading) {
    return (
      <div className="h-24 flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-24 flex items-center justify-center text-slate-400 text-xs">
        No data
      </div>
    );
  }

  const score = data.confidence_score ?? 0;
  const isLow = score < 0.4;

  return (
    <button
      onClick={onClick}
      className="w-full h-full min-h-[5.5rem] p-2 text-left hover:bg-slate-50 transition-colors group rounded"
    >
      {/* Confidence badge */}
      <span
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border mb-1.5 ${confidenceClass(score)}`}
      >
        {isLow && <span title="Low confidence">⚠ </span>}
        {confidenceLabel(score)} {Math.round(score * 100)}%
      </span>

      {/* Summary snippet */}
      <p className="text-[11px] text-slate-600 leading-relaxed line-clamp-3 group-hover:text-slate-800">
        {data.summary
          ? data.summary.slice(0, 110) + (data.summary.length > 110 ? "…" : "")
          : "Insufficient public data available."}
      </p>
    </button>
  );
}

// ── Main component ────────────────────────────────────────────────
interface Props {
  onCellClick: (competitor: string, dimension: string, data: DimensionResult) => void;
}

export default function CompetitorMatrix({ onCellClick }: Props) {
  // matrix[dimension][competitor] = DimensionResult | null
  const [matrix, setMatrix] = useState<Record<string, Record<string, DimensionResult | null>>>({});
  const [loadingDims, setLoadingDims] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Load dimensions one at a time (avoids hammering Ollama)
  useEffect(() => {
    let cancelled = false;
    async function loadAll() {
      for (const dim of CI_DIMENSIONS) {
        if (cancelled) break;
        setLoadingDims((prev) => new Set(prev).add(dim.slug));
        try {
          const resp: CompareResponse = await compareCompetitors(dim.slug);
          if (!cancelled) {
            setMatrix((prev) => ({
              ...prev,
              [dim.slug]: resp.competitors ?? {},
            }));
          }
        } catch (e: any) {
          console.warn("Matrix load error for", dim.slug, e.message);
          if (!cancelled) {
            setMatrix((prev) => ({ ...prev, [dim.slug]: {} }));
          }
        } finally {
          if (!cancelled) {
            setLoadingDims((prev) => {
              const next = new Set(prev);
              next.delete(dim.slug);
              return next;
            });
          }
        }
      }
    }
    loadAll();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
      <table className="w-full text-sm border-collapse">
        {/* Header row */}
        <thead>
          <tr className="bg-slate-900 text-white">
            <th className="px-4 py-3 text-left font-semibold text-xs uppercase tracking-wider w-40 border-r border-slate-700">
              Dimension
            </th>
            {COMPETITORS.map((comp) => (
              <th
                key={comp.slug}
                className="px-3 py-3 text-center font-semibold text-xs uppercase tracking-wider border-r border-slate-700 last:border-r-0"
              >
                {comp.display}
              </th>
            ))}
          </tr>
        </thead>

        {/* Data rows */}
        <tbody>
          {CI_DIMENSIONS.map((dim, dimIdx) => {
            const isLoading = loadingDims.has(dim.slug);
            const rowData = matrix[dim.slug] ?? {};

            return (
              <tr
                key={dim.slug}
                className={`border-b border-slate-100 ${dimIdx % 2 === 0 ? "bg-white" : "bg-slate-50/50"}`}
              >
                {/* Dimension label */}
                <td className="px-4 py-2 border-r border-slate-200">
                  <span className="font-medium text-slate-700 text-xs leading-tight">
                    {dim.display}
                  </span>
                </td>

                {/* One cell per competitor */}
                {COMPETITORS.map((comp) => (
                  <td
                    key={comp.slug}
                    className="border-r border-slate-100 last:border-r-0 align-top"
                    style={{ minWidth: 160 }}
                  >
                    <MatrixCell
                      data={rowData[comp.slug] ?? null}
                      loading={isLoading}
                      onClick={() => {
                        if (rowData[comp.slug]) {
                          onCellClick(comp.slug, dim.slug, rowData[comp.slug]!);
                        }
                      }}
                    />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
