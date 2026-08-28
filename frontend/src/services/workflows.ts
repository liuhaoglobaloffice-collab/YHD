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

export interface Workflow {
  id: string;
  name: string;
  description: string;
  definition: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export async function fetchWorkflows(): Promise<Workflow[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workflows`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch workflows: ${res.status}`);
  return res.json();
}