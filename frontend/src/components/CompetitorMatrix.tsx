/**
 * frontend/src/components/CompetitorMatrix.tsx
 * ──────────────────────────────────────────────
 * Competitor Overview & CI Matrix Grid:
 *   - 5 Competitor profile highlight cards
 *   - 6x5 Matrix table (Dimensions × 5 Competitors)
 *   - Confidence badges, summaries, and click-to-drilldown
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

const COMPETITOR_HIGHLIGHTS = [
  {
    slug: "reliance_digital",
    display: "Reliance Digital",
    stores: "620+ stores",
    cities: "210+ cities",
    revenue: "₹22,500 Cr (FY24)",
    strength: "Largest nationwide electronics retailer with 3-hr O2O delivery & experience zones",
    badge: "Market Leader",
  },
  {
    slug: "vijay_sales",
    display: "Vijay Sales",
    stores: "130 showrooms",
    cities: "Maharashtra, Gujarat, Delhi NCR",
    revenue: "₹7,200 Cr (FY24)",
    strength: "Dominant West & North retail footprint with VS Rewards & high EMI adoption",
    badge: "West & North Powerhouse",
  },
  {
    slug: "aditya_vision",
    display: "Aditya Vision",
    stores: "145 showrooms",
    cities: "Bihar, Jharkhand, UP",
    revenue: "₹1,452 Cr (FY24)",
    strength: "Unrivaled Tier-3/4 regional leader with 70%+ owned stores & 7.1% EBITDA margin",
    badge: "Fastest Regional Growth",
  },
  {
    slug: "poojara",
    display: "Poojara Telecom",
    stores: "260 outlets",
    cities: "Gujarat, Rajasthan, Maharashtra",
    revenue: "₹1,120 Cr (FY24)",
    strength: "Dense mobile & accessory retail network across Western semi-urban markets",
    badge: "Mobile & Gadget Specialist",
  },
  {
    slug: "bajaj_electronics",
    display: "Bajaj Electronics (EMIL)",
    stores: "115 stores",
    cities: "Telangana, AP, Delhi NCR",
    revenue: "₹4,850 Cr (FY24)",
    strength: "South Indian dominance in Hyderabad & Andhra Pradesh with strong large-appliance mix",
    badge: "South Regional Leader",
  },
];

function confidenceColor(score: number): string {
  if (score >= 0.7) return "bg-emerald-950/40 text-emerald-300 border-emerald-800/60";
  if (score >= 0.4) return "bg-amber-950/40 text-amber-300 border-amber-800/60";
  return "bg-rose-950/40 text-rose-300 border-rose-800/60";
}

interface CellProps {
  data: DimensionResult | null;
  loading: boolean;
  onClick: () => void;
}

function MatrixCell({ data, loading, onClick }: CellProps) {
  if (loading) {
    return (
      <div className="h-24 flex items-center justify-center">
        <div className="w-4 h-4 border-2 border-zinc-600 border-t-zinc-200 rounded-full animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-24 flex items-center justify-center text-zinc-600 text-xs">
        No data
      </div>
    );
  }

  const score = data.confidence_score ?? 0;

  return (
    <button
      onClick={onClick}
      className="w-full h-full min-h-[5.5rem] p-2.5 text-left hover:bg-zinc-800/40 transition-colors group rounded-xl text-xs"
    >
      <div className="flex items-center justify-between mb-1.5">
        <span
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${confidenceColor(
            score
          )}`}
        >
          {Math.round(score * 100)}%
        </span>
        {data.key_metrics && data.key_metrics.length > 0 && (
          <span className="text-[10px] text-zinc-500 font-mono">
            {data.key_metrics.length} metric{data.key_metrics.length > 1 ? "s" : ""}
          </span>
        )}
      </div>

      <p className="text-[11px] text-zinc-400 leading-relaxed line-clamp-3 group-hover:text-zinc-200">
        {data.summary || "Insufficient verified public data available."}
      </p>
    </button>
  );
}

interface Props {
  onCellClick?: (competitor: string, dimension: string, data: DimensionResult) => void;
}

export default function CompetitorMatrix({ onCellClick }: Props) {
  const [matrix, setMatrix] = useState<Record<string, Record<string, DimensionResult | null>>>({});
  const [loadingDims, setLoadingDims] = useState<Set<string>>(new Set());

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
          console.warn("Matrix load error for", dim.slug, e?.message);
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
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* ── Top Header ─────────────────────────────────────────── */}
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold text-white tracking-tight">Competitor Landscape & Intelligence Matrix</h1>
        <p className="text-zinc-400 text-xs">
          Direct side-by-side comparison across all 5 major Indian electronics retail competitors.
        </p>
      </div>

      {/* ── 5 Competitor Highlight Cards ──────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {COMPETITOR_HIGHLIGHTS.map((comp) => (
          <div
            key={comp.slug}
            className="p-4 rounded-2xl bg-[#0f0f13] border border-zinc-800/80 hover:border-zinc-700 transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between gap-1 mb-2">
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700/50">
                  {comp.badge}
                </span>
              </div>
              <h3 className="font-bold text-sm text-white">{comp.display}</h3>
              <div className="mt-2 space-y-1 text-[11px]">
                <div className="text-emerald-400 font-semibold">{comp.stores}</div>
                <div className="text-zinc-400">{comp.cities}</div>
                <div className="text-zinc-300 font-mono text-[10px]">{comp.revenue}</div>
              </div>
            </div>
            <p className="text-[10px] text-zinc-500 mt-3 pt-2 border-t border-zinc-800/60 leading-tight">
              {comp.strength}
            </p>
          </div>
        ))}
      </div>

      {/* ── 6x5 Intelligence Matrix Grid ──────────────────────── */}
      <div className="bg-[#0f0f13] rounded-3xl border border-zinc-800 shadow-xl overflow-hidden">
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Multi-Dimensional Comparison Matrix</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Click any cell to drill into verified evidence, citations, and metrics.</p>
          </div>
          <span className="text-[11px] text-zinc-500 font-mono">6 Dimensions × 5 Competitors</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#141419] border-b border-zinc-800 text-zinc-400 text-[11px] uppercase tracking-wider">
                <th className="px-4 py-3.5 font-semibold w-44 border-r border-zinc-800/80">Dimension</th>
                {COMPETITORS.map((comp) => (
                  <th key={comp.slug} className="px-3.5 py-3.5 font-semibold text-center border-r border-zinc-800/80 last:border-r-0">
                    {comp.display}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {CI_DIMENSIONS.map((dim, idx) => {
                const isLoading = loadingDims.has(dim.slug);
                const rowData = matrix[dim.slug] ?? {};

                return (
                  <tr key={dim.slug} className={idx % 2 === 0 ? "bg-[#0f0f13]" : "bg-[#111116]/50"}>
                    <td className="px-4 py-3 border-r border-zinc-800/80 align-top">
                      <span className="font-semibold text-zinc-200 text-xs">{dim.display}</span>
                    </td>
                    {COMPETITORS.map((comp) => (
                      <td
                        key={comp.slug}
                        className="border-r border-zinc-800/80 last:border-r-0 align-top p-1"
                        style={{ minWidth: 165 }}
                      >
                        <MatrixCell
                          data={rowData[comp.slug] ?? null}
                          loading={isLoading}
                          onClick={() => {
                            if (rowData[comp.slug] && onCellClick) {
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
      </div>
    </div>
  );
}
