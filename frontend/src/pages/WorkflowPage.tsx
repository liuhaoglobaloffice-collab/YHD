import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { fetchWorkflows, Workflow } from '../services/workflows';
import { useI18n } from '../i18n';
import { AIWorkStatus, type AIStatus } from '../components/AIWorkStatus';
import { AIActivityFeed, type ActivityItem } from '../components/AIActivityFeed';
import { AIEmptyState } from '../components/AIEmptyState';
import {
  fetchTradeTemplates,
  fetchTradeTemplate,
  instantiateTradeTemplate,
  type TradeTemplate,
  type InstantiateResult,
} from '../services/trade';
import {
  fetchLiveActivity,
  type LiveActivity,
  type LiveTask,
  type LiveWorkflow,
} from '../services/live';

const statusLabels: Record<string, string> = {
  active: '运行中', inactive: '已停止', draft: '草稿',
  published: '已发布', archived: '已归档',
};

const statusColors: Record<string, string> = {
  active: '#4ade80', inactive: '#8fa0e0', draft: '#facc15',
  published: '#4cc9f0', archived: '#666',
};

const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

const CATEGORY_LABELS: Record<string, string> = {
  customer_dev: '客户开发', supplier_procurement: '供应商采购', deal_closure: '报价成交',
};

/** 任务/执行状态 → 颜色/文案/图标（真实状态，无伪造） */
function execStatusMeta(status: string): { color: string; label: string; icon: string } {
  const s = (status || '').toLowerCase();
  if (s === 'completed' || s === 'success')
    return { color: '#4ade80', label: '已完成', icon: '🟢' };
  if (s === 'failed' || s === 'failure' || s === 'error')
    return { color: '#ff6b6b', label: '失败', icon: '🔴' };
  if (s === 'running' || s === 'processing')
    return { color: '#4cc9f0', label: '执行中', icon: '🔵' };
  if (s === 'blocked') return { color: '#facc15', label: '阻塞', icon: '🟡' };
  if (s === 'pending' || s === 'queued')
    return { color: '#facc15', label: '等待中', icon: '🟡' };
  if (s === 'cancelled' || s === 'canceled')
    return { color: 'rgba(255,255,255,0.45)', label: '已取消', icon: '⚪' };
  return { color: 'rgba(255,255,255,0.55)', label: status || '未知', icon: '⚪' };
}

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  const diff = Date.now() - d.getTime();
  if (Number.isNaN(diff)) return '';
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return '刚刚';
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  return `${Math.floor(hr / 24)} 天前`;
}

function fullTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('zh-CN', { hour12: false });
}

export function WorkflowPage() {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [templates, setTemplates] = useState<TradeTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [apiError, setApiError] = useState(false);

  // 真实执行记录（DB 持久化，来自 /dashboard/live-activity）
  const [live, setLive] = useState<LiveActivity | null>(null);
  const [detailTask, setDetailTask] = useState<LiveTask | null>(null);
  const [detailWf, setDetailWf] = useState<LiveWorkflow | null>(null);

  // 模板执行
  const [execTemplate, setExecTemplate] = useState<TradeTemplate | null>(null);
  const [execInputs, setExecInputs] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState<InstantiateResult | null>(null);
  const [execError, setExecError] = useState('');

  useEffect(() => {
    Promise.all([loadWorkflows(), loadTemplates(), loadLive()]);
  }, []);

  // 从驾驶舱跳转：?task=<id> 打开任务执行详情；?execution=<id> 打开工作流执行详情
  useEffect(() => {
    if (!live) return;
    const taskId = searchParams.get('task');
    const executionId = searchParams.get('execution');
    if (taskId) {
      const task = live.recent_tasks?.find((x) => x.id === taskId);
      if (task) setDetailTask(task);
    } else if (executionId) {
      const wf = live.workflows?.find((x) => x.execution_id === executionId);
      if (wf) setDetailWf(wf);
    }
    // 仅在 live 首次到达时处理一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live]);

  const closeDetail = () => {
    setDetailTask(null);
    setDetailWf(null);
    if (searchParams.has('task') || searchParams.has('execution')) {
      setSearchParams({}, { replace: true });
    }
  };

  const loadLive = async () => {
    try {
      const data = await fetchLiveActivity(30);
      setLive(data);
    } catch (e) {
      // 执行记录为增强信息，失败不阻塞页面主体
      console.error('Failed to load live executions', e);
    }
  };

  const loadWorkflows = async () => {
    try {
      const data = await fetchWorkflows();
      setWorkflows(data);
      setApiError(false);
    } catch (e) {
      console.error('Failed to load workflows', e);
      setError('加载工作流列表失败');
      setApiError(true);
    }
  };

  const loadTemplates = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}${API_PREFIX}/workflows/trade-templates`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setTemplates(data.items ?? []);
      }
    } catch (e) {
      console.error('Failed to load trade templates', e);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <section className="page">
        <h1>AI 工作流中心</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  // API 错误：显示 AI 诊断 + 重试
  if (apiError) {
    return (
      <section className="page">
        <h1>AI 工作流中心</h1>
        <AIEmptyState
          isError
          errorMessage={error}
          onRetry={() => { setLoading(true); setApiError(false); Promise.all([loadWorkflows(), loadTemplates()]); }}
        />
      </section>
    );
  }

  // 真实工作流执行活动（来自 DB 的 workflow_executions，非演示推导）
  const realActivities: ActivityItem[] = (live?.workflows ?? []).map((wf) => {
    const s = (wf.status || '').toLowerCase();
    const status: ActivityItem['status'] =
      s === 'completed' || s === 'success'
        ? 'success'
        : s === 'failed' || s === 'failure'
          ? 'failed'
          : s === 'running' || s === 'processing'
            ? 'running'
            : 'pending';
    const actionText =
      status === 'success'
        ? '工作流执行完成'
        : status === 'failed'
          ? `工作流执行失败${wf.error ? `：${wf.error.slice(0, 40)}` : ''}`
          : status === 'running'
            ? '工作流执行中'
            : '工作流等待执行';
    const d = new Date(wf.completed_at || wf.started_at || '');
    return {
      id: `wf-exec-${wf.execution_id}`,
      time: wf.completed_at || wf.started_at
        ? d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        : '--:--',
      aiName: wf.workflow_name || '工作流引擎',
      action: wf.goal_title ? `${actionText}（目标：${wf.goal_title}）` : actionText,
      status,
    };
  });

  // 最近 AI 任务执行（DB 持久化，驾驶舱「最近 AI 执行」同源数据）
  const recentExecutions: LiveTask[] = live?.recent_tasks ?? [];

  return (
    <>
    <section className="page">
      <h1>AI 工作流中心</h1>

      {/* 工作流统计 */}
      <div className="grid" style={{ marginBottom: 20 }}>
        <div className="card" style={{ borderLeft: '3px solid #4ade80' }}>
          <div className="cost-label">运行中</div>
          <div className="cost-value" style={{ color: '#4ade80' }}>{workflows.filter(w => w.status === 'active').length}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #8fa0e0' }}>
          <div className="cost-label">已停止</div>
          <div className="cost-value" style={{ color: '#8fa0e0' }}>{workflows.filter(w => w.status === 'inactive').length}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #facc15' }}>
          <div className="cost-label">草稿</div>
          <div className="cost-value" style={{ color: '#facc15' }}>{workflows.filter(w => w.status === 'draft').length}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #4cc9f0' }}>
          <div className="cost-label">模板</div>
          <div className="cost-value" style={{ color: '#4cc9f0' }}>{templates.length}</div>
        </div>
      </div>

      {/* 最近 AI 执行（DB 真实记录；点击行查看执行详情） */}
      <div className="import-panel" style={{ marginBottom: 20 }}>
        <div className="executions-header">
          <strong>最近 AI 执行</strong>
          <span className="executions-count">{recentExecutions.length} 条</span>
        </div>
        {recentExecutions.length === 0 ? (
          <p className="card-desc" style={{ marginTop: 8 }}>
            暂无 AI 执行记录。AI 员工执行任务后，结果会实时出现在这里。
          </p>
        ) : (
          <div style={{ marginTop: 8 }}>
            {recentExecutions.slice(0, 10).map((task) => {
              const meta = execStatusMeta(task.status);
              return (
                <div
                  key={task.id}
                  onClick={() => setDetailTask(task)}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 10,
                    padding: '10px 8px', borderRadius: 8, cursor: 'pointer',
                    borderBottom: '1px solid rgba(110,130,255,0.1)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(76,201,240,0.06)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ fontSize: 14, marginTop: 2 }}>{meta.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13 }}>
                      <strong style={{ color: '#dce9ff' }}>{task.employee_name || 'AI 员工'}</strong>
                      <span style={{ color: 'rgba(255,255,255,0.8)' }}> · {task.title}</span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                      {task.goal_title && (
                        <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: 'rgba(123,97,255,0.12)', border: '1px solid rgba(123,97,255,0.35)', color: '#c3b4ff' }}>
                          🎯 {task.goal_title}
                        </span>
                      )}
                      {task.workflow_name && (
                        <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: 'rgba(76,201,240,0.1)', border: '1px solid rgba(76,201,240,0.25)', color: '#9fdcff' }}>
                          🔗 {task.workflow_name}
                        </span>
                      )}
                      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, color: meta.color, border: `1px solid ${meta.color}55`, background: `${meta.color}14` }}>
                        {meta.label}
                      </span>
                    </div>
                    {task.status === 'failed' && task.error ? (
                      <div style={{ fontSize: 12, color: '#ff9d9d', marginTop: 3 }}>⚠ {task.error}</div>
                    ) : task.summary ? (
                      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        📄 {task.summary}
                      </div>
                    ) : null}
                  </div>
                  <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap' }}>
                    {timeAgo(task.completed_at || task.updated_at)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 左侧：外贸业务模板 + 工作流列表 / 右侧：活动时间线 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16, marginBottom: 20 }}>
        <div>
          {/* 外贸业务模板 */}
          {templates.length > 0 && (
            <div className="import-panel" style={{ marginBottom: 16 }}>
              <div className="executions-header">
                <strong>外贸业务模板</strong>
                <span className="executions-count">{templates.length} 个</span>
              </div>
              <p className="card-desc">一键启动外贸业务流程，AI 自动串行执行各步骤</p>
              <div className="market-grid" style={{ marginTop: 12 }}>
                {templates.map((tpl) => (
                  <div key={tpl.template_id} className="market-card" style={{ borderTop: `3px solid ${tpl.color}` }}>
                    <strong style={{ fontSize: 16 }}>{tpl.name}</strong>
                    <p className="card-desc" style={{ marginTop: 4 }}>{tpl.description}</p>
                    {/* 工作流步骤链 */}
                    <div className="workflow-chain" style={{ marginTop: 8 }}>
                      {tpl.steps.map((s, idx) => (
                        <span key={idx} className="workflow-chain-step">
                          <span className="workflow-chain-dot" style={{ background: tpl.color }} />
                          <span className="workflow-chain-name">{s.name}</span>
                          {idx < tpl.steps.length - 1 && <span className="workflow-chain-arrow">→</span>}
                        </span>
                      ))}
                    </div>
                    <div className="card-meta" style={{ marginTop: 8 }}>
                      <span>⏱ 约 {tpl.estimated_total_minutes} 分钟</span>
                      <span className="lead-badge">{CATEGORY_LABELS[tpl.category] ?? tpl.category}</span>
                    </div>
                    <button
                      className="btn btn-submit"
                      style={{ marginTop: 12, width: '100%' }}
                      onClick={() => {
                        setExecTemplate(tpl);
                        setExecInputs({});
                        setExecResult(null);
                        setExecError('');
                      }}
                    >
                      启动流程
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 已有工作流列表 */}
          <div className="import-panel">
            <div className="executions-header">
              <strong>已有工作流</strong>
              <span className="executions-count">{workflows.length} 个</span>
            </div>

            {workflows.length === 0 ? (
              <AIEmptyState
                title="AI 工作流引擎已就绪"
                description="等待创建第一个工作流。可以手动创建，或让 AI 为您生成。"
                aiStatus="waiting"
                availableTasks={['手动创建工作流', '使用外贸业务模板', 'AI 自动生成工作流']}
                nextStep="建议先使用外贸业务模板快速启动"
                actionLabel="+ 创建工作流"
                onAction={() => alert('创建工作流（开发中）')}
              />
            ) : (
              <div className="grid" style={{ marginTop: 12 }}>
                {workflows.map((wf) => (
                  <div key={wf.id} className="card" style={{ borderLeft: `3px solid ${statusColors[wf.status] ?? '#666'}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <strong>{wf.name}</strong>
                      <span className="ai-status-badge" style={{ color: statusColors[wf.status] ?? '#666', background: `${statusColors[wf.status] ?? '#666'}15`, fontSize: 10 }}>
                        {statusLabels[wf.status] ?? wf.status}
                      </span>
                    </div>
                    <p className="card-desc">{wf.description || '暂无描述'}</p>
                    <div className="card-meta">
                      创建于 {wf.created_at ? new Date(wf.created_at).toLocaleString('zh-CN') : 'N/A'}
                    </div>
                    <div className="sub-actions" style={{ marginTop: 8 }}>
                      <button className="btn btn-sm btn-submit" disabled={wf.status !== 'active'}>执行</button>
                      <button className="btn btn-sm">查看</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 右侧：AI 工作流活动（真实执行记录） */}
        <div>
          <AIActivityFeed
            activities={realActivities}
            title="工作流执行活动"
            maxItems={8}
            emptyMessage="暂无工作流执行记录"
          />
          {(live?.workflows ?? []).length > 0 && (
            <div className="card" style={{ marginTop: 12, padding: 12 }}>
              <div className="cost-label" style={{ marginBottom: 8 }}>执行记录</div>
              {(live?.workflows ?? []).slice(0, 5).map((wf) => {
                const meta = execStatusMeta(wf.status);
                return (
                  <div
                    key={wf.execution_id}
                    onClick={() => setDetailWf(wf)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '6px 4px',
                      cursor: 'pointer', borderRadius: 6, fontSize: 12,
                      color: 'rgba(255,255,255,0.75)',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(76,201,240,0.06)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <span>{meta.icon}</span>
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {wf.workflow_name || '工作流执行'}
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap' }}>
                      {timeAgo(wf.completed_at || wf.started_at)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* AI 生成工作流 */}
          <div className="card" style={{ marginTop: 16, borderLeft: '3px solid #4cc9f0' }}>
            <div className="cost-label" style={{ marginBottom: 8 }}>🤖 AI 生成工作流</div>
            <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', lineHeight: 1.6 }}>
              描述你的业务需求，AI 将自动生成完整的工作流定义。
            </p>
            <button className="btn btn-submit" style={{ width: '100%' }} onClick={() => alert('AI 生成工作流（开发中）')}>
              AI 生成工作流
            </button>
          </div>
        </div>
      </div>
      </section>

      {/* 模板执行弹窗 */}
      {execTemplate && (
        <div className="modal-overlay" onClick={() => { if (!executing) setExecTemplate(null); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600 }}>
            <h2 style={{ color: execTemplate.color }}>{execTemplate.name}</h2>
            <p className="card-desc">{execTemplate.description}</p>

            {execResult ? (
              /* 执行结果 */
              <div>
                <div className="executions-header">
                  <strong>执行结果</strong>
                  <span className={`lead-badge ${execResult.status === 'completed' ? 'ok' : 'off'}`}>
                    {execResult.status === 'completed' ? '✅ 完成' : '❌ 失败'}
                  </span>
                </div>
                <div style={{ marginTop: 12 }}>
                  <div className="cost-label">执行步骤</div>
                  {execResult.steps.map((step, i) => (
                    <div key={i} className="card" style={{ marginTop: 8, padding: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <strong style={{ fontSize: 13 }}>{step.name}</strong>
                        <span className="execution-time" style={{ fontSize: 11 }}>
                          {step.result?.status === 'completed' ? '✅' : step.result?.status === 'pending_approval' ? '⏳' : '⬜'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
                        {Object.entries(step.result || {}).map(([k, v]) => (
                          <div key={k}>{k}: {String(v)}</div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="modal-actions" style={{ marginTop: 16 }}>
                  <button className="btn btn-submit" onClick={() => setExecTemplate(null)}>
                    完成
                  </button>
                </div>
              </div>
            ) : (
              /* 输入表单 */
              <div>
                {execError && <p className="error-text">{execError}</p>}

                <div style={{ marginTop: 12 }}>
                  <div className="cost-label">流程步骤</div>
                  <div className="workflow-chain" style={{ marginTop: 8, flexWrap: 'wrap' }}>
                    {execTemplate.steps.map((s, idx) => (
                      <span key={idx} className="workflow-chain-step">
                        <span className="workflow-chain-dot" style={{ background: execTemplate.color }} />
                        <span className="workflow-chain-name">{s.name}</span>
                        {idx < execTemplate.steps.length - 1 && <span className="workflow-chain-arrow">→</span>}
                      </span>
                    ))}
                  </div>
                </div>

                {/* 输入参数 */}
                {execTemplate.inputs && execTemplate.inputs.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <div className="cost-label">输入参数</div>
                    {execTemplate.inputs.map((input) => (
                      <div className="form-group" key={input.key} style={{ marginTop: 8 }}>
                        <label>
                          {input.label}
                          {input.required && <span style={{ color: '#ff4444' }}> *</span>}
                        </label>
                        {input.type === 'multi_select' ? (
                          <select
                            value={execInputs[input.key] ?? ''}
                            onChange={(e) => setExecInputs({ ...execInputs, [input.key]: e.target.value })}
                          >
                            <option value="">{input.placeholder || `选择${input.label}`}</option>
                            {(input.options || []).map((opt) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        ) : input.type === 'lang_select' ? (
                          <select
                            value={execInputs[input.key] ?? 'en'}
                            onChange={(e) => setExecInputs({ ...execInputs, [input.key]: e.target.value })}
                          >
                            <option value="en">English</option>
                            <option value="zh">中文</option>
                            <option value="es">Español</option>
                            <option value="ar">العربية</option>
                          </select>
                        ) : (
                          <input
                            value={execInputs[input.key] ?? ''}
                            onChange={(e) => setExecInputs({ ...execInputs, [input.key]: e.target.value })}
                            placeholder={input.placeholder || `输入${input.label}`}
                            type={input.type === 'number' ? 'number' : 'text'}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div className="modal-actions" style={{ marginTop: 16 }}>
                  <button className="btn btn-cancel" onClick={() => setExecTemplate(null)} disabled={executing}>
                    取消
                  </button>
                  <button
                    className="btn btn-submit"
                    onClick={async () => {
                      setExecuting(true);
                      setExecError('');
                      try {
                        const result = await instantiateTradeTemplate(execTemplate.template_id, execInputs);
                        setExecResult(result);
                      } catch (e) {
                        setExecError(e instanceof Error ? e.message : '执行失败');
                      }
                      setExecuting(false);
                    }}
                    disabled={executing}
                  >
                    {executing ? '执行中...' : `⏱ 启动（约 ${execTemplate.estimated_total_minutes} 分钟）`}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 执行详情弹窗（任务 / 工作流执行，全部为真实 DB 数据） */}
      {(detailTask || detailWf) && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 620 }}>
            {detailTask && (() => {
              const meta = execStatusMeta(detailTask.status);
              return (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                    <h2 style={{ margin: 0, fontSize: 17 }}>
                      {meta.icon} 任务执行详情
                    </h2>
                    <span style={{ fontSize: 12, padding: '3px 12px', borderRadius: 999, color: meta.color, background: `${meta.color}18`, border: `1px solid ${meta.color}55`, fontWeight: 700 }}>
                      {meta.label}
                    </span>
                  </div>
                  <p className="card-desc" style={{ marginTop: 8, fontSize: 14, color: '#dce9ff' }}>
                    {detailTask.title}
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 12, fontSize: 13 }}>
                    <div><span style={{ color: 'rgba(255,255,255,0.5)' }}>执行员工：</span>{detailTask.employee_name || '—'}</div>
                    <div><span style={{ color: 'rgba(255,255,255,0.5)' }}>Provider：</span>{detailTask.provider || '—'}{detailTask.model ? ` · ${detailTask.model}` : ''}</div>
                    <div style={{ gridColumn: '1 / -1' }}><span style={{ color: 'rgba(255,255,255,0.5)' }}>所属目标：</span>{detailTask.goal_title || '—'}</div>
                    <div style={{ gridColumn: '1 / -1' }}><span style={{ color: 'rgba(255,255,255,0.5)' }}>所属工作流：</span>{detailTask.workflow_name || '—'}</div>
                    <div><span style={{ color: 'rgba(255,255,255,0.5)' }}>开始时间：</span>{fullTime(detailTask.started_at || detailTask.updated_at)}</div>
                    <div><span style={{ color: 'rgba(255,255,255,0.5)' }}>完成时间：</span>{fullTime(detailTask.completed_at)}</div>
                  </div>
                  {detailTask.status === 'failed' && detailTask.error && (
                    <div className="card" style={{ marginTop: 12, padding: 10, borderLeft: '3px solid #ff6b6b' }}>
                      <div className="cost-label" style={{ color: '#ff9d9d' }}>失败原因</div>
                      <div style={{ fontSize: 13, color: '#ffb3b3', marginTop: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {detailTask.error}
                      </div>
                    </div>
                  )}
                  {detailTask.summary && (
                    <div className="card" style={{ marginTop: 12, padding: 10, borderLeft: '3px solid #4ade80' }}>
                      <div className="cost-label" style={{ color: '#9ff0bd' }}>执行结果</div>
                      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', marginTop: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {detailTask.summary}
                      </div>
                    </div>
                  )}
                  <div className="modal-actions" style={{ marginTop: 16 }}>
                    <button className="btn btn-submit" onClick={closeDetail}>关闭</button>
                  </div>
                </>
              );
            })()}
            {detailWf && (() => {
              const meta = execStatusMeta(detailWf.status);
              return (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                    <h2 style={{ margin: 0, fontSize: 17 }}>
                      {meta.icon} 工作流执行详情
                    </h2>
                    <span style={{ fontSize: 12, padding: '3px 12px', borderRadius: 999, color: meta.color, background: `${meta.color}18`, border: `1px solid ${meta.color}55`, fontWeight: 700 }}>
                      {meta.label}
                    </span>
                  </div>
                  <p className="card-desc" style={{ marginTop: 8, fontSize: 14, color: '#dce9ff' }}>
                    {detailWf.workflow_name || '工作流执行'}
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 12, fontSize: 13 }}>
                    <div style={{ gridColumn: '1 / -1' }}><span style={{ color: 'rgba(255,255,255,0.5)' }}>所属目标：</span>{detailWf.goal_title || '—'}</div>
                    <div><span style={{ color: 'rgba(255,255,255,0.5)' }}>开始时间：</span>{fullTime(detailWf.started_at)}</div>
                    <div><span style={{ color: 'rgba(255,255,255,0.5)' }}>完成时间：</span>{fullTime(detailWf.completed_at)}</div>
                  </div>
                  {detailWf.error && (
                    <div className="card" style={{ marginTop: 12, padding: 10, borderLeft: '3px solid #ff6b6b' }}>
                      <div className="cost-label" style={{ color: '#ff9d9d' }}>失败原因</div>
                      <div style={{ fontSize: 13, color: '#ffb3b3', marginTop: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {detailWf.error}
                      </div>
                    </div>
                  )}
                  <div className="modal-actions" style={{ marginTop: 16 }}>
                    <button className="btn btn-submit" onClick={closeDetail}>关闭</button>
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}
  </>
  );
}