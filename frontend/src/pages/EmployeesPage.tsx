import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  fetchEmployees, executeTaskStream, submitAsyncTask, fetchExecution, fetchExecutions, cancelAsyncTask,
  fetchProviderStatus, type Employee, type ExecuteTaskResponse, type ProviderStatus, type ExecutionRecord,
} from '../services/employees';
import { useI18n } from '../i18n';
import { AIWorkStatus, AIStatusDot, type AIStatus } from '../components/AIWorkStatus';
import { AIActivityFeed, type ActivityItem } from '../components/AIActivityFeed';
import { AIEmptyState } from '../components/AIEmptyState';

/** 后端 lifecycle 状态 → AIWorkStatus 工作状态映射 */
const STATUS_MAP: Record<string, AIStatus> = {
  active: 'working',    // 工作中（蓝色脉冲）
  training: 'waiting',  // 配置中（黄色）
  created: 'idle',      // 已就绪（灰色）
  suspended: 'offline', // 已暂停（灰色）
  retired: 'offline',   // 已退休（灰色）
};

/** 状态对应的建议文案 */
const STATUS_SUGGESTION: Record<string, string> = {
  active: '该员工正在执行 AI 任务，可在执行记录中查看输出。',
  training: '该员工正在配置中，完成后即可分配任务。',
  created: '该员工已就绪，可以开始分配任务。',
  suspended: '该员工已被暂停，需激活后才能使用。',
  retired: '该员工已退休，不再接受任务。',
};

/** 状态对应的当前任务文案 */
const STATUS_TASK: Record<string, string> = {
  active: '执行 AI 任务中',
  training: '配置 AI 能力中',
  created: '等待任务分配',
  suspended: '已暂停',
  retired: '已退休',
};

/** 每个 Agent 角色的快速提示词模板 */
const PROMPT_TEMPLATES: Record<string, string[]> = {
  gpt: ['分析公司当前运营状况，给出优化建议', '总结本周核心业务指标', '评估新项目的可行性'],
  grok: ['分析市场趋势数据', '生成竞品分析报告', '评估新市场机会'],
  claude: ['审查系统架构设计，指出潜在风险', '排查生产环境异常', '优化系统性能'],
  deepseek: ['分析用户行为数据，发现关键洞察', '生成数据可视化报告', '预测下季度业务趋势'],
  gemini: ['调研行业最新技术趋势', '整理竞争对手动态', '分析目标用户画像'],
  kimi: ['分析用户需求反馈，提炼核心痛点', '生成产品功能优先级建议', '评估产品迭代方向'],
};

const DEFAULT_TEMPLATES: string[] = ['分析当前业务状况，给出改进建议', '整理关键数据指标，输出报告', '评估潜在风险，给出应对方案'];

export function EmployeesPage() {
  const { t } = useI18n();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [apiError, setApiError] = useState(false);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<ExecuteTaskResponse | null>(null);
  const [executing, setExecuting] = useState(false);
  const [execError, setExecError] = useState('');
  const [streamOutput, setStreamOutput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [asyncTask, setAsyncTask] = useState<ExecutionRecord | null>(null);
  const [asyncPolling, setAsyncPolling] = useState(false);
  const [useAsyncMode, setUseAsyncMode] = useState(false);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [showExecutions, setShowExecutions] = useState(false);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setApiError(false);
    setError('');
    await Promise.all([loadEmployees(), loadProviderStatus()]);
    setLoading(false);
  };

  const loadEmployees = async () => {
    try {
      const data = await fetchEmployees();
      setEmployees(data);
    } catch (e) {
      console.error('Failed to load employees', e);
      setError('加载 AI 员工列表失败');
      setApiError(true);
    }
  };

  const loadProviderStatus = async () => {
    try {
      const status = await fetchProviderStatus();
      setProviderStatus(status);
    } catch (e) {
      console.error('Failed to load provider status', e);
    }
  };

  const openExecute = (id: string) => {
    setExecutingId(id);
    setPrompt('');
    setResult(null);
    setExecError('');
    setStreamOutput('');
    setIsStreaming(false);
  };

  const closeExecute = () => {
    setExecutingId(null);
    setPrompt('');
    setResult(null);
    setExecuting(false);
    setExecError('');
    setStreamOutput('');
    setIsStreaming(false);
  };

  const handleExecute = async () => {
    if (!executingId || !prompt.trim()) return;
    setExecuting(true);
    setExecError('');
    setResult(null);
    setStreamOutput('');
    setIsStreaming(true);
    try {
      const { output, error } = await executeTaskStream(executingId, { prompt: prompt.trim() }, (delta) => {
        setStreamOutput((prev) => prev + delta);
      });
      setResult({
        execution_id: '', employee_id: executingId, employee_name: selectedEmployee?.name ?? '',
        agent_type: selectedEmployee?.agent_type ?? '', status: error ? 'failed' : 'completed',
        output: output || streamOutput, error: error ?? null, response_time_ms: null,
      });
      if (error) setExecError(error);
    } catch (e) {
      setExecError(e instanceof Error ? e.message : '执行任务失败');
    }
    setExecuting(false);
    setIsStreaming(false);
  };

  const loadExecutions = useCallback(async () => {
    try {
      const data = await fetchExecutions();
      setExecutions(data.executions);
    } catch (e) {
      console.error('Failed to load executions', e);
    }
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) { clearInterval(pollTimerRef.current); pollTimerRef.current = null; }
    setAsyncPolling(false);
  }, []);

  const pollExecution = useCallback(async (taskId: string) => {
    try {
      const record = await fetchExecution(taskId);
      setAsyncTask(record);
      if (record.status === 'running' || record.status === 'queued') { setAsyncPolling(true); }
      else { stopPolling(); }
      return record;
    } catch (e) {
      console.error('Failed to poll execution', e);
      stopPolling();
      return null;
    }
  }, [stopPolling]);

  const handleAsyncExecute = async () => {
    if (!executingId || !prompt.trim()) return;
    setExecuting(true); setExecError(''); setResult(null); setStreamOutput(''); setAsyncTask(null); setAsyncPolling(true);
    try {
      const record = await submitAsyncTask(executingId, { prompt: prompt.trim() });
      setAsyncTask(record);
      pollTimerRef.current = setInterval(() => { pollExecution(record.task_id); }, 1500);
      await pollExecution(record.task_id);
      loadExecutions();
    } catch (e) {
      setExecError(e instanceof Error ? e.message : '提交任务失败');
      stopPolling();
    }
    setExecuting(false);
  };

  const handleCancelAsync = async () => {
    if (!asyncTask) return;
    try {
      await cancelAsyncTask(asyncTask.task_id);
      stopPolling();
      setAsyncTask((prev) => prev ? { ...prev, status: 'cancelled', error: '已取消' } : prev);
      loadExecutions();
    } catch (e) { console.error('Failed to cancel', e); }
  };

  const handleViewExecutions = async () => {
    const next = !showExecutions;
    setShowExecutions(next);
    if (next) loadExecutions();
  };

  useEffect(() => () => { if (pollTimerRef.current) clearInterval(pollTimerRef.current); }, []);

  const selectedEmployee = executingId ? employees.find(e => e.id === executingId) : null;
  const templates = useMemo(() => {
    if (!selectedEmployee?.agent_type) return DEFAULT_TEMPLATES;
    return PROMPT_TEMPLATES[selectedEmployee.agent_type] ?? DEFAULT_TEMPLATES;
  }, [selectedEmployee]);

  // 员工统计
  const stats = useMemo(() => {
    const working = employees.filter(e => STATUS_MAP[e.status] === 'working').length;
    const idle = employees.filter(e => STATUS_MAP[e.status] === 'idle' || STATUS_MAP[e.status] === 'waiting').length;
    const offline = employees.filter(e => STATUS_MAP[e.status] === 'offline').length;
    return { total: employees.length, working, idle, offline };
  }, [employees]);

  // 活动数据（从员工状态生成）
  const demoActivities: ActivityItem[] = employees.length > 0
    ? employees.map((emp, i) => ({
        id: emp.id,
        time: new Date(emp.updated_at || emp.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        aiName: emp.name,
        action: emp.status === 'active' ? '正在执行任务' : '等待任务分配',
        status: (emp.status === 'active' ? 'running' : 'pending') as 'running' | 'pending',
      }))
    : [];

  if (loading) {
    return (
      <section className="page">
        <h1>AI 员工办公室</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  if (apiError) {
    return (
      <section className="page">
        <h1>AI 员工办公室</h1>
        <AIEmptyState isError errorMessage={error} onRetry={loadData} />
      </section>
    );
  }

  return (
    <section className="page">
      <h1>AI 员工办公室</h1>

      {/* 员工统计 */}
      <div className="grid" style={{ marginBottom: 20 }}>
        <div className="card" style={{ borderLeft: '3px solid #4cc9f0' }}>
          <div className="cost-label">AI 员工总数</div>
          <div className="cost-value" style={{ color: '#4cc9f0' }}>{stats.total}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #4ade80' }}>
          <div className="cost-label">工作中</div>
          <div className="cost-value" style={{ color: '#4ade80' }}>{stats.working}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #facc15' }}>
          <div className="cost-label">空闲/配置中</div>
          <div className="cost-value" style={{ color: '#facc15' }}>{stats.idle}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #666' }}>
          <div className="cost-label">已暂停/退休</div>
          <div className="cost-value" style={{ color: '#666' }}>{stats.offline}</div>
        </div>
      </div>

      {/* Provider 状态 + 执行记录 */}
      {providerStatus && (
        <div className={`provider-banner ${providerStatus.available ? 'provider-ok' : 'provider-warn'}`} style={{ marginBottom: 16 }}>
          <span className="provider-icon">{providerStatus.available ? '✓' : '!'}</span>
          <span className="provider-text">
            LLM 提供商: <strong>{providerStatus.description}</strong>
            {providerStatus.model && <span className="provider-model"> ({providerStatus.model})</span>}
          </span>
          <button className="btn btn-sm" onClick={handleViewExecutions}>
            {showExecutions ? '收起记录' : `执行记录 (${executions.length})`}
          </button>
        </div>
      )}

      {/* 执行记录面板 */}
      {showExecutions && (
        <div className="executions-panel" style={{ marginBottom: 16 }}>
          <div className="executions-header">
            <strong>异步任务执行记录</strong>
            <span className="executions-count">{executions.length} 条</span>
          </div>
          {executions.length === 0 ? (
            <p className="executions-empty">暂无执行记录</p>
          ) : (
            <div className="executions-list">
              {executions.map((ex) => (
                <div key={ex.task_id} className={`execution-item st-${ex.status}`}>
                  <div className="execution-item-main">
                    <span className="execution-employee">{ex.employee_name}</span>
                    <span className={`execution-status st-${ex.status}`}>{ex.status}</span>
                  </div>
                  <div className="execution-item-sub">
                    <span className="execution-prompt">{ex.prompt.slice(0, 40)}</span>
                    {ex.elapsed_ms != null && <span className="execution-time">{Math.round(ex.elapsed_ms)}ms</span>}
                  </div>
                  {ex.error && <div className="execution-error">{ex.error}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 主区域：员工列表 + 活动时间线 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16 }}>
        {/* 员工卡片列表 */}
        <div>
          {employees.length === 0 ? (
            <AIEmptyState
              title="AI 员工团队尚未建立"
              description="还没有 AI 员工。请通过企业初始化流程创建第一个 AI 员工。"
              aiStatus="idle"
              availableTasks={['创建 AI 员工', '配置 AI 员工能力', '分配任务给 AI 员工']}
              nextStep="建议先创建一个 AI 销售助手"
              actionLabel="前往初始化"
              onAction={() => window.location.href = '/onboarding'}
            />
          ) : (
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', margin: 0 }}>
              {employees.map((emp) => {
                const aiStatus = STATUS_MAP[emp.status] ?? 'idle';
                return (
                  <div key={emp.id} style={{ position: 'relative' }}>
                    <AIWorkStatus
                      name={emp.name}
                      status={aiStatus}
                      position={emp.position}
                      model={emp.agent_type ?? undefined}
                      currentTask={STATUS_TASK[emp.status]}
                      suggestion={STATUS_SUGGESTION[emp.status]}
                    />
                    <button
                      className="btn btn-execute"
                      style={{ position: 'absolute', bottom: 12, right: 12, fontSize: 11, padding: '4px 12px' }}
                      onClick={() => openExecute(emp.id)}
                      disabled={!emp.agent_type}
                      title={!emp.agent_type ? '该员工未分配 Agent 类型' : '执行任务'}
                    >
                      执行任务
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 右侧：AI 活动时间线 */}
        <div>
          <AIActivityFeed
            activities={demoActivities}
            title="员工活动"
            maxItems={8}
            emptyMessage="暂无员工活动记录"
          />

          {/* 操作面板 */}
          {employees.length > 0 && (
            <div className="card" style={{ marginTop: 16, borderLeft: '3px solid #4cc9f0' }}>
              <div className="cost-label" style={{ marginBottom: 8 }}>⚡ 快速操作</div>
              <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', lineHeight: 1.6, marginBottom: 10 }}>
                点击员工卡片上的"执行任务"按钮，选择 AI 员工并分配具体任务。
              </p>
              <button className="btn btn-submit" style={{ width: '100%' }} onClick={handleViewExecutions}>
                {showExecutions ? '收起执行记录' : `查看执行记录 (${executions.length})`}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Execute Modal */}
      {executingId && selectedEmployee && (
        <div className="modal-overlay" onClick={closeExecute}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>执行任务 - {selectedEmployee.name}</h2>
            <p className="modal-meta">
              {selectedEmployee.department} · {selectedEmployee.position}
              {selectedEmployee.agent_type && ` · Agent: ${selectedEmployee.agent_type}`}
            </p>

            <div className="template-chips">
              <span className="template-label">快速模板：</span>
              {templates.map((t, i) => (
                <button key={i} className="template-chip" onClick={() => setPrompt(t)} disabled={executing}>{t}</button>
              ))}
            </div>

            <textarea className="modal-textarea" rows={4} placeholder="输入任务描述，或点击上方快速模板..." value={prompt} onChange={e => setPrompt(e.target.value)} disabled={executing} />

            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={closeExecute} disabled={executing}>取消</button>
              <div className="exec-mode-switch" title="选择执行方式">
                <button className={`exec-mode-btn ${!useAsyncMode ? 'active' : ''}`} onClick={() => setUseAsyncMode(false)} disabled={executing}>实时流式</button>
                <button className={`exec-mode-btn ${useAsyncMode ? 'active' : ''}`} onClick={() => setUseAsyncMode(true)} disabled={executing}>异步队列</button>
              </div>
              {useAsyncMode ? (
                <button className="btn btn-submit" onClick={handleAsyncExecute} disabled={executing || !prompt.trim()}>{executing ? '提交中...' : '提交任务'}</button>
              ) : (
                <button className="btn btn-submit" onClick={handleExecute} disabled={executing || !prompt.trim()}>{executing ? (isStreaming ? '生成中...' : '执行中...') : '执行'}</button>
              )}
            </div>

            {execError && <div className="modal-error"><strong>错误：</strong> {execError}</div>}

            {useAsyncMode && asyncTask && (
              <div className={`modal-result async-result st-${asyncTask.status}`}>
                <div className="result-header">
                  <span className={`result-status status-${asyncTask.status}`}>
                    {asyncTask.status === 'queued' ? '排队中' : asyncTask.status === 'running' ? '执行中' : asyncTask.status === 'completed' ? '已完成' : asyncTask.status === 'cancelled' ? '已取消' : '失败'}
                  </span>
                  <span className="result-time">任务: {asyncTask.task_id.slice(0, 8)}</span>
                </div>
                {asyncPolling && (
                  <div className="async-progress">
                    <div className="progress-bar"><div className="progress-fill" /></div>
                    <span className="progress-label">AI 后台执行中，实时同步输出...</span>
                  </div>
                )}
                {asyncTask.output && <div className="result-output"><strong>输出：</strong><pre>{asyncTask.output}</pre></div>}
                {asyncTask.error && <div className="result-error"><strong>错误：</strong> {asyncTask.error}</div>}
                {(asyncTask.status === 'queued' || asyncTask.status === 'running') && (
                  <div className="async-actions"><button className="btn btn-cancel btn-sm" onClick={handleCancelAsync}>取消任务</button></div>
                )}
              </div>
            )}

            {isStreaming && (
              <div className="modal-result streaming">
                <div className="result-header">
                  <span className="result-status status-streaming">● 生成中</span>
                  <span className="streaming-indicator"><span className="streaming-dot" /> AI 正在思考...</span>
                </div>
                <div className="result-output"><pre className="streaming-output">{streamOutput || ' '}<span className="stream-cursor" /></pre></div>
              </div>
            )}

            {result && (
              <div className="modal-result">
                <div className="result-header">
                  <span className={`result-status status-${result.status}`}>{result.status}</span>
                  {result.response_time_ms != null && <span className="result-time">响应时间: {result.response_time_ms}ms</span>}
                </div>
                <div className="result-output"><strong>输出：</strong><pre>{result.output || '（无输出）'}</pre></div>
                {result.error && <div className="result-error"><strong>错误：</strong> {result.error}</div>}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}