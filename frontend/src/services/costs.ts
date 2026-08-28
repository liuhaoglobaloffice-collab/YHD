const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export interface CostRecord {
  id: number;
  provider: string;
  model?: string | null;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms?: number | null;
  status: string;
  employee_id?: string | null;
  agent_type?: string | null;
  created_at?: string | null;
}

export interface CostSummary {
  days: number;
  total_requests: number;
  total_cost_usd: number;
  total_tokens: number;
  avg_latency_ms: number;
  failed_requests: number;
  by_provider: Record<string, { requests: number; cost_usd: number; tokens: number }>;
}

export async function fetchCostSummary(days = 7): Promise<CostSummary> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/costs/summary?days=${days}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch cost summary: ${res.status}`);
  return res.json();
}

export async function fetchCostRecords(limit = 10): Promise<CostRecord[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/costs?limit=${limit}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch cost records: ${res.status}`);
  return res.json();
}