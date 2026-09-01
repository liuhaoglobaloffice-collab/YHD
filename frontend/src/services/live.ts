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

// ============================================================
// AI Core（AI 总控）状态机 —— 全站统一的 AI 运行状态派生
// 数据源：/dashboard/live-activity（真实数据库记录，绝不伪造）
// 状态优先级：执行中 > 异常 > 等待审批 > 已完成 > 待机
// ============================================================

/** AI Core 状态码（与 AIWorkStatus 的 AIStatus 结构一致，可直接喂给 AIStatusDot） */
export type AICoreStatus = 'working' | 'error' | 'waiting' | 'completed' | 'idle' | 'offline';

export interface AICoreState {
  status: AICoreStatus;
  /** 状态标签，如「执行中 · 2 项任务」 */
  label: string;
  /** AI 当前正在做什么（第一条执行中任务的描述，无则为空） */
  detail: string;
}

/**
 * 从真实实时数据派生 AI Core 运行状态。
 * - working        执行中：有任务/工作流正在运行
 * - error          异常：存在失败任务且当前无任务执行
 * - waiting        等待审批：存在阻塞任务待人工处理
 * - completed      已完成：今日有完成任务且当前无执行/异常/阻塞
 * - idle           待机：一切平静，AI 员工就绪
 * - offline        离线：API 不可达（live 为 null）
 */
export function deriveAICoreState(live: LiveActivity | null | undefined): AICoreState {
  if (!live) return { status: 'offline', label: '连接中断', detail: '' };

  const working = live.working_now?.length ?? 0;
  const failed = live.failed_tasks ?? 0;
  const blocked = live.blocked_tasks ?? 0;
  const doneToday = live.today?.completed ?? 0;

  if (working > 0) {
    const first = live.working_now?.[0];
    return {
      status: 'working',
      label: `执行中 · ${working} 项任务`,
      detail: first
        ? `${first.kind === 'workflow' ? first.workflow_name || '工作流' : first.employee_name || 'AI 员工'}：${first.title}`
        : '',
    };
  }
  if (failed > 0) {
    const failedTask = live.recent_tasks?.find((t) => t.status === 'failed');
    return {
      status: 'error',
      label: `异常 · ${failed} 个任务失败`,
      detail: failedTask ? `失败：${failedTask.title}${failedTask.error ? `（${failedTask.error}）` : ''}` : '',
    };
  }
  if (blocked > 0) {
    return {
      status: 'waiting',
      label: `等待审批 · ${blocked} 项`,
      detail: '存在被阻塞的任务，需要人工处理',
    };
  }
  if (doneToday > 0) {
    const lastDone = live.recent_tasks?.find((t) => t.status === 'completed');
    return {
      status: 'completed',
      label: `今日已完成 ${doneToday} 项`,
      detail: lastDone ? `最近完成：${lastDone.title}` : '',
    };
  }
  return {
    status: 'idle',
    label: `待机 · ${live.active_employees} 名 AI 在线`,
    detail: 'AI 员工在线，可前往目标中心下发任务',
  };
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
