/**
 * frontend/src/components/CitationBadge.tsx
 * ───────────────────────────────────────────
 * Renders a single citation with:
 *   - Source domain / name
 *   - Publication date
 *   - Short excerpt (≤15 words from spec)
 *   - Click → opens source URL
 */

"use client";

import React, { useState } from "react";
import type { Citation } from "@/lib/api";

interface Props {
  citation: Citation;
  index: number;
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url.slice(0, 40);
  }
}

function isValidUrl(str: string): boolean {
  try {
    new URL(str);
    return true;
  } catch {
    return false;
  }
}

export default function CitationBadge({ citation, index }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasUrl = isValidUrl(citation.source);
  const domain = hasUrl ? extractDomain(citation.source) : citation.source;

  return (
    <div className="group flex gap-3 items-start p-3 rounded-lg border border-slate-200 bg-slate-50 hover:bg-white hover:border-slate-300 transition-all">
      {/* Index number */}
      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-700 text-white text-[10px] font-bold flex items-center justify-center mt-0.5">
        {index}
      </span>

      <div className="flex-1 min-w-0">
        {/* Source + date row */}
        <div className="flex items-center gap-2 flex-wrap">
          {hasUrl ? (
            <a
              href={citation.source}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-blue-700 hover:underline truncate max-w-[260px]"
              title={citation.source}
            >
              {domain}
            </a>
          ) : (
            <span className="text-xs font-semibold text-slate-700 truncate max-w-[260px]">
              {domain}
            </span>
          )}
          {citation.date && (
            <span className="text-[10px] text-slate-400 flex-shrink-0">
              {citation.date}
            </span>
          )}
          {hasUrl && (
            <a
              href={citation.source}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Open source"
            >
              <svg className="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          )}
        </div>

        {/* Excerpt */}
        {citation.excerpt && (
          <p className="mt-1 text-xs text-slate-500 italic leading-relaxed line-clamp-2">
            "{citation.excerpt}"
          </p>
        )}
      </div>
    </div>
  );
}
