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

export interface TradeTemplate {
  template_id: string;
  name: string;
  description: string;
  category: string;
  estimated_total_minutes: number;
  steps: Array<{ name: string; description: string; type: string; estimated_minutes: number }>;
  inputs: Array<{ key: string; label: string; type: string; required: boolean; default?: unknown; placeholder?: string; options?: string[] }>;
  icon: string;
  color: string;
}

export interface InstantiateResult {
  template_id: string;
  template_name: string;
  status: string;
  inputs: Record<string, unknown>;
  steps: Array<{ name: string; type: string; result: Record<string, unknown> }>;
  total_steps: number;
  completed_steps: number;
}

export async function fetchTradeTemplates(): Promise<{ items: TradeTemplate[]; total: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workflows/trade-templates`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取外贸模板失败: ${res.status}`);
  return res.json();
}

export async function fetchTradeTemplate(templateId: string): Promise<TradeTemplate> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workflows/trade-templates/${encodeURIComponent(templateId)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取模板详情失败: ${res.status}`);
  return res.json();
}

export async function instantiateTradeTemplate(
  templateId: string,
  inputData: Record<string, unknown>
): Promise<InstantiateResult> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workflows/trade-templates/${encodeURIComponent(templateId)}/instantiate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ input_data: inputData }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '执行模板失败');
  }
  return res.json();
}