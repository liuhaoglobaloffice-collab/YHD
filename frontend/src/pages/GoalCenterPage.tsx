import { useCallback, useEffect, useState } from 'react';
import { useI18n } from '../i18n';
import { getAuthToken } from '../services/auth';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

/** 统一注入 JWT（系统鉴权基于 Authorization 头，而非 cookie） */
function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

interface Goal {
  id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  kpi_name: string | null;
  kpi_target: number | null;
  kpi_current: number | null;
  kpi_unit: string | null;
  budget_total: number | null;
  budget_spent: number | null;
  progress_pct: number;
  plan_data: Record<string, unknown> | null;
  workflow_id: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

interface FailureRecord {
  id: number;
  goal_id: number | null;
  failure_category: string;
  failure_summary: string;
  failure_detail: string | null;
  retry_count: number;
  max_retries: number;
  strategy_action: string | null;
  strategy_detail: Record<string, unknown> | null;
  lesson_learned: string | null;
  is_successful: boolean | null;
  threshold_exceeded: boolean;
  boss_notified: boolean;
  boss_decision: string | null;
  created_at: string;
  resolved_at: string | null;
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'active': return '#4cc9f0';
    case 'completed': return '#00e676';
    case 'failed': return '#ff5252';
    case 'cancelled': return '#9e9e9e';
    default: return '#ffd740'; // draft
  }
}

function getPriorityLabel(priority: string): string {
  switch (priority) {
    case 'critical': return '紧急';
    case 'high': return '高';
    case 'normal': return '普通';
    case 'low': return '低';
    default: return priority;
  }
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    provider_error: 'Provider 错误',
    network_error: '网络错误',
    timeout: '超时',
    rate_limit: '频率限制',
    auth_error: '认证失败',
    agent_error: 'Agent 错误',
    business_logic_error: '业务逻辑错误',
    invalid_input: '无效输入',
    budget_exceeded: '预算超限',
    unknown: '未知错误',
  };
  return labels[category] || category;
}

function getStrategyLabel(action: string | null): string {
  const labels: Record<string, string> = {
    retry: '重试',
    switch_agent: '更换 Agent',
    switch_provider: '更换 Provider',
    adjust_params: '调整参数',
    change_approach: '更换方案',
    request_boss: '请求老板',
    abort: '终止',
  };
  return labels[action || ''] || action || '待确定';
}

export function GoalCenterPage() {
  const { t } = useI18n();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);
  const [goalFailures, setGoalFailures] = useState<FailureRecord[]>([]);
  const [tab, setTab] = useState<'goals' | 'failures'>('goals');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // 创建表单
  const [formTitle, setFormTitle] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formPriority, setFormPriority] = useState('normal');
  const [formKpiName, setFormKpiName] = useState('');
  const [formKpiTarget, setFormKpiTarget] = useState('');
  const [formKpiUnit, setFormKpiUnit] = useState('');
  const [formBudget, setFormBudget] = useState('');
  const [creating, setCreating] = useState(false);

  // P1-G1.1: 老板一句话创建目标（自然语言 → LLM/规则解析 → KPI/预算/时间）
  const [nlText, setNlText] = useState('');
  const [nlCreating, setNlCreating] = useState(false);
  const [parseInfo, setParseInfo] = useState<{
    parse_method: string;
    llm_error: string | null;
    extracted: {
      kpi_name: string | null;
      kpi_target: number | null;
      kpi_unit: string | null;
      budget_total: number | null;
      time_start: string | null;
      time_end: string | null;
      risk_boundaries: string[] | null;
    };
  } | null>(null);
  const [executingRecovery, setExecutingRecovery] = useState<number | null>(null);
  const [recoveryResult, setRecoveryResult] = useState<{recordId: number; success: boolean; message: string} | null>(null);

  const loadGoals = useCallback(async () => {
    try {
      setLoading(true);
      const url = `${API_BASE}/api/v1/goals${filterStatus ? `?status=${filterStatus}` : ''}`;
      const resp = await fetch(url, { headers: authHeaders() });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setGoals(data.items || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  const loadFailures = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/v1/goals/failures`, { headers: authHeaders() });
      if (!resp.ok) return;
      const data = await resp.json();
      setGoalFailures(data.items || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadGoals();
    loadFailures();
  }, [loadGoals, loadFailures]);

  const handleCreateFromText = async () => {
    if (!nlText.trim()) return;
    setNlCreating(true);
    setError(null);
    setParseInfo(null);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/goals/from-text`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ text: nlText.trim() }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `创建失败 (HTTP ${resp.status})`);
      }
      const data = await resp.json();
      setParseInfo(data.parse_info || null);
      setNlText('');
      await loadGoals();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setNlCreating(false);
    }
  };

  const handleCreate = async () => {
    if (!formTitle.trim()) return;
    setCreating(true);
    try {
      const body: Record<string, unknown> = {
        title: formTitle.trim(),
        description: formDesc.trim() || null,
        priority: formPriority,
      };
      if (formKpiName) body.kpi_name = formKpiName;
      if (formKpiTarget) body.kpi_target = parseFloat(formKpiTarget);
      if (formKpiUnit) body.kpi_unit = formKpiUnit;
      if (formBudget) body.budget_total = parseFloat(formBudget);

      const resp = await fetch(`${API_BASE}/api/v1/goals`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || '创建失败');
      }
      setShowCreate(false);
      setFormTitle('');
      setFormDesc('');
      setFormPriority('normal');
      setFormKpiName('');
      setFormKpiTarget('');
      setFormKpiUnit('');
      setFormBudget('');
      await loadGoals();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (goalId: number) => {
    try {
      const resp = await fetch(`${API_BASE}/api/v1/goals/${goalId}/activate`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || '激活失败');
      }
      await loadGoals();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleCancel = async (goalId: number) => {
    try {
      await fetch(`${API_BASE}/api/v1/goals/${goalId}/cancel`, {
        method: 'POST',
        headers: authHeaders(),
      });
      await loadGoals();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleSelectGoal = async (goal: Goal) => {
    setSelectedGoal(goal);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/goals/${goal.id}/failures`, { headers: authHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        setGoalFailures(data.items || []);
      }
    } catch { /* ignore */ }
  };

  const handleExecuteStrategy = async (recordId: number) => {
    setExecutingRecovery(recordId);
    setRecoveryResult(null);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/goals/failures/${recordId}/execute-strategy`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ context: {} }),
      });
      const data = await resp.json();
      setRecoveryResult({ recordId, success: data.success, message: data.message });
      // 刷新数据
      await loadGoals();
      await loadFailures();
      if (selectedGoal) {
        const fResp = await fetch(`${API_BASE}/api/v1/goals/${selectedGoal.id}/failures`, { headers: authHeaders() });
        if (fResp.ok) {
          const fData = await fResp.json();
          setGoalFailures(fData.items || []);
        }
      }
    } catch (e) {
      setRecoveryResult({ recordId, success: false, message: (e as Error).message });
    } finally {
      setExecutingRecovery(null);
    }
  };

  const handleDismissBoss = async (recordId: number, decision: string) => {
    try {
      await fetch(`${API_BASE}/api/v1/goals/failures/${recordId}/boss-decision`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ decision }),
      });
      await loadFailures();
    } catch { /* ignore */ }
  };

  const handleComplete = async (goalId: number) => {
    try {
      await fetch(`${API_BASE}/api/v1/goals/${goalId}/complete`, {
        method: 'POST',
        headers: authHeaders(),
      });
      await loadGoals();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div style={{ padding: '24px 32px', color: '#e0e0e0', fontFamily: 'monospace', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ color: '#4cc9f0', fontSize: 20, margin: 0 }}>老板目标中心</h1>
          <p style={{ color: '#888', fontSize: 12, marginTop: 4 }}>设定目标 → 自动分解 → 跟踪执行 → 失败恢复</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => { setTab('goals'); setShowCreate(false); }}
            style={{
              padding: '6px 16px', background: tab === 'goals' ? '#1a237e' : '#1e1e2e',
              border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, cursor: 'pointer', fontSize: 12,
            }}
          >
            目标列表
          </button>
          <button
            onClick={() => { setTab('failures'); loadFailures(); }}
            style={{
              padding: '6px 16px', background: tab === 'failures' ? '#1a237e' : '#1e1e2e',
              border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, cursor: 'pointer', fontSize: 12,
            }}
          >
            失败记录
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: '#2d1b1b', border: '1px solid #ff5252', color: '#ff8a80', padding: '8px 12px', borderRadius: 4, marginBottom: 16, fontSize: 12 }}>
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: 12, background: 'none', border: 'none', color: '#ff8a80', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* P1-G1.1: 老板一句话创建目标 */}
      <div style={{ background: '#1a1a2e', border: '1px solid #2a4a6a', borderRadius: 8, padding: 16, marginBottom: 16 }}>
        <h3 style={{ color: '#4cc9f0', fontSize: 13, margin: '0 0 6px 0' }}>一句话创建目标</h3>
        <p style={{ color: '#888', fontSize: 11, margin: '0 0 10px 0' }}>
          告诉鎏灏你的最终目标（如：30天开发美国市场，获取100个潜在客户，预算2000美元），系统自动提取 KPI、预算、时间与风险边界
        </p>
        <div style={{ display: 'flex', gap: 8 }}>
          <textarea
            value={nlText}
            onChange={e => setNlText(e.target.value)}
            rows={2}
            placeholder="例：帮我开发美国市场，30天内获取100个潜在客户，预算2000美元"
            style={{ flex: 1, padding: '8px 10px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12, resize: 'vertical' }}
          />
          <button
            onClick={handleCreateFromText}
            disabled={nlCreating || !nlText.trim()}
            style={{
              padding: '8px 18px', background: '#00695c', border: 'none', color: '#fff',
              borderRadius: 4, cursor: nlCreating || !nlText.trim() ? 'not-allowed' : 'pointer',
              fontSize: 12, opacity: nlCreating || !nlText.trim() ? 0.6 : 1, alignSelf: 'flex-start',
            }}
          >
            {nlCreating ? '解析中...' : 'AI 解析并创建'}
          </button>
        </div>
        {parseInfo && (
          <div style={{ marginTop: 10, padding: '8px 10px', background: '#0d0d1a', border: '1px solid #2a4a2a', borderRadius: 4, fontSize: 11 }}>
            <div style={{ marginBottom: 6 }}>
              <span style={{ color: '#66bb6a', fontWeight: 600 }}>
                解析方式: {parseInfo.parse_method === 'llm' ? 'LLM 理解' : '规则解析（LLM 未配置）'}
              </span>
              {parseInfo.llm_error && (
                <span style={{ color: '#facc15', marginLeft: 8 }}>({parseInfo.llm_error})</span>
              )}
            </div>
            <div style={{ color: '#aaa', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '2px 12px' }}>
              {parseInfo.extracted.kpi_name && <span>KPI: {parseInfo.extracted.kpi_name} = {parseInfo.extracted.kpi_target} {parseInfo.extracted.kpi_unit || ''}</span>}
              {parseInfo.extracted.budget_total != null && <span>预算: {parseInfo.extracted.budget_total} USD</span>}
              {parseInfo.extracted.time_start && <span>开始: {String(parseInfo.extracted.time_start).slice(0, 10)}</span>}
              {parseInfo.extracted.time_end && <span>截止: {String(parseInfo.extracted.time_end).slice(0, 10)}</span>}
              {parseInfo.extracted.risk_boundaries && parseInfo.extracted.risk_boundaries.length > 0 && (
                <span>风险边界: {parseInfo.extracted.risk_boundaries.slice(0, 3).join('；')}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {tab === 'goals' && (
        <>
          {/* 筛选和创建按钮 */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              style={{
                padding: '4px 8px', background: '#1e1e2e', border: '1px solid #333',
                color: '#e0e0e0', borderRadius: 4, fontSize: 12,
              }}
            >
              <option value="">全部状态</option>
              <option value="draft">草稿</option>
              <option value="active">执行中</option>
              <option value="completed">已完成</option>
              <option value="failed">失败</option>
              <option value="cancelled">已取消</option>
            </select>
            <button
              onClick={() => setShowCreate(true)}
              style={{
                padding: '6px 16px', background: '#0d47a1', border: 'none',
                color: '#fff', borderRadius: 4, cursor: 'pointer', fontSize: 12,
              }}
            >
              + 新目标
            </button>
          </div>

          {/* 创建表单 */}
          {showCreate && (
            <div style={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: 8, padding: 20, marginBottom: 16 }}>
              <h3 style={{ color: '#4cc9f0', fontSize: 14, margin: '0 0 16px 0' }}>创建新目标</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>目标标题 *</label>
                  <input value={formTitle} onChange={e => setFormTitle(e.target.value)}
                    style={{ width: '100%', padding: '6px 8px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12 }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>优先级</label>
                  <select value={formPriority} onChange={e => setFormPriority(e.target.value)}
                    style={{ width: '100%', padding: '6px 8px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12 }}>
                    <option value="low">低</option>
                    <option value="normal">普通</option>
                    <option value="high">高</option>
                    <option value="critical">紧急</option>
                  </select>
                </div>
                <div style={{ gridColumn: 'span 2' }}>
                  <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>描述</label>
                  <textarea value={formDesc} onChange={e => setFormDesc(e.target.value)} rows={2}
                    style={{ width: '100%', padding: '6px 8px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12, resize: 'vertical' }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>KPI 名称</label>
                  <input value={formKpiName} onChange={e => setFormKpiName(e.target.value)} placeholder="例: 月度销售额"
                    style={{ width: '100%', padding: '6px 8px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12 }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>KPI 目标值</label>
                  <input value={formKpiTarget} onChange={e => setFormKpiTarget(e.target.value)} type="number" placeholder="例: 100000"
                    style={{ width: '100%', padding: '6px 8px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12 }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>KPI 单位</label>
                  <input value={formKpiUnit} onChange={e => setFormKpiUnit(e.target.value)} placeholder="USD"
                    style={{ width: '100%', padding: '6px 8px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12 }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>总预算 (USD)</label>
                  <input value={formBudget} onChange={e => setFormBudget(e.target.value)} type="number" placeholder="5000"
                    style={{ width: '100%', padding: '6px 8px', background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, fontSize: 12 }} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                <button onClick={handleCreate} disabled={creating || !formTitle.trim()}
                  style={{
                    padding: '6px 20px', background: '#0d47a1', border: 'none', color: '#fff',
                    borderRadius: 4, cursor: creating || !formTitle.trim() ? 'not-allowed' : 'pointer', fontSize: 12, opacity: creating || !formTitle.trim() ? 0.6 : 1,
                  }}>
                  {creating ? '创建中...' : '创建目标'}
                </button>
                <button onClick={() => setShowCreate(false)}
                  style={{ padding: '6px 20px', background: '#333', border: 'none', color: '#e0e0e0', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
                  取消
                </button>
              </div>
            </div>
          )}

          {/* 目标列表 */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#666', fontSize: 12 }}>加载中...</div>
          ) : goals.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#666', fontSize: 12, border: '1px dashed #333', borderRadius: 8 }}>
              还没有目标。点击「+ 新目标」创建第一个目标。
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {goals.map(goal => (
                <div
                  key={goal.id}
                  onClick={() => handleSelectGoal(goal)}
                  style={{
                    background: selectedGoal?.id === goal.id ? '#1a1a2e' : '#12121e',
                    border: `1px solid ${selectedGoal?.id === goal.id ? '#4cc9f0' : '#2a2a3e'}`,
                    borderRadius: 8, padding: 16, cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <span style={{ color: '#e0e0e0', fontSize: 14, fontWeight: 600 }}>{goal.title}</span>
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: 10,
                          background: getStatusColor(goal.status), color: '#000', fontSize: 10, fontWeight: 600,
                        }}>
                          {goal.status === 'active' ? '执行中' : goal.status === 'draft' ? '草稿' : goal.status === 'completed' ? '已完成' : goal.status === 'failed' ? '失败' : '已取消'}
                        </span>
                        <span style={{ color: '#888', fontSize: 11 }}>P{getPriorityLabel(goal.priority)}</span>
                      </div>
                      {goal.description && <p style={{ color: '#888', fontSize: 11, margin: '0 0 8px 0' }}>{goal.description}</p>}
                      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#666' }}>
                        {goal.kpi_name && <span>KPI: {goal.kpi_name} ({goal.kpi_current ?? 0}/{goal.kpi_target ?? '-'} {goal.kpi_unit || ''})</span>}
                        {goal.budget_total != null && <span>预算: ${goal.budget_spent?.toFixed(0) ?? 0}/${goal.budget_total.toFixed(0)}</span>}
                        {goal.plan_data && <span>任务数: {(goal.plan_data as Record<string, unknown>).tasks?.length ?? 0}</span>}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', minWidth: 100 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end', marginBottom: 4 }}>
                        <span style={{ fontSize: 11, color: '#888' }}>{goal.progress_pct.toFixed(0)}%</span>
                      </div>
                      <div style={{ width: 100, height: 4, background: '#2a2a3e', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{
                          width: `${goal.progress_pct}%`, height: '100%',
                          background: getStatusColor(goal.status), borderRadius: 2,
                          transition: 'width 0.3s ease',
                        }} />
                      </div>
                      <div style={{ display: 'flex', gap: 4, marginTop: 8, justifyContent: 'flex-end' }}>
                        {goal.status === 'draft' && (
                          <button onClick={e => { e.stopPropagation(); handleActivate(goal.id); }}
                            style={{ padding: '3px 8px', background: '#0d47a1', border: 'none', color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10 }}>
                            激活
                          </button>
                        )}
                        {goal.status === 'active' && (
                          <button onClick={e => { e.stopPropagation(); handleComplete(goal.id); }}
                            style={{ padding: '3px 8px', background: '#1b5e20', border: 'none', color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10 }}>
                            完成
                          </button>
                        )}
                        {(goal.status === 'draft' || goal.status === 'active') && (
                          <button onClick={e => { e.stopPropagation(); handleCancel(goal.id); }}
                            style={{ padding: '3px 8px', background: '#b71c1c', border: 'none', color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10 }}>
                            取消
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 选中目标的详情 */}
          {selectedGoal && (
            <div style={{ marginTop: 24, background: '#1a1a2e', border: '1px solid #333', borderRadius: 8, padding: 20 }}>
              <h3 style={{ color: '#4cc9f0', fontSize: 14, margin: '0 0 12px 0' }}>
                执行计划 - {selectedGoal.title}
              </h3>
              {selectedGoal.plan_data ? (
                <div>
                  <p style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>
                    解析模式: {(selectedGoal.plan_data as Record<string, unknown>).execution_order as string} |
                    预估时长: {(selectedGoal.plan_data as Record<string, unknown>).estimated_duration_minutes as number} 分钟
                  </p>
                  <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #333' }}>
                        <th style={{ padding: '6px 8px', textAlign: 'left', color: '#888' }}>#</th>
                        <th style={{ padding: '6px 8px', textAlign: 'left', color: '#888' }}>任务</th>
                        <th style={{ padding: '6px 8px', textAlign: 'left', color: '#888' }}>Agent</th>
                        <th style={{ padding: '6px 8px', textAlign: 'right', color: '#888' }}>时长(分)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {((selectedGoal.plan_data as Record<string, unknown>).tasks as Array<Record<string, unknown>> || []).map((task, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #222' }}>
                          <td style={{ padding: '6px 8px', color: '#666' }}>{idx + 1}</td>
                          <td style={{ padding: '6px 8px', color: '#e0e0e0' }}>{task.name as string}</td>
                          <td style={{ padding: '6px 8px', color: '#4cc9f0' }}>{task.agent_type as string}</td>
                          <td style={{ padding: '6px 8px', textAlign: 'right', color: '#888' }}>{task.estimated_duration_minutes as number}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p style={{ fontSize: 12, color: '#666', fontStyle: 'italic' }}>尚未激活，激活后自动生成执行计划。</p>
              )}

              {/* 关联失败记录 */}
              {goalFailures.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ color: '#ff8a80', fontSize: 12, margin: '0 0 8px 0' }}>失败恢复记录 ({goalFailures.length})</h4>
                  {goalFailures.map(f => (
                    <div key={f.id} style={{ background: '#2d1b1b', border: '1px solid #442222', borderRadius: 4, padding: 8, marginBottom: 6, fontSize: 11 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ background: '#ff5252', color: '#fff', padding: '1px 6px', borderRadius: 3, fontSize: 10 }}>{getCategoryLabel(f.failure_category)}</span>
                        <span style={{ color: '#ff8a80' }}>{f.failure_summary}</span>
                        {f.is_successful === true && <span style={{ color: '#00e676', fontSize: 10 }}>已恢复 ✓</span>}
                        {f.is_successful === false && <span style={{ color: '#ff5252', fontSize: 10 }}>未恢复 ✗</span>}
                      </div>
                      <div style={{ color: '#888', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                        <span>重试: {f.retry_count}/{f.max_retries}</span>
                        <span>策略: {getStrategyLabel(f.strategy_action)}</span>
                        {f.threshold_exceeded && <span style={{ color: '#ff5252' }}>超阈值 ⚠</span>}
                        {f.boss_notified && <span style={{ color: '#ffd740' }}>已通知老板 ✓</span>}
                        {f.lesson_learned && <span>经验: {f.lesson_learned}</span>}
                        {f.failure_detail && <div style={{ width: '100%', color: '#666', marginTop: 2, fontSize: 10 }}>{f.failure_detail.slice(0, 200)}</div>}
                      </div>
                      {/* 策略执行按钮 */}
                      {f.is_successful === null && (
                        <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                          <button
                            onClick={e => { e.stopPropagation(); handleExecuteStrategy(f.id); }}
                            disabled={executingRecovery === f.id}
                            style={{
                              padding: '3px 8px', background: '#0d47a1', border: 'none',
                              color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10,
                              opacity: executingRecovery === f.id ? 0.6 : 1,
                            }}
                          >
                            {executingRecovery === f.id ? '执行中...' : '执行策略'}
                          </button>
                          {recoveryResult && recoveryResult.recordId === f.id && (
                            <span style={{ color: recoveryResult.success ? '#00e676' : '#ff5252', fontSize: 10, padding: '3px 0' }}>
                              {recoveryResult.message}
                            </span>
                          )}
                        </div>
                      )}
                      {/* 老板决策输入 */}
                      {f.boss_notified && !f.boss_decision && (
                        <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                          <button onClick={e => { e.stopPropagation(); handleDismissBoss(f.id, 'continue'); }}
                            style={{ padding: '3px 8px', background: '#1b5e20', border: 'none', color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10 }}>
                            继续执行
                          </button>
                          <button onClick={e => { e.stopPropagation(); handleDismissBoss(f.id, 'abort'); }}
                            style={{ padding: '3px 8px', background: '#b71c1c', border: 'none', color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10 }}>
                            终止
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {tab === 'failures' && (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <span style={{ color: '#888', fontSize: 12, padding: '6px 0' }}>全局失败记录 ({goalFailures.length})</span>
          </div>
          {goalFailures.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#666', fontSize: 12, border: '1px dashed #333', borderRadius: 8 }}>
              暂无失败记录。
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 8 }}>
              {goalFailures.map(f => (
                <div key={f.id} style={{ background: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: 6, padding: 12 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ background: '#ff5252', color: '#fff', padding: '2px 8px', borderRadius: 3, fontSize: 10 }}>{getCategoryLabel(f.failure_category)}</span>
                    <span style={{ color: '#e0e0e0', fontSize: 12 }}>{f.failure_summary}</span>
                    {f.is_successful === true && <span style={{ color: '#00e676', fontSize: 10 }}>已恢复 ✓</span>}
                    {f.is_successful === false && <span style={{ color: '#ff5252', fontSize: 10 }}>未恢复 ✗</span>}
                  </div>
                  <div style={{ color: '#888', fontSize: 11, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    <span>重试: {f.retry_count}/{f.max_retries}</span>
                    <span>策略: {getStrategyLabel(f.strategy_action)}</span>
                    {f.threshold_exceeded && <span style={{ color: '#ff5252' }}>超阈值 ⚠</span>}
                    {f.boss_notified && <span style={{ color: '#ffd740' }}>已通知老板 ✓</span>}
                    {f.boss_decision && <span>老板决策: {f.boss_decision}</span>}
                    {f.lesson_learned && <span>经验: {f.lesson_learned}</span>}
                    {f.is_successful !== null && <span>{f.is_successful ? '已恢复' : '未恢复'}</span>}
                    <span style={{ color: '#555' }}>{new Date(f.created_at).toLocaleString('zh-CN')}</span>
                  </div>
                  {f.failure_detail && (
                    <div style={{ color: '#666', fontSize: 10, marginTop: 4 }}>{f.failure_detail.slice(0, 200)}</div>
                  )}
                  {/* 策略执行按钮 */}
                  {f.is_successful === null && (
                    <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                      <button
                        onClick={() => handleExecuteStrategy(f.id)}
                        disabled={executingRecovery === f.id}
                        style={{
                          padding: '3px 8px', background: '#0d47a1', border: 'none',
                          color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10,
                          opacity: executingRecovery === f.id ? 0.6 : 1,
                        }}
                      >
                        {executingRecovery === f.id ? '执行中...' : '执行策略'}
                      </button>
                      {recoveryResult && recoveryResult.recordId === f.id && (
                        <span style={{ color: recoveryResult.success ? '#00e676' : '#ff5252', fontSize: 10, padding: '3px 0' }}>
                          {recoveryResult.message}
                        </span>
                      )}
                      {/* 老板决策输入 */}
                      {f.boss_notified && !f.boss_decision && (
                        <>
                          <button onClick={() => handleDismissBoss(f.id, 'continue')}
                            style={{ padding: '3px 8px', background: '#1b5e20', border: 'none', color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10 }}>
                            继续
                          </button>
                          <button onClick={() => handleDismissBoss(f.id, 'abort')}
                            style={{ padding: '3px 8px', background: '#b71c1c', border: 'none', color: '#fff', borderRadius: 3, cursor: 'pointer', fontSize: 10 }}>
                            终止
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}