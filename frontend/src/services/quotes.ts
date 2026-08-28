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

export interface QuoteItem {
  product_name: string;
  product_code?: string;
  specification?: string;
  unit: string;
  quantity: number;
  unit_price: number;
  remark?: string;
}

export interface Quote {
  id: number;
  quote_number: string;
  lead_id?: number | null;
  lead_name: string;
  lead_company?: string | null;
  lead_email?: string | null;
  lead_phone?: string | null;
  status: string;
  subject: string;
  currency: string;
  subtotal: number;
  discount: number;
  tax_rate: number;
  tax_amount: number;
  total_amount: number;
  valid_days: number;
  payment_terms?: string | null;
  delivery_terms?: string | null;
  notes?: string | null;
  items: Array<{
    id?: number;
    product_name: string;
    product_code?: string;
    specification?: string;
    unit: string;
    quantity: number;
    unit_price: number;
    total_price: number;
    remark?: string;
  }>;
  created_at?: string;
  updated_at?: string;
  sent_at?: string | null;
  expires_at?: string | null;
}

export interface QuoteList {
  items: Quote[];
  total: number;
  page: number;
  page_size: number;
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  pending_approval: '待审批',
  approved: '已审批',
  sent: '已发送',
  following_up: '跟进中',
  accepted: '已成交',
  rejected: '已拒绝',
  expired: '已过期',
};

const STATUS_COLORS: Record<string, string> = {
  draft: '#888',
  pending_approval: '#facc15',
  approved: '#4ade80',
  sent: '#4cc9f0',
  following_up: '#8fa0e0',
  accepted: '#10b981',
  rejected: '#ff4444',
  expired: '#666',
};

export { STATUS_LABELS, STATUS_COLORS };

export async function fetchQuotes(params?: {
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<QuoteList> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.q) searchParams.set('q', params.q);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));
  const qs = searchParams.toString();
  const res = await fetch(`${API_BASE}${API_PREFIX}/quotes${qs ? '?' + qs : ''}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取报价单失败: ${res.status}`);
  return res.json();
}

export async function fetchQuote(id: number): Promise<Quote> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/quotes/${id}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取报价单详情失败: ${res.status}`);
  return res.json();
}

export async function createQuote(data: {
  lead_id?: number;
  lead_name: string;
  lead_company?: string;
  lead_email?: string;
  lead_phone?: string;
  subject: string;
  currency?: string;
  discount?: number;
  tax_rate?: number;
  valid_days?: number;
  payment_terms?: string;
  delivery_terms?: string;
  notes?: string;
  items: QuoteItem[];
}): Promise<Quote> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/quotes`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '创建报价单失败');
  }
  return res.json();
}

export async function updateQuoteStatus(id: number, status: string): Promise<Quote> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/quotes/${id}/status`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '更新状态失败');
  }
  return res.json();
}

export async function sendQuote(id: number, sendVia?: string): Promise<{ status: string; sent_via: string[]; quote_number: string }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/quotes/${id}/send`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ send_via: sendVia }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '发送报价单失败');
  }
  return res.json();
}