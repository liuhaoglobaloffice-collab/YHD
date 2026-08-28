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

export interface LeadItem {
  id: number;
  source: string;
  source_label: string;
  source_detail?: string | null;
  name: string;
  company?: string | null;
  country?: string | null;
  city?: string | null;
  industry?: string | null;
  phone?: string | null;
  email?: string | null;
  whatsapp?: string | null;
  wechat?: string | null;
  linkedin?: string | null;
  website?: string | null;
  product_interest?: string | null;
  estimated_value?: number | null;
  score: number;
  status: string;
  status_label: string;
  priority: string;
  quote_amount?: number | null;
  won_amount?: number | null;
  expected_close_at?: string | null;
  lost_reason?: string | null;
  next_follow_up_at?: string | null;
  last_activity_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadDetail extends LeadItem {
  activities: LeadActivity[];
}

export interface LeadActivity {
  id: number;
  lead_id: number;
  activity_type: string;
  content: string;
  result?: string | null;
  created_at: string;
}

export interface FunnelStage {
  status: string;
  count: number;
  rate: number;
}

export interface LeadStats {
  total: number;
  by_status: Record<string, number>;
  stages: FunnelStage[];
  total_estimated_value: number;
  quote_total: number;
  won_total: number;
  win_rate: number;
  lost_by_reason: Record<string, number>;
  follow_up_due: number;
}

export interface CustomsRecord {
  id?: number;
  hs_code?: string | null;
  product: string;
  product_desc?: string | null;
  importer_name?: string | null;
  importer_country?: string | null;
  exporter_name?: string | null;
  exporter_country?: string | null;
  quantity?: number | null;
  unit?: string | null;
  value?: number | null;
  trade_date?: string | null;
}

export interface SupplierReport {
  id: number;
  supplier_id?: number | null;
  supplier_name: string;
  product_category?: string | null;
  risk_level?: string | null;
  risk_score?: number | null;
  risk_summary?: string | null;
  price_level?: string | null;
  price_score?: number | null;
  price_summary?: string | null;
  capacity_level?: string | null;
  capacity_score?: number | null;
  capacity_summary?: string | null;
  overall_score?: number | null;
  overall_level?: string | null;
  report?: string | null;
  recommendations: string[];
  analysis_method: string;
  created_at: string;
}

// ==================== 获客引擎 ====================

export async function runAcquisition(payload: {
  sources: string[];
  keywords?: string[];
  limit?: number;
  save_to_pool?: boolean;
}): Promise<{
  leads: Array<Record<string, unknown> & { name: string; source: string }>;
  stats: Record<string, number>;
  saved: { created: number; skipped: number };
}> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/acquisition/run`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `获客失败: ${res.status}`);
  }
  return res.json();
}

// ==================== 线索池 ====================

export async function fetchLeads(params: {
  status?: string;
  source?: string;
  keyword?: string;
  follow_up?: boolean;
  page?: number;
  page_size?: number;
}): Promise<{ items: LeadItem[]; total: number; page: number; page_size: number }> {
  const q = new URLSearchParams();
  if (params.status) q.set('status', params.status);
  if (params.source) q.set('source', params.source);
  if (params.keyword) q.set('keyword', params.keyword);
  if (params.follow_up) q.set('follow_up', 'true');
  q.set('page', String(params.page ?? 1));
  q.set('page_size', String(params.page_size ?? 50));
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads?${q}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch leads: ${res.status}`);
  return res.json();
}

export async function fetchLeadStats(): Promise<LeadStats> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/stats`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取线索统计失败');
  return res.json();
}

export async function fetchLeadDetail(leadId: number): Promise<LeadDetail> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/${leadId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch lead: ${res.status}`);
  return res.json();
}

export async function createLead(payload: Record<string, unknown>): Promise<LeadItem> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `创建线索失败: ${res.status}`);
  }
  return res.json();
}

export async function updateLead(leadId: number, patch: Record<string, unknown>): Promise<LeadItem> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/${leadId}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`更新线索失败: ${res.status}`);
  return res.json();
}

export async function deleteLead(leadId: number): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/${leadId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('删除线索失败');
}

export async function addLeadActivity(
  leadId: number,
  payload: { activity_type: string; content: string; result?: string; next_follow_up_at?: string }
): Promise<LeadActivity> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/${leadId}/activities`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`添加跟进失败: ${res.status}`);
  return res.json();
}

// ==================== 海关数据 ====================

export async function searchCustoms(payload: {
  product?: string;
  country?: string;
  limit?: number;
  save?: boolean;
}): Promise<{ records: CustomsRecord[]; saved: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/customs/search`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`海关查询失败: ${res.status}`);
  return res.json();
}

export async function fetchCustoms(product?: string): Promise<CustomsRecord[]> {
  const q = product ? `?product=${encodeURIComponent(product)}` : '';
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/customs${q}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取海关数据失败: ${res.status}`);
  return res.json();
}

// ==================== 供应商发现与分析 ====================

export async function discoverSuppliers(payload: {
  product?: string;
  limit?: number;
}): Promise<{ suppliers: Array<Record<string, unknown> & { name: string }>; total: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/suppliers/discover`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`发现供应商失败: ${res.status}`);
  return res.json();
}

export async function analyzeSupplier(payload: {
  supplier_name: string;
  product_category?: string;
  supplier_data?: Record<string, unknown>;
  supplier_id?: number;
}): Promise<SupplierReport> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/suppliers/analyze`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `分析失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchSupplierReports(): Promise<SupplierReport[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/suppliers/analysis`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取分析报告失败: ${res.status}`);
  return res.json();
}

// ==================== 询价 / 比价（V3） ====================

export interface SupplierInquiry {
  id: number;
  supplier_name: string;
  product: string;
  quantity?: number | null;
  unit_price?: number | null;
  currency?: string | null;
  lead_time?: string | null;
  payment?: string | null;
  quality_note?: string | null;
  note?: string | null;
  created_by?: number | null;
  created_at: string;
}

export interface InquiryCompare {
  product: string;
  count: number;
  cheapest: SupplierInquiry | null;
  items: SupplierInquiry[];
}

export async function createInquiry(payload: {
  supplier_name: string;
  product: string;
  quantity?: number;
  unit_price?: number;
  currency?: string;
  lead_time?: string;
  payment?: string;
  quality_note?: string;
  note?: string;
}): Promise<SupplierInquiry> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/supplier-inquiries`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `录入询价失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchInquiries(product?: string): Promise<SupplierInquiry[]> {
  const q = product ? `?product=${encodeURIComponent(product)}` : '';
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/supplier-inquiries${q}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取询价记录失败: ${res.status}`);
  return res.json();
}

export async function compareInquiries(product: string): Promise<InquiryCompare> {
  const res = await fetch(
    `${API_BASE}${API_PREFIX}/crm/supplier-inquiries/compare?product=${encodeURIComponent(product)}`,
    { headers: authHeaders() }
  );
  if (!res.ok) throw new Error(`比价失败: ${res.status}`);
  return res.json();
}

// ==================== 报价单（V3） ====================

export interface Quotation {
  lead_id: number;
  company?: string | null;
  contact?: string | null;
  email?: string | null;
  whatsapp?: string | null;
  country?: string | null;
  product?: string | null;
  quantity: number;
  currency: string;
  unit_price?: number | null;
  freight?: number | null;
  total: number;
  moq?: string | null;
  lead_time: string;
  payment: string;
  valid_until: string;
  notes?: string | null;
  missing_fields: string[];
}

export async function generateQuotation(
  leadId: number,
  params?: { quantity?: number; unit_price?: number; moq?: string; lead_time?: string; payment?: string; currency?: string; freight?: number; valid_days?: number }
): Promise<Quotation> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/${leadId}/quotation`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(params ?? {}),
  });
  if (!res.ok) throw new Error(`生成报价单失败: ${res.status}`);
  return res.json();
}

// ==================== 外贸周报（V3） ====================

export interface WeeklyReport {
  days: number;
  period: string;
  leads: { new_total: number; by_source: Record<string, number>; follow_up_due: number };
  funnel: { quoted: number; won_count: number; won_amount: number; lost_count: number; lost_reasons: Record<string, number> };
  messages: { sent: number; received: number };
  supplier_reports: number;
  inquiries: number;
  ai: { calls: number; cost_usd: number };
  summary: string;
}

export async function fetchWeeklyReport(days = 7): Promise<WeeklyReport> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/weekly-report?days=${days}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取周报失败');
  return res.json();
}

// ==================== 导出 ====================

export async function exportLeadsCsv(): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/export`, { headers: authHeaders() });
  if (!res.ok) throw new Error('导出失败');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'leads.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// ==================== AI 员工分配 ====================

export async function assignLeadToEmployee(leadId: number, employeeId: string): Promise<LeadItem> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/${leadId}/assign`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ employee_id: employeeId }),
  });
  if (!res.ok) throw new Error('分配失败');
  return res.json();
}

export async function batchAssignLeads(leadIds: number[], employeeId: string): Promise<{ assigned: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/crm/leads/batch-assign`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ lead_ids: leadIds, employee_id: employeeId }),
  });
  if (!res.ok) throw new Error('批量分配失败');
  return res.json();
}
