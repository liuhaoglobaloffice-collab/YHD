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

/** 运行时 Provider 状态（来自 /provider/status，反映真实可用性，而非数据库注册表） */
export interface ProviderRuntimeInfo {
  name: string;
  type: string;
  status: string; // healthy | unconfigured | error
  env_var?: string;
  models: string[];
}

export interface ProviderStatus {
  configured: boolean;
  provider: string;
  registered_any: boolean;
  using_mock: boolean;
  production_blocked: boolean;
  environment: string;
  providers: ProviderRuntimeInfo[];
}

/** 旧接口保留：Productization 数据库注册表 */
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

export async function fetchProviderStatus(): Promise<ProviderStatus> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/provider/status`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch provider status: ${res.status}`);
  return res.json();
}

export async function fetchProviders(): Promise<ProviderInfo[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/productization/providers`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch providers: ${res.status}`);
  const data = await res.json();
  return data.providers ?? [];
}
