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

export interface Template {
  id: string;
  name: string;
  category: string;
  language: string;
  platform: string;
  variables: number;
  components: { type: string; text?: string; format?: string }[];
  example?: Record<string, string[]> | null;
}

export interface TemplateRenderResult {
  rendered: string;
}

export interface TemplateSendResult {
  message_id: number;
  status: string;
  template_id: string;
  rendered: string;
}

export async function fetchTemplates(platform?: string): Promise<{ templates: Template[] }> {
  const qs = platform ? `?platform=${encodeURIComponent(platform)}` : '';
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/templates${qs}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取模板列表失败: ${res.status}`);
  return res.json();
}

export async function fetchTemplate(id: string): Promise<Template> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/templates/${encodeURIComponent(id)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`获取模板详情失败: ${res.status}`);
  return res.json();
}

export async function renderTemplate(
  templateId: string,
  variables: Record<string, string>
): Promise<TemplateRenderResult> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/templates/render`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ template_id: templateId, variables }),
  });
  if (!res.ok) throw new Error('渲染模板失败');
  return res.json();
}

export async function sendTemplate(
  templateId: string,
  accountId: number,
  toId: string,
  variables: Record<string, string>,
  toName?: string
): Promise<TemplateSendResult> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/platforms/templates/send`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      template_id: templateId,
      account_id: accountId,
      to_id: toId,
      to_name: toName,
      variables,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? '发送模板失败');
  }
  return res.json();
}