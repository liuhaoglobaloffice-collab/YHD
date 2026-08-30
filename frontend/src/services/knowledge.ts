// Knowledge / RAG API client — wires the Knowledge page to the real
// backend knowledge pipeline: document upload -> chunk -> embedding ->
// semantic retrieval, plus persisted memory.
const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export interface KnowledgeDocument {
  id: string;
  title?: string;
  filename?: string;
  file_type?: string;
  status?: string;
  created_at?: string;
  tags?: string[];
  summary?: string;
  [key: string]: unknown;
}

export interface KnowledgeSearchResult {
  id: string;
  source?: string;
  source_type?: string;
  title?: string;
  content?: string;
  snippet?: string;
  text?: string;
  score?: number;
  created_at?: string;
}

export interface KnowledgeMemory {
  memory_id?: string;
  id?: string;
  memory_type?: string;
  content?: string;
  value?: string;
  key?: string;
  created_at?: string;
}

export async function listDocuments(): Promise<KnowledgeDocument[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/knowledge/documents?limit=100`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to load documents: ${res.status}`);
  const data = await res.json();
  return data.documents ?? [];
}

export async function uploadDocument(file: File, title?: string): Promise<unknown> {
  const form = new FormData();
  form.append('file', file);
  if (title) form.append('title', title);
  const res = await fetch(`${API_BASE}${API_PREFIX}/knowledge/documents`, {
    method: 'POST',
    headers: authHeaders(), // browser sets multipart boundary automatically
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail ?? `Upload failed: ${res.status}`);
  return data;
}

export async function semanticSearch(
  query: string,
  strategy: 'semantic' | 'keyword' | 'hybrid' = 'semantic',
  sources: string[] = ['document', 'memory']
): Promise<{ results: KnowledgeSearchResult[]; total: number }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/knowledge/retrieval/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ query, strategy, sources, limit: 10, offset: 0 }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail ?? `Search failed: ${res.status}`);
  return { results: data.results ?? [], total: data.total ?? 0 };
}

export async function listMemories(): Promise<KnowledgeMemory[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/knowledge/memory?limit=50`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to load memories: ${res.status}`);
  const data = await res.json();
  return data.memories ?? [];
}
