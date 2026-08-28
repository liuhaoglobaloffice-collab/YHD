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

export interface ProviderInfo {
  provider: string;
  model: string;
  mode: string;
  enabled: boolean;
  registry_key: string;
}

export interface ModelRegistry {
  providers: ProviderInfo[];
  total: number;
}

export async function fetchProviders(): Promise<ProviderInfo[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/productization/providers`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch providers: ${res.status}`);
  const data = await res.json();
  return data.providers ?? [];
}