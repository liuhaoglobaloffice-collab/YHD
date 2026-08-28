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

export const IMPORT_TYPES = [
  { value: 'supplier', label: '供应商' },
  { value: 'customer', label: '客户' },
  { value: 'contract', label: '合同' },
  { value: 'quotation', label: '报价' },
] as const;

export type ImportTypeValue = (typeof IMPORT_TYPES)[number]['value'];

export interface ImportResult {
  import_record_id: number;
  status: string;
  total: number;
  success: number;
  failed: number;
  errors: { row: number; error: string }[];
}

export interface ImportRecordItem {
  id: number;
  import_type: string;
  filename: string;
  file_type: string;
  status: string;
  total: number;
  success: number;
  failed: number;
  errors: { row: number; error: string }[];
  created_by?: number | null;
  created_at?: string | null;
  completed_at?: string | null;
}

export interface ImportRecordList {
  items: ImportRecordItem[];
  total: number;
  page: number;
  page_size: number;
}

export async function uploadImport(
  importType: string,
  file: File,
  fileType: 'excel' | 'csv' = 'excel'
): Promise<ImportResult> {
  const form = new FormData();
  form.append('import_type', importType);
  form.append('file_type', fileType);
  form.append('file', file);
  const res = await fetch(`${API_BASE}${API_PREFIX}/imports/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `导入失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchImports(
  page = 1,
  pageSize = 20,
  importType?: string
): Promise<ImportRecordList> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (importType) params.set('import_type', importType);
  const res = await fetch(`${API_BASE}${API_PREFIX}/imports?${params}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch imports: ${res.status}`);
  return res.json();
}

export async function downloadImportTemplate(importType: string): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/imports/templates/${importType}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`下载模板失败: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${importType}_import_template.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
