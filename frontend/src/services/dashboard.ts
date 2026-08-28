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

export interface DashboardOverview {
  ai_employees: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  system_health: string;
  components: Array<{ name: string; status: string; load: number }>;
  last_updated: string;
}

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/dashboard/overview`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch dashboard: ${res.status}`);
  return res.json();
}