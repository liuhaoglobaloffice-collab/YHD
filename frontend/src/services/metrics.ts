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

export interface SystemHealth {
  overall_status: string;
  components: Array<{
    name: string;
    status: string;
    load: number;
    last_check: string;
  }>;
  last_updated: string;
}

export interface SystemInfo {
  version: string;
  environment: string;
  features: Record<string, boolean>;
  policies: Record<string, boolean>;
}

export interface MetricsData {
  cpu_load: number;
  memory_load: number;
  latency_ms: number;
  throughput: number;
  system_version: string;
  environment: string;
  overall_status: string;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/dashboard/system-health`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch system health: ${res.status}`);
  return res.json();
}

export async function fetchSystemInfo(): Promise<SystemInfo> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/health/system`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch system info: ${res.status}`);
  return res.json();
}

export async function fetchMetrics(): Promise<MetricsData> {
  const [health, info] = await Promise.all([
    fetchSystemHealth(),
    fetchSystemInfo(),
  ]);

  const dbComponent = health.components.find(c => c.name === 'Database');
  const apiComponent = health.components.find(c => c.name === 'API Gateway');
  const brainComponent = health.components.find(c => c.name === 'AI Brain');

  return {
    cpu_load: brainComponent?.load ?? 0,
    memory_load: dbComponent?.load ?? 0,
    latency_ms: apiComponent?.load ?? 0,
    throughput: health.components.length * 10,
    system_version: info.version,
    environment: info.environment,
    overall_status: health.overall_status,
  };
}