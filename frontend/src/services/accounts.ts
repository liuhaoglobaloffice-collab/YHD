const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { ...(extra ?? {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export interface SubAccount {
  id: number;
  username: string;
  email: string;
  full_name?: string | null;
  role: string;
  business_role?: string | null;
  account_type?: string | null;
  is_active: boolean;
  data_scope?: string | null;
  approval_status?: string | null;
  created_at: string;
  last_login?: string | null;
  permissions_config?: Record<string, boolean> | null;
  ai_budget_monthly?: number | null;
}

export interface SubAccountList {
  sub_accounts: SubAccount[];
  total: number;
}

export async function fetchSubAccounts(): Promise<SubAccountList> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch sub accounts: ${res.status}`);
  return res.json();
}

export async function createSubAccount(payload: {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  business_role?: string;
  data_scope?: string;
}): Promise<SubAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `创建子账号失败: ${res.status}`);
  }
  return res.json();
}

export async function updateSubAccount(
  subId: number,
  patch: { business_role?: string; is_active?: boolean; data_scope?: string; full_name?: string }
): Promise<SubAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${subId}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `更新子账号失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchPendingApprovals(): Promise<SubAccountList> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/pending-approvals`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch pending approvals: ${res.status}`);
  return res.json();
}

export async function approveSubAccount(subId: number): Promise<SubAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/${subId}/approve`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `同意失败: ${res.status}`);
  }
  return res.json();
}

export async function rejectSubAccount(subId: number): Promise<SubAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/${subId}/reject`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `拒绝失败: ${res.status}`);
  }
  return res.json();
}

/** 系统中主账号信息（公开接口，不需要 token）。 */
export interface OwnerInfo {
  has_owner: boolean;
  owner_username: string | null;
  owner_email: string | null;
}

export async function fetchOwnerInfo(): Promise<OwnerInfo> {
  const base = import.meta.env?.VITE_API_BASE ?? '';
  const res = await fetch(`${base}/api/v1/auth/owner-info`);
  if (!res.ok) throw new Error(`获取主账号信息失败: ${res.status}`);
  return res.json();
}

/** 子账号自助注册（公开接口，不需要 token）。 */
export async function registerSubAccount(payload: {
  username: string;
  password: string;
}): Promise<{ id: number; username: string; status: string; owner_username: string; message: string }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/auth/register-sub`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `注册失败: ${res.status}`);
  }
  return res.json();
}

// ==================== AI 预算（V4） ====================

export interface SubBudget {
  user_id: number;
  username: string;
  month: string;
  monthly_budget?: number | null;
  used_usd: number;
  calls: number;
  remaining_usd?: number | null;
  over_budget: boolean;
}

export async function fetchMyBudget(): Promise<SubBudget> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/budget/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取预算失败: ${res.status}`);
  return res.json();
}

export async function fetchSubBudgets(): Promise<{ items: SubBudget[]; total: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/budgets`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取子账号预算失败: ${res.status}`);
  return res.json();
}

export async function setSubBudget(subId: number, monthly_budget: number): Promise<SubBudget> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${subId}/budget`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ monthly_budget }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `设置预算失败: ${res.status}`);
  }
  return res.json();
}

// ==================== 子账号数据摘要（V4 · 主账号数据管理台） ====================

export interface SubDataSummary {
  user_id: number;
  username: string;
  leads: { total: number; by_status: Record<string, number>; total_estimated_value: number };
  messages: number;
  inquiries: number;
  ai_cost: { month: string; cost_usd: number; calls: number };
  budget: SubBudget;
}

export async function fetchSubDataSummary(subId: number): Promise<SubDataSummary> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${subId}/data-summary`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取子账号数据失败: ${res.status}`);
  return res.json();
}

// ==================== 业务角色与权限配置 ====================

export interface BusinessRoleInfo {
  role: string;
  label: string;
  description: string;
  permissions: string[];
}

export async function fetchBusinessRoles(): Promise<BusinessRoleInfo[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/roles`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取业务角色失败: ${res.status}`);
  return res.json();
}

export async function fetchAllPermissions(): Promise<{ permissions: string[] }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/permissions/all`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取权限列表失败: ${res.status}`);
  return res.json();
}

export async function fetchSubPermissions(subId: number): Promise<{
  user_id: number;
  username: string;
  business_role: string | null;
  data_scope: string;
  permissions_config: Record<string, boolean>;
}> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${subId}/permissions`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取权限配置失败: ${res.status}`);
  return res.json();
}

export async function updateSubPermissions(
  subId: number,
  permissions: Record<string, boolean>
): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${subId}/permissions`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ permissions }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `更新权限失败: ${res.status}`);
  }
}

export async function updateSubDataScope(
  subId: number,
  dataScope: string
): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${subId}/data-scope`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ data_scope: dataScope }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `更新数据范围失败: ${res.status}`);
  }
}

export async function approveSubAccountWithRole(
  subId: number,
  payload: { business_role: string; data_scope?: string; full_name?: string }
): Promise<SubAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/${subId}/approve`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `审批失败: ${res.status}`);
  }
  return res.json();
}
