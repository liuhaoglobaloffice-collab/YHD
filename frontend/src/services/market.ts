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

export interface EmployeeTemplate {
  id: number;
  name: string;
  department: string;
  position: string;
  description?: string | null;
  agent_type?: string | null;
  category: string;
  author?: string | null;
  version: string;
  price: number;
  rating: number;
  installs: number;
  skill_ids: number[];
}

export interface SkillPack {
  id: number;
  name: string;
  code: string;
  description?: string | null;
  category: string;
  capabilities: string[];
  is_system: boolean;
  version: string;
}

export interface MarketEmployee {
  id: string;
  name: string;
  department: string;
  position: string;
  description: string;
  agent_type?: string | null;
  status: string;
  skills: string[];
  market_category?: string | null;
  created_at: string;
}

export interface MetaKnowledge {
  id: number;
  source_employee_id?: number | null;
  source_employee_name?: string | null;
  source_type: string;
  title: string;
  summary?: string | null;
  knowledge?: string | null;
  tags: string[];
  method: string;
  created_at: string;
}

export interface EvolutionProposal {
  id: number;
  title: string;
  category: string;
  analysis?: string | null;
  improvements: string[];
  risks: string[];
  action_plan: string[];
  summary?: string | null;
  full_text?: string | null;
  status: string;
  method: string;
  created_at: string;
}

// ==================== 市场 ====================

export async function fetchTemplates(category?: string): Promise<EmployeeTemplate[]> {
  const q = category ? `?category=${category}` : '';
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/templates${q}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch templates: ${res.status}`);
  return (await res.json()).items;
}

export async function installTemplate(templateId: number): Promise<MarketEmployee> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/templates/install`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ template_id: templateId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `安装失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchSkillPacks(): Promise<SkillPack[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/skills`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取技能包失败');
  return (await res.json()).items;
}

export async function installSkillToEmployee(employeeId: string, skillId: number): Promise<MarketEmployee> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/skills/install`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ employee_id: employeeId, skill_id: skillId }),
  });
  if (!res.ok) throw new Error(`安装技能失败: ${res.status}`);
  return res.json();
}

export async function fetchMarketEmployees(): Promise<MarketEmployee[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/employees`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取员工失败');
  return (await res.json()).items;
}

// ==================== 元学习 ====================

export async function runMetaLearning(): Promise<MetaKnowledge> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/meta-learning/run`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('元学习执行失败');
  return res.json();
}

export async function fetchMetaKnowledge(): Promise<MetaKnowledge[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/meta-learning`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取知识失败');
  return (await res.json()).items;
}

// ==================== 自我进化 ====================

export async function generateEvolution(): Promise<EvolutionProposal> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/evolution/generate`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error('进化方案生成失败');
  return res.json();
}

export async function fetchProposals(): Promise<EvolutionProposal[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/evolution`, { headers: authHeaders() });
  if (!res.ok) throw new Error('获取方案失败');
  return (await res.json()).items;
}

// ==================== 新增: 元学习知识管理 ====================

export async function deleteMetaKnowledge(knowledgeId: number): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/meta-learning/${knowledgeId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error('删除知识失败');
}

// ==================== 新增: 进化方案操作 ====================

export async function applyProposal(proposalId: number, action: 'apply' | 'reject'): Promise<EvolutionProposal> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/market/evolution/${proposalId}`, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error('操作方案失败');
  return res.json();
}