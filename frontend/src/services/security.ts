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

export interface Permission {
  code: string;
  resource: string;
  action: string;
  description: string;
}

export interface Role {
  id: number;
  name: string;
  description: string | null;
  is_system: boolean;
  created_at: string;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  status: string;
  error_message: string | null;
  timestamp: string;
}

export interface SecurityStatus {
  rbac: string;
  permissions_count: number;
  roles_count: number;
  audit_count: number;
  last_audit_time: string | null;
}

export async function fetchPermissions(): Promise<Permission[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/permissions`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch permissions: ${res.status}`);
  return res.json();
}

export async function fetchRoles(): Promise<Role[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/roles`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch roles: ${res.status}`);
  return res.json();
}

export async function fetchAuditLogs(limit = 5): Promise<AuditLog[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/audit?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch audit logs: ${res.status}`);
  const data = await res.json();
  return data.logs ?? [];
}

export async function fetchSecurityStatus(): Promise<SecurityStatus> {
  const [perms, roles, audit] = await Promise.all([
    fetchPermissions(),
    fetchRoles(),
    fetchAuditLogs(5),
  ]);

  return {
    rbac: perms.length > 0 ? 'Active' : 'Inactive',
    permissions_count: perms.length,
    roles_count: roles.length,
    audit_count: audit.length,
    last_audit_time: audit.length > 0 ? audit[0].timestamp : null,
  };
}