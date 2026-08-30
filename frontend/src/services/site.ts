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

export interface Site {
  id: number;
  domain: string;
  name: string;
  platform: string;
  status: string;
  default_meta_title?: string | null;
  default_meta_description?: string | null;
  default_lang?: string | null;
  target_countries: string[];
  target_keywords: string[];
  created_at: string;
}

export interface SiteStats {
  pages: number;
  published: number;
  total_views: number;
  total_conversions: number;
  conversion_rate: number;
}

export interface SitePage {
  id: number;
  site_id: number;
  title: string;
  slug: string;
  content?: string | null;
  content_type: string;
  meta_title?: string | null;
  meta_description?: string | null;
  keywords: string[];
  canonical_url?: string | null;
  status: string;
  published_at?: string | null;
  views: number;
  conversions: number;
  created_at: string;
  updated_at: string;
}

export interface KeywordInfo {
  keyword: string;
  volume: number;
  difficulty: number;
  opportunity: number;
  suggestions: string[];
}

export interface SEOContentResult {
  keyword: string;
  title?: string;
  suggested_slug?: string;
  meta_description?: string;
  outline?: string[];
  tags?: string[];
  content?: string;
  search_intent?: string;
  method: string;
  source_type?: string;
  llm_error?: string | null;
  saved_id?: number | null;
}

export interface KeywordRank {
  id?: number;
  keyword: string;
  rank?: number | null;
  previous_rank?: number | null;
  trend: string;
  search_volume?: number | null;
  url?: string | null;
  country?: string | null;
  checked_at?: string;
}

export interface SEOSavedContent {
  id: number;
  keyword: string;
  title?: string;
  meta_description?: string;
  outline?: string;
  content?: string;
  content_type: string;
  suggested_slug?: string;
  suggested_tags: string[];
  search_intent?: string;
  method: string;
  source_type?: string;
  created_at: string;
}

// ==================== 独立站 ====================

export async function fetchSites(): Promise<{ items: Site[]; total: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch sites: ${res.status}`);
  return res.json();
}

export async function createSite(payload: Record<string, unknown>): Promise<Site> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `创建站点失败: ${res.status}`);
  }
  return res.json();
}

export async function deleteSite(siteId: number): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('删除站点失败');
}

export async function fetchSiteStats(siteId: number): Promise<SiteStats> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/stats`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch site stats: ${res.status}`);
  return res.json();
}

// ==================== 页面 ====================

export async function fetchPages(
  siteId: number,
  status?: string
): Promise<{ items: SitePage[]; total: number }> {
  const q = status ? `?status=${status}` : '';
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/pages${q}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch pages: ${res.status}`);
  return res.json();
}

export async function createPage(
  siteId: number,
  payload: Record<string, unknown>
): Promise<SitePage> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/pages`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `创建页面失败: ${res.status}`);
  }
  return res.json();
}

export async function updatePage(
  siteId: number,
  pageId: number,
  patch: Record<string, unknown>
): Promise<SitePage> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/pages/${pageId}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`更新页面失败: ${res.status}`);
  return res.json();
}

export async function publishPage(siteId: number, pageId: number): Promise<SitePage> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/pages/${pageId}/publish`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`发布失败: ${res.status}`);
  return res.json();
}

export async function deletePage(siteId: number, pageId: number): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/pages/${pageId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('删除页面失败');
}

// ==================== SEO ====================

export async function analyzeKeywords(
  keywords?: string[],
  limit = 10
): Promise<KeywordInfo[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/seo/keywords/analyze`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ keywords, limit }),
  });
  if (!res.ok) throw new Error(`关键词分析失败: ${res.status}`);
  return (await res.json()).keywords;
}

export async function generateSEOContent(
  keyword: string,
  save = true
): Promise<SEOContentResult> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/seo/content/generate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ keyword, save }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `生成内容失败: ${res.status}`);
  }
  return res.json();
}

export async function trackRankings(
  keywords: string[],
  save = true
): Promise<KeywordRank[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/seo/rankings/track`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ keywords, save }),
  });
  if (!res.ok) throw new Error(`排名跟踪失败: ${res.status}`);
  return (await res.json()).rankings;
}

export async function fetchRankings(): Promise<KeywordRank[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/seo/rankings`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取排名失败: ${res.status}`);
  return res.json();
}

export async function fetchSEOContents(): Promise<SEOSavedContent[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/seo/contents`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取内容失败: ${res.status}`);
  return res.json();
}
// ==================== SEO 文件（P1-G5.4） ====================

export interface SEOFilesResult {
  source_type: string;
  sitemap_xml: string;
  robots_txt: string;
  published_pages: number;
  sitemap_url: string;
}

export interface PageSchemaResult {
  source_type: string;
  schema: Record<string, unknown>;
  json_ld: string;
}

export async function fetchSEOFiles(siteId: number): Promise<SEOFilesResult> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/seo/files`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取 SEO 文件失败: ${res.status}`);
  return res.json();
}

export async function fetchPageSchema(siteId: number, pageId: number): Promise<PageSchemaResult> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/site/sites/${siteId}/pages/${pageId}/schema`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取结构化数据失败: ${res.status}`);
  return res.json();
}