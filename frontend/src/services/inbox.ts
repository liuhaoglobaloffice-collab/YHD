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

export interface InboxMessage {
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
  remote_id?: string | null;
}

export interface InboxResponse {
  messages: InboxMessage[];
  total: number;
  page: number;
  page_size: number;
}

export interface InboxStats {
  total: number;
  today: number;
  pending: number;
  reply_rate: number;
  by_platform: Record<string, number>;
}

export async function fetchInbox(params?: {
  platform?: string;
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<InboxResponse> {
  const searchParams = new URLSearchParams();
  if (params?.platform) searchParams.set('platform', params.platform);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.q) searchParams.set('q', params.q);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/inbox${qs ? '?' + qs : ''}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取收件箱失败: ${res.status}`);
  return res.json();
}

export async function fetchInboxStats(): Promise<InboxStats> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/inbox/stats`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取收件箱统计失败: ${res.status}`);
  return res.json();
}

export async function replyInboxMessage(
  messageId: number,
  content: string,
  targetLang?: string
): Promise<{ message_id: number; status: string }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/inbox/${messageId}/reply`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ content, target_lang: targetLang }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '回复失败');
  }
  return res.json();
}