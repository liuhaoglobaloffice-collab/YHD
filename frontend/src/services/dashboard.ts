const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export interface DashboardOverview {
  ai_employees: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  system_health: string;
  components: Array<{ name: string; status: string; load: number }>;
  last_updated: string;
}

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/dashboard/overview`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch dashboard: ${res.status}`);
  return res.json();
}

export interface ActivityItem {
  id: string;
  timestamp: string;
  category: 'audit' | 'task' | 'workflow';
  actor: string;
  action_summary: string;
  status: string;
  detail_url?: string | null;
}

export type DashboardActivitiesResponse = ActivityItem[];

export async function fetchDashboardActivities(limit = 20): Promise<ActivityItem[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/dashboard/activities?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch dashboard activities: ${res.status}`);
  return res.json();
}

import type { ActivityItem as FeedActivityItem } from '../components/AIActivityFeed';

export function toFeedActivity(raw: ActivityItem): FeedActivityItem {
  const t = raw.timestamp.endsWith('Z') ? raw.timestamp : raw.timestamp + 'Z';
  const d = new Date(t);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const catLabel: Record<string, string> = { audit: '审计', task: '任务', workflow: '工作流' };
  const s = (raw.status || '').toLowerCase();
  let status: FeedActivityItem['status'] = 'success';
  if (['running', 'pending', 'processing'].includes(s)) status = 'running';
  else if (['failed', 'failure', 'denied', 'error'].includes(s)) status = 'error';
  else if (['completed', 'success', 'active', 'healthy'].includes(s)) status = 'success';
  return {
    id: raw.id,
    time: `${hh}:${mm}`,
    aiName: raw.actor || catLabel[raw.category] || raw.category,
    action: `[${catLabel[raw.category] || raw.category}] ${raw.action_summary}`,
    status,
  };
}
