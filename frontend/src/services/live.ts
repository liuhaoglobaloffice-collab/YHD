/**
 * Live Activity — 全站「AI 正在工作」实时活动源（Y1.0）。
 *
 * 单一聚合接口 /dashboard/live-activity，供 Layout 全局状态条与各页面消费。
 * 所有数据均来自后端数据库真实记录（员工状态/任务执行/工作流/目标/模型调用/知识记忆/审计）。
 */

const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('liuhao_auth_token') ?? '';
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export interface LiveEmployee {
  id: string;
  name: string;
  position: string | null;
  department: string | null;
  status: string; // active / created / suspended / retired
  provider: string | null;
  model: string | null;
}

export interface LiveTask {
  id: string;
  title: string;
  status: string;
  updated_at: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  summary: string;
  error: string | null;
  employee_id?: string | null;
  employee_name: string | null;
  provider?: string | null;
  model?: string | null;
  workflow_id?: string | null;
  workflow_name?: string | null;
  goal_id?: number | null;
  goal_title?: string | null;
}

/** 「AI 正在工作」：运行中的任务 / 工作流（真实 Execution 数据）。 */
export interface LiveWorkingItem {
  kind: 'task' | 'workflow';
  id: string;
  title: string;
  status: string;
  employee_id?: string | null;
  employee_name?: string | null;
  position?: string | null;
  provider?: string | null;
  model?: string | null;
  goal_id?: number | null;
  goal_title?: string | null;
  goal_progress?: number | null;
  workflow_id?: string | null;
  workflow_name?: string | null;
  execution_id?: string;
  current_step?: string | null;
  /** 真实进度百分比；null 表示后端未记录进度，前端必须显示不确定态，不得伪造。 */
  progress?: number | null;
  started_at?: string | null;
}

/** 「AI CEO 建议」：全部由真实信号派生。 */
export interface LiveRecommendation {
  id: string;
  type: string;
  priority: 'high' | 'medium' | 'low';
  title: string;
  problem: string;
  impact: string;
  analysis: string;
  suggestion: string;
  action_label: string;
  action_url: string;
  created_at: string;
}

export interface LiveWorkflow {
  execution_id: string;
  workflow_id?: string | null;
  workflow_name?: string | null;
  status: string;
  started_at: string | null;
  completed_at?: string | null;
  error: string | null;
  goal_id?: number | null;
  goal_title?: string | null;
}

export interface LiveGoal {
  id: number;
  title: string;
  status: string;
  progress_pct: number;
  kpi_name: string | null;
  kpi_current: number | null;
  kpi_target: number | null;
  budget_total: number | null;
  budget_spent: number | null;
}

export interface LiveModelCall {
  provider: string | null;
  model: string | null;
  total_tokens: number | null;
  status: string | null;
  created_at: string | null;
}

export interface LiveMemoryItem {
  agent_name: string;
  role: string | null;
  excerpt: string;
  created_at: string | null;
}

export interface LiveAuditItem {
  action: string;
  resource_type: string | null;
  status: string | null;
  created_at: string | null;
}

export interface LiveActivity {
  server_time: string;
  employees: LiveEmployee[];
  active_employees: number;
  total_employees: number;
  running_tasks: number;
  blocked_tasks?: number;
  failed_tasks?: number;
  today?: { completed: number; failed: number };
  working_now?: LiveWorkingItem[];
  recommendations?: LiveRecommendation[];
  recent_tasks: LiveTask[];
  workflows: LiveWorkflow[];
  goals: LiveGoal[];
  model_calls: LiveModelCall[];
  knowledge: { documents: number; memory_activity: LiveMemoryItem[] };
  audit_activity: LiveAuditItem[];
}

export async function fetchLiveActivity(limit = 12): Promise<LiveActivity> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/dashboard/live-activity?limit=${limit}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch live activity: ${res.status}`);
  return res.json();
}

/** 把实时数据压缩成状态条的一句话摘要。 */
export function summarizeActivity(live: LiveActivity): {
  headline: string;
  detail: string;
  tone: 'working' | 'idle' | 'error';
} {
  const lastTask = live.recent_tasks?.[0];
  const lastWf = live.workflows?.[0];
  const failedTask = live.recent_tasks?.find((t) => t.status === 'failed');

  if (live.running_tasks > 0) {
    return {
      headline: `${live.active_employees} 名 AI 员工在岗 · ${live.running_tasks} 个任务执行中`,
      detail: lastTask ? `正在执行：${lastTask.title}` : '',
      tone: 'working',
    };
  }
  if (lastWf?.status === 'COMPLETED' || lastTask?.status === 'completed') {
    const doneGoal = live.goals?.find((g) => g.status === 'completed');
    return {
      headline: `${live.active_employees} 名 AI 员工在岗 · 最近任务已完成`,
      detail: doneGoal
        ? `目标「${doneGoal.title}」进度 ${doneGoal.progress_pct}%${
            doneGoal.kpi_current != null && doneGoal.kpi_target
              ? ` · KPI ${doneGoal.kpi_current}/${doneGoal.kpi_target}`
              : ''
          }`
        : lastTask?.title
          ? `已完成：${lastTask.title}`
          : '',
      tone: 'working',
    };
  }
  if (failedTask) {
    return {
      headline: `${live.active_employees} 名 AI 员工在岗 · 最近任务失败`,
      detail: failedTask.error || `失败任务：${failedTask.title}`,
      tone: 'error',
    };
  }
  return {
    headline: `${live.active_employees} 名 AI 员工在岗 · 等待任务`,
    detail: lastTask?.title ? `最近执行：${lastTask.title}` : '',
    tone: 'idle',
  };
}
