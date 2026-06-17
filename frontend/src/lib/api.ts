/**
 * frontend/src/lib/api.ts
 * ─────────────────────────
 * Type-safe API client for the Croma CI backend.
 * All requests include JWT auth token from localStorage.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────

export interface KeyMetric {
  metric: string;
  value: string;
  period: string;
}

export interface Citation {
  source: string;
  date: string;
  excerpt: string;
}

export interface DimensionResult {
  summary: string;
  key_metrics: KeyMetric[];
  citations: Citation[];
  confidence_score: number;
  competitor?: string;
  ci_dimension?: string;
  query?: string;
}

export interface QueryResponse {
  query: string;
  summary: string;
  key_metrics: KeyMetric[];
  citations: Citation[];
  confidence_score: number;
  sub_query_count: number;
}

export interface CompareResponse {
  ci_dimension: string;
  generated_at: string;
  competitors: Record<string, DimensionResult>;
}

export interface CompetitorReport {
  competitor: string;
  competitor_display: string;
  generated_at: string;
  dimensions: Record<string, DimensionResult>;
  overall_confidence: number;
}

export interface SourceRecord {
  competitor: string;
  source_type: string;
  source_url: string;
  publication_date: string;
  ingestion_date: string;
  chunk_count: number;
  ci_dimensions: string[];
  status: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  components: Record<string, { ok: boolean; models?: string[] }>;
}

// ── Auth ──────────────────────────────────────────────────────────

let _token: string | null = null;

export function setToken(token: string) {
  _token = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("croma_ci_token", token);
  }
}

export function getToken(): string | null {
  if (_token) return _token;
  if (typeof window !== "undefined") {
    _token = localStorage.getItem("croma_ci_token");
  }
  return _token;
}

export function clearToken() {
  _token = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("croma_ci_token");
  }
}

// ── Fetch wrapper ─────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> || {}),
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    throw new Error("Unauthorised — please log in");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  return res.json();
}

// ── Auth endpoints ────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<void> {
  const form = new FormData();
  form.append("username", username);
  form.append("password", password);

  const res = await fetch(`${BASE_URL}/api/auth/token`, {
    method: "POST",
    body: new URLSearchParams({ username, password }),
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = await res.json();
  setToken(data.access_token);
}

// ── CI endpoints ──────────────────────────────────────────────────

export async function freeFormQuery(
  query: string,
  competitor?: string,
  ciDimension?: string,
  useCache = true
): Promise<QueryResponse> {
  return apiFetch("/api/query/", {
    method: "POST",
    body: JSON.stringify({ query, competitor, ci_dimension: ciDimension, use_cache: useCache }),
  });
}

export async function compareCompetitors(
  ciDimension: string,
  query?: string
): Promise<CompareResponse> {
  return apiFetch("/api/compare/", {
    method: "POST",
    body: JSON.stringify({ ci_dimension: ciDimension, query }),
  });
}

export async function getCompetitorReport(
  competitor: string,
  useCache = true
): Promise<CompetitorReport> {
  return apiFetch(`/api/report/${competitor}?use_cache=${useCache}`);
}

export async function exportReportPdf(competitor: string): Promise<Blob> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}/api/report/export`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ competitor, format: "pdf" }),
  });
  if (!res.ok) throw new Error("Export failed");
  return res.blob();
}

export async function listSources(
  competitor?: string,
  sourceType?: string,
  limit = 50
): Promise<{ total: number; sources: SourceRecord[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (competitor) params.set("competitor", competitor);
  if (sourceType) params.set("source_type", sourceType);
  return apiFetch(`/api/sources/?${params}`);
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch("/api/health/");
}

// ── Constants ─────────────────────────────────────────────────────

export const COMPETITORS = [
  { slug: "reliance_digital", display: "Reliance Digital" },
  { slug: "vijay_sales", display: "Vijay Sales" },
  { slug: "aditya_vision", display: "Aditya Vision" },
  { slug: "poojara", display: "Poojara" },
  { slug: "bajaj_electronics", display: "Bajaj Electronics" },
] as const;

export const CI_DIMENSIONS = [
  { slug: "business_model", display: "Business Model" },
  { slug: "geographical_presence", display: "Geographical Presence" },
  { slug: "financial_performance", display: "Financial Performance" },
  { slug: "customer_feedback", display: "Customer Feedback" },
  { slug: "strategic_initiatives", display: "Strategic Initiatives" },
  { slug: "future_outlook", display: "Future Outlook" },
] as const;
