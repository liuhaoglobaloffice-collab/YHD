import { useEffect, useState } from 'react';
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

export function WorkflowPage() {
  const { t } = useI18n();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [templates, setTemplates] = useState<TradeTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [apiError, setApiError] = useState(false);

  // 模板执行
  const [execTemplate, setExecTemplate] = useState<TradeTemplate | null>(null);
  const [execInputs, setExecInputs] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState<InstantiateResult | null>(null);
  const [execError, setExecError] = useState('');

  useEffect(() => {
    Promise.all([loadWorkflows(), loadTemplates()]);
  }, []);

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

  // 模拟工作流执行活动（演示）
  const demoActivities: ActivityItem[] = workflows.length > 0
    ? workflows.map((wf, i) => ({
        id: `wf-${wf.id}`,
        time: new Date(wf.updated_at || wf.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        aiName: wf.name,
        action: wf.status === 'active' ? '工作流运行中' : '工作流已停止',
        status: (wf.status === 'active' ? 'running' : 'pending') as 'running' | 'pending',
      }))
    : [];

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

        {/* 右侧：AI 工作流活动 */}
        <div>
          <AIActivityFeed
            activities={demoActivities}
            title="工作流执行活动"
            maxItems={8}
            emptyMessage="暂无工作流执行记录"
          />

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
  </>
  );
}