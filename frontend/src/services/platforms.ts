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

export interface PlatformAccount {
  id: number;
  platform: string;
  name: string;
  account_id: string;
  status: string;
  is_active: boolean;
  last_connected_at?: string | null;
  created_at: string;
}

export interface PlatformOption {
  value: string;
  label: string;
}

export interface AccountList {
  accounts: PlatformAccount[];
  total: number;
  platforms: PlatformOption[];
}

export interface PlatformMessage {
  id: number;
  platform: string;
  account_id: number;
  direction: string;
  from_id?: string | null;
  from_name?: string | null;
  to_id?: string | null;
  to_name?: string | null;
  content: string;
  translated_content?: string | null;
  source_lang?: string | null;
  target_lang?: string | null;
  status: string;
  created_at: string;
}

export interface PlatformContact {
  id: number;
  platform: string;
  remote_id: string;
  name?: string | null;
  phone?: string | null;
  email?: string | null;
  last_message_at?: string | null;
}

export interface Language {
  code: string;
  name: string;
  en: string;
}

export async function fetchAccounts(): Promise<AccountList> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch accounts: ${res.status}`);
  return res.json();
}

export async function bindAccount(payload: {
  platform: string;
  name: string;
  account_id: string;
  credentials?: Record<string, unknown> | null;
}): Promise<PlatformAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `绑定失败: ${res.status}`);
  }
  return res.json();
}

export async function unbindAccount(accountId: number): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`解绑失败: ${res.status}`);
}

export async function testAccount(accountId: number): Promise<{ ok: boolean; message: string }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/test`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '测试失败');
  }
  return res.json();
}

export async function sendPlatformMessage(
  accountId: number,
  payload: { to_id: string; to_name?: string; content: string; target_lang?: string }
): Promise<PlatformMessage> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/messages`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `发送失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchMessages(accountId: number): Promise<PlatformMessage[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/messages`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
  return res.json();
}

export async function receiveMessages(accountId: number): Promise<PlatformMessage[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/receive`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to receive: ${res.status}`);
  return res.json();
}

export async function fetchContacts(accountId: number): Promise<PlatformContact[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/contacts`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch contacts: ${res.status}`);
  return res.json();
}

export async function syncContacts(accountId: number): Promise<{ synced: number }> {
  const res = await fetch(
    `${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/contacts/sync`,
    { method: 'POST', headers: authHeaders() }
  );
  if (!res.ok) throw new Error('同步联系人失败');
  return res.json();
}

export async function fetchLanguages(): Promise<Language[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/languages`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('获取语言列表失败');
  return (await res.json()).languages;
}

export async function translateText(
  text: string,
  target_lang: string
): Promise<{ translated: string; mock: boolean }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/translate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ text, target_lang }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '翻译失败');
  }
  return res.json();
}

// ==================== 新增 ====================

export async function updateAccount(
  accountId: number,
  payload: { name?: string; credentials?: Record<string, unknown> }
): Promise<PlatformAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('更新账号失败');
  return res.json();
}

export async function toggleAccount(accountId: number): Promise<PlatformAccount> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/toggle`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('切换状态失败');
  return res.json();
}

export async function searchMessages(accountId: number, q: string): Promise<PlatformMessage[]> {
  const res = await fetch(
    `${API_BASE}${API_PREFIX}/platforms/accounts/${accountId}/messages/search?q=${encodeURIComponent(q)}`,
    { headers: authHeaders() }
  );
  if (!res.ok) throw new Error('搜索消息失败');
  return res.json();
}
