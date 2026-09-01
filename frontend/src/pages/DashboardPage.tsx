import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  fetchLiveActivity,
  deriveAICoreState,
  type LiveActivity,
  type LiveWorkingItem,
  type LiveRecommendation,
  type LiveTask,
} from '../services/live';
import { fetchCostSummary, type CostSummary } from '../services/costs';
import { AIEmptyState } from '../components/AIEmptyState';
import { AIStatusDot } from '../components/AIWorkStatus';

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Gemini',
  deepseek: 'DeepSeek',
  moonshot: 'Moonshot',
  xai: 'Grok',
  ollama: 'Ollama 本地',
  mock: 'Mock',
  unknown: '未知',
};

const COLORS = {
  cyan: '#4cc9f0',
  violet: '#7b61ff',
  green: '#4ade80',
  yellow: '#facc15',
  red: '#ff6b6b',
  muted: 'rgba(255,255,255,0.5)',
};

const fmtUsd = (v: number) =>
  v >= 0.01 ? `$${v.toFixed(2)}` : v > 0 ? `$${v.toFixed(4)}` : '$0.00';

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

function clockTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function taskStatusMeta(status: string): { color: string; label: string; icon: string } {
  const s = (status || '').toLowerCase();
  if (s === 'completed' || s === 'success')
    return { color: COLORS.green, label: '完成', icon: '🟢' };
  if (s === 'failed' || s === 'failure' || s === 'error')
    return { color: COLORS.red, label: '失败', icon: '🔴' };
  if (s === 'running' || s === 'processing')
    return { color: COLORS.cyan, label: '执行中', icon: '🔵' };
  if (s === 'blocked') return { color: COLORS.yellow, label: '阻塞', icon: '🟡' };
  if (s === 'pending' || s === 'queued')
    return { color: COLORS.yellow, label: '等待中', icon: '🟡' };
  if (s === 'cancelled' || s === 'canceled')
    return { color: COLORS.muted, label: '已取消', icon: '⚪' };
  return { color: COLORS.muted, label: status || '未知', icon: '⚪' };
}

const DASH_CSS = `
.ceo-dashboard { display: flex; flex-direction: column; gap: 14px; }
.ceo-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ceo-head h1 { margin: 0; font-size: 22px; }
.ceo-sub { font-size: 12px; color: rgba(255,255,255,0.45); margin-top: 4px; }
.ceo-live { display: flex; align-items: center; gap: 8px; font-size: 12px; color: rgba(255,255,255,0.6); background: rgba(15,23,51,0.7); border: 1px solid rgba(110,130,255,0.2); padding: 6px 12px; border-radius: 999px; }
@keyframes ceo-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.kpi-card { cursor: pointer; padding: 16px 18px; position: relative; overflow: hidden; }
.kpi-card .kpi-icon { font-size: 18px; }
.kpi-card .kpi-label { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 6px; }
.kpi-card .kpi-value { font-size: 32px; font-weight: 800; line-height: 1.1; margin-top: 2px; }
.kpi-card .kpi-sub { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.kpi-card .kpi-bar { position: absolute; left: 0; top: 0; bottom: 0; width: 3px; }
.dash-main-row { display: grid; grid-template-columns: 1.55fr 1fr; gap: 14px; align-items: start; }
.dash-bottom-row { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; align-items: start; }
.dash-panel { background: linear-gradient(145deg, rgba(28,40,78,0.6), rgba(18,26,54,0.6)); border: 1px solid rgba(110,130,255,0.18); border-radius: 12px; padding: 16px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; }
.panel-head h2 { margin: 0; font-size: 15px; font-weight: 700; }
.panel-link { background: none; border: 1px solid rgba(110,130,255,0.3); color: #4cc9f0; font-size: 12px; padding: 4px 10px; border-radius: 6px; cursor: pointer; }
.panel-link:hover { background: rgba(76,201,240,0.1); }
.work-card { border: 1px solid rgba(123,97,255,0.3); background: rgba(123,97,255,0.07); border-radius: 10px; padding: 14px; margin-bottom: 10px; cursor: pointer; transition: all .2s; }
.work-card:hover { border-color: rgba(123,97,255,0.6); box-shadow: 0 0 18px rgba(123,97,255,0.18); }
.work-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.work-agent { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14px; }
.work-agent .agent-dot { width: 9px; height: 9px; border-radius: 50%; background: #4cc9f0; box-shadow: 0 0 8px #4cc9f0; animation: ceo-pulse 1.4s infinite; }
.work-badge { font-size: 11px; color: #05070f; background: #4cc9f0; padding: 2px 10px; border-radius: 999px; font-weight: 700; white-space: nowrap; }
.work-task { font-size: 14px; margin-top: 8px; color: #dce9ff; }
.work-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chip { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: rgba(76,201,240,0.1); border: 1px solid rgba(76,201,240,0.25); color: #9fdcff; }
.chip-violet { background: rgba(123,97,255,0.12); border-color: rgba(123,97,255,0.35); color: #c3b4ff; }
.chip-green { background: rgba(74,222,128,0.1); border-color: rgba(74,222,128,0.3); color: #9ff0bd; }
.work-step { font-size: 12px; color: rgba(255,255,255,0.65); margin-top: 8px; }
.progress-track { height: 6px; border-radius: 999px; background: rgba(255,255,255,0.08); margin-top: 10px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #7b61ff, #4cc9f0); transition: width .4s; }
.progress-indeterminate { height: 100%; width: 35%; border-radius: 999px; background: linear-gradient(90deg, transparent, rgba(123,97,255,0.8), transparent); animation: ceo-indet 1.6s infinite; }
@keyframes ceo-indet { 0% { transform: translateX(-120%); } 100% { transform: translateX(320%); } }
.progress-label { display: flex; justify-content: space-between; font-size: 11px; color: rgba(255,255,255,0.45); margin-top: 5px; }
.rec-card { border-left: 3px solid #facc15; background: rgba(250,204,21,0.05); border-radius: 8px; padding: 12px; margin-bottom: 10px; }
.rec-card.prio-high { border-left-color: #ff6b6b; background: rgba(255,107,107,0.06); }
.rec-card.prio-medium { border-left-color: #facc15; background: rgba(250,204,21,0.05); }
.rec-card.prio-low { border-left-color: #4cc9f0; background: rgba(76,201,240,0.05); }
.rec-title { font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
.rec-prio { font-size: 10px; padding: 1px 8px; border-radius: 999px; font-weight: 700; white-space: nowrap; }
.rec-prio.high { background: rgba(255,107,107,0.2); color: #ff9d9d; }
.rec-prio.medium { background: rgba(250,204,21,0.2); color: #fde68a; }
.rec-prio.low { background: rgba(76,201,240,0.2); color: #9fdcff; }
.rec-body { font-size: 12px; color: rgba(255,255,255,0.65); line-height: 1.55; margin-top: 6px; }
.rec-body b { color: rgba(255,255,255,0.85); font-weight: 600; }
.rec-btn { margin-top: 8px; font-size: 12px; padding: 5px 14px; border-radius: 7px; border: none; cursor: pointer; font-weight: 700; }
.rec-btn.high { background: #ff6b6b; color: #fff; }
.rec-btn.medium { background: #facc15; color: #241a00; }
.rec-btn.low { background: rgba(76,201,240,0.25); color: #9fdcff; }
.exec-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 8px; border-radius: 8px; cursor: pointer; border-bottom: 1px solid rgba(110,130,255,0.1); }
.exec-row:hover { background: rgba(76,201,240,0.06); }
.exec-icon { font-size: 14px; margin-top: 2px; }
.exec-main { flex: 1; min-width: 0; }
.exec-line1 { font-size: 13px; }
.exec-agent { font-weight: 700; color: #dce9ff; }
.exec-title { color: rgba(255,255,255,0.8); }
.exec-result { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.exec-error { font-size: 12px; color: #ff9d9d; margin-top: 3px; }
.exec-time { font-size: 11px; color: rgba(255,255,255,0.4); white-space: nowrap; }
.goal-row { margin-bottom: 12px; cursor: pointer; }
.goal-name { font-size: 13px; display: flex; justify-content: space-between; gap: 8px; }
.goal-status { font-size: 10px; padding: 1px 8px; border-radius: 999px; white-space: nowrap; }
.cost-line { display: flex; justify-content: space-between; font-size: 13px; padding: 6px 0; border-bottom: 1px solid rgba(110,130,255,0.1); }
.cost-line:last-child { border-bottom: none; }
.dash-empty { text-align: center; padding: 26px 12px; color: rgba(255,255,255,0.45); font-size: 13px; }
.dash-empty .empty-icon { font-size: 26px; display: block; margin-bottom: 8px; opacity: 0.7; }
.mini-exec { font-size: 12px; padding: 7px 8px; border-radius: 7px; cursor: pointer; display: flex; gap: 8px; align-items: center; color: rgba(255,255,255,0.7); }
.mini-exec:hover { background: rgba(74,222,128,0.07); }
@media (max-width: 1200px) { .dash-main-row, .dash-bottom-row { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .kpi-row { grid-template-columns: 1fr 1fr; gap: 10px; } .kpi-card .kpi-value { font-size: 26px; } }
`;

export function DashboardPage() {
  const navigate = useNavigate();
  const [live, setLive] = useState<LiveActivity | null>(null);
  const [cost, setCost] = useState<CostSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const [liveData, costData] = await Promise.all([
        fetchLiveActivity(15),
        fetchCostSummary(7).catch(() => null),
      ]);
      setLive(liveData);
      setCost(costData);
      setLastUpdated(new Date());
      setError('');
    } catch (e) {
      console.error('Failed to load dashboard', e);
      setError('加载驾驶舱数据失败，请确认后端服务已启动');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // 真实数据轮询：每 15 秒重新请求 API（状态全部来自数据库，非前端伪造）
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, [load]);

  if (loading && !live) {
    return (
      <section className="page">
        <style>{DASH_CSS}</style>
        <h1>CEO 驾驶舱</h1>
        <p style={{ color: 'rgba(255,255,255,0.5)' }}>正在加载实时数据…</p>
      </section>
    );
  }

  if (error && !live) {
    return (
      <section className="page">
        <style>{DASH_CSS}</style>
        <h1>CEO 驾驶舱</h1>
        <AIEmptyState isError errorMessage={error} onRetry={load} />
      </section>
    );
  }

  if (!live) return null;

  // ===== 真实数据派生（在线员工 ≠ 执行中任务，语义严格区分）=====
  const onlineEmployees = live.active_employees ?? 0;
  const totalEmployees = live.total_employees ?? 0;
  const workingNow: LiveWorkingItem[] = live.working_now ?? [];
  const workingCount = workingNow.length;
  const completedToday = live.today?.completed ?? 0;
  const failedTotal = live.failed_tasks ?? 0;
  const blockedTotal = live.blocked_tasks ?? 0;
  const attentionCount = failedTotal + blockedTotal;
  const recommendations: LiveRecommendation[] = live.recommendations ?? [];
  const recentTasks: LiveTask[] = live.recent_tasks ?? [];
  const recentlyDone = recentTasks.filter((t) => t.status === 'completed').slice(0, 4);
  const goals = live.goals ?? [];
  // AI Core 统一状态（与 Header/Sidebar 同一状态机派生，来自本页已加载的真实数据）
  const aiCore = deriveAICoreState(live);

  const goTask = (t: LiveTask) => navigate(`/workflow?task=${t.id}`);
  const goWorking = (w: LiveWorkingItem) => {
    if (w.kind === 'workflow') navigate(`/workflow?execution=${w.execution_id || w.id}`);
    else navigate(`/workflow?task=${w.id}`);
  };

  return (
    <section className="page ceo-dashboard">
      <style>{DASH_CSS}</style>

      {/* ===== 页头 ===== */}
      <div className="ceo-head">
        <div>
          <h1>CEO 驾驶舱</h1>
          <div className="ceo-sub">AI 企业操作系统 · 团队实时态势（数据每 15 秒自动刷新）</div>
        </div>
        <div className="ceo-live" title={aiCore.detail || aiCore.label}>
          <AIStatusDot status={aiCore.status} size={8} />
          AI {aiCore.label} · 更新于 {lastUpdated ? lastUpdated.toLocaleTimeString('zh-CN') : '--'}
        </div>
      </div>

      {/* ===== 第一层：CEO KPI ===== */}
      <div className="kpi-row">
        <div className="card kpi-card" onClick={() => navigate('/employees')}>
          <span className="kpi-bar" style={{ background: COLORS.cyan }} />
          <div className="kpi-icon">👥</div>
          <div className="kpi-label">AI 员工在线</div>
          <div className="kpi-value" style={{ color: COLORS.cyan }}>{onlineEmployees}</div>
          <div className="kpi-sub">
            共 {totalEmployees} 名 · 在线 {onlineEmployees} · 执行中 {workingCount}
            {workingCount > 0 ? ` · 可派发 ${Math.max(0, onlineEmployees - workingCount)}` : ' · 全部可派发'}
          </div>
        </div>
        <div className="card kpi-card" onClick={() => navigate('/workflow')}>
          <span className="kpi-bar" style={{ background: COLORS.violet }} />
          <div className="kpi-icon">⚡</div>
          <div className="kpi-label">任务执行中</div>
          <div className="kpi-value" style={{ color: workingCount > 0 ? COLORS.violet : COLORS.muted }}>
            {workingCount}
          </div>
          <div className="kpi-sub">
            {workingCount > 0
              ? `${workingCount} 项任务/工作流运行中`
              : '当前没有执行中的任务'}
          </div>
        </div>
        <div className="card kpi-card" onClick={() => navigate('/workflow')}>
          <span className="kpi-bar" style={{ background: COLORS.green }} />
          <div className="kpi-icon">✅</div>
          <div className="kpi-label">今日完成</div>
          <div className="kpi-value" style={{ color: COLORS.green }}>{completedToday}</div>
          <div className="kpi-sub">今日已完成的 AI 任务</div>
        </div>
        <div
          className="card kpi-card"
          onClick={() => navigate(attentionCount > 0 ? '/workflow' : '/metrics')}
        >
          <span className="kpi-bar" style={{ background: attentionCount > 0 ? COLORS.red : COLORS.green }} />
          <div className="kpi-icon">🔔</div>
          <div className="kpi-label">需要关注</div>
          <div className="kpi-value" style={{ color: attentionCount > 0 ? COLORS.red : COLORS.green }}>
            {attentionCount}
          </div>
          <div className="kpi-sub">
            {attentionCount > 0 ? `失败 ${failedTotal} · 阻塞 ${blockedTotal}` : '系统运行正常'}
          </div>
        </div>
      </div>

      {/* ===== 第二层：AI 正在工作 + AI CEO 建议 ===== */}
      <div className="dash-main-row">
        {/* 视觉核心：AI 正在工作 */}
        <div className="dash-panel">
          <div className="panel-head">
            <h2>🤖 AI 正在工作</h2>
            <button className="panel-link" onClick={() => navigate('/workflow')}>
              工作流中心 →
            </button>
          </div>

          {workingNow.length === 0 ? (
            <div>
              <div className="dash-empty">
                <span className="empty-icon">🌙</span>
                当前没有 AI 正在执行
                <div style={{ marginTop: 6, fontSize: 12 }}>
                  AI 团队 {onlineEmployees} 名员工在线，可前往目标中心下发任务
                </div>
              </div>
              {recentlyDone.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <div
                    style={{
                      fontSize: 12,
                      color: 'rgba(255,255,255,0.45)',
                      margin: '4px 8px 8px',
                    }}
                  >
                    最近完成
                  </div>
                  {recentlyDone.map((t) => (
                    <div key={t.id} className="mini-exec" onClick={() => goTask(t)}>
                      <span>🟢</span>
                      <span style={{ flex: 1 }}>
                        <b>{t.employee_name || 'AI 员工'}</b> 完成「{t.title}」
                      </span>
                      <span className="exec-time">{timeAgo(t.completed_at || t.updated_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            workingNow.map((w) => (
              <div key={`${w.kind}-${w.id}`} className="work-card" onClick={() => goWorking(w)}>
                <div className="work-top">
                  <div className="work-agent">
                    <span className="agent-dot" />
                    {w.kind === 'workflow' ? '🔄 工作流引擎' : w.employee_name || 'AI 员工'}
                    {w.position && (
                      <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', fontWeight: 400 }}>
                        {w.position}
                      </span>
                    )}
                  </div>
                  <span className="work-badge">执行中</span>
                </div>
                <div className="work-task">{w.title}</div>
                <div className="work-meta">
                  {w.goal_title && <span className="chip chip-violet">🎯 {w.goal_title}</span>}
                  {w.workflow_name && <span className="chip">🔗 {w.workflow_name}</span>}
                  {w.provider && (
                    <span className="chip chip-green">
                      {PROVIDER_LABELS[w.provider] ?? w.provider}
                      {w.model ? ` · ${w.model}` : ''}
                    </span>
                  )}
                </div>
                {w.current_step && (
                  <div className="work-step">📍 当前步骤：{w.current_step}</div>
                )}
                {/* 进度：有真实百分比显示真实值；否则显示不确定态（不伪造数字） */}
                <div className="progress-track">
                  {typeof w.progress === 'number' && w.progress !== null ? (
                    <div
                      className="progress-fill"
                      style={{ width: `${Math.max(0, Math.min(100, w.progress))}%` }}
                    />
                  ) : (
                    <div className="progress-indeterminate" />
                  )}
                </div>
                <div className="progress-label">
                  <span>
                    {typeof w.progress === 'number' && w.progress !== null
                      ? `进度 ${Math.round(w.progress)}%`
                      : '执行中（进度以实际步骤为准）'}
                  </span>
                  <span>
                    {w.started_at ? `开始于 ${clockTime(w.started_at)} · ${timeAgo(w.started_at)}` : ''}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* AI CEO 建议 */}
        <div className="dash-panel">
          <div className="panel-head">
            <h2>💡 AI CEO 建议</h2>
            {recommendations.length > 0 && (
              <span style={{ fontSize: 12, color: COLORS.yellow }}>{recommendations.length} 项待处理</span>
            )}
          </div>

          {recommendations.length === 0 ? (
            <div className="dash-empty">
              <span className="empty-icon">✨</span>
              当前没有需要 CEO 处理的事项
              <div style={{ marginTop: 6, fontSize: 12 }}>
                失败任务、阻塞审批、业务异常出现时会在这里提示
              </div>
            </div>
          ) : (
            recommendations.map((rec) => (
              <div key={rec.id} className={`rec-card prio-${rec.priority}`}>
                <div className="rec-title">
                  <span className={`rec-prio ${rec.priority}`}>
                    {rec.priority === 'high'
                      ? '高优先级'
                      : rec.priority === 'medium'
                        ? '中优先级'
                        : '低优先级'}
                  </span>
                  <span>{rec.title}</span>
                </div>
                <div className="rec-body">
                  <div><b>问题：</b>{rec.problem}</div>
                  <div style={{ marginTop: 4 }}><b>建议：</b>{rec.suggestion}</div>
                </div>
                <button
                  className={`rec-btn ${rec.priority}`}
                  onClick={() => navigate(rec.action_url)}
                >
                  {rec.action_label} →
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ===== 第三层：最近 AI 执行（真实任务执行，非审计日志）===== */}
      <div className="dash-panel">
        <div className="panel-head">
          <h2>📋 最近 AI 执行</h2>
          <button className="panel-link" onClick={() => navigate('/workflow')}>
            全部执行记录 →
          </button>
        </div>
        {recentTasks.length === 0 ? (
          <div className="dash-empty">
            <span className="empty-icon">📭</span>
            暂无 AI 执行记录
            <div style={{ marginTop: 6, fontSize: 12 }}>
              AI 员工执行任务后，结果会实时出现在这里
            </div>
          </div>
        ) : (
          recentTasks.slice(0, 7).map((t) => {
            const meta = taskStatusMeta(t.status);
            return (
              <div key={t.id} className="exec-row" onClick={() => goTask(t)}>
                <span className="exec-icon">{meta.icon}</span>
                <div className="exec-main">
                  <div className="exec-line1">
                    <span className="exec-agent">{t.employee_name || 'AI 员工'}</span>
                    <span className="exec-title"> · {t.title}</span>
                  </div>
                  <div className="work-meta" style={{ marginTop: 4 }}>
                    {t.goal_title && <span className="chip chip-violet">🎯 {t.goal_title}</span>}
                    {t.workflow_name && <span className="chip">🔗 {t.workflow_name}</span>}
                    {t.provider && (
                      <span className="chip chip-green">
                        {PROVIDER_LABELS[t.provider] ?? t.provider}
                      </span>
                    )}
                    <span
                      className="chip"
                      style={{ color: meta.color, borderColor: `${meta.color}55`, background: `${meta.color}14` }}
                    >
                      {meta.label}
                    </span>
                  </div>
                  {t.status === 'failed' && t.error ? (
                    <div className="exec-error">⚠ {t.error}</div>
                  ) : t.summary ? (
                    <div className="exec-result">📄 {t.summary}</div>
                  ) : null}
                </div>
                <span className="exec-time">{timeAgo(t.completed_at || t.updated_at)}</span>
              </div>
            );
          })
        )}
      </div>

      {/* ===== 第四层：目标进度 + AI 成本 ===== */}
      <div className="dash-bottom-row">
        <div className="dash-panel" style={{ cursor: 'pointer' }} onClick={() => navigate('/goals')}>
          <div className="panel-head">
            <h2>🎯 目标进度</h2>
            <button
              className="panel-link"
              onClick={(e) => { e.stopPropagation(); navigate('/goals'); }}
            >
              目标中心 →
            </button>
          </div>
          {goals.length === 0 ? (
            <div className="dash-empty">
              <span className="empty-icon">🎯</span>
              暂无目标，前往目标中心用一句话创建业务目标
            </div>
          ) : (
            goals.slice(0, 4).map((g) => {
              const pct = Math.max(0, Math.min(100, Number(g.progress_pct ?? 0)));
              const gColor =
                g.status === 'completed'
                  ? COLORS.green
                  : g.status === 'failed'
                    ? COLORS.red
                    : COLORS.cyan;
              return (
                <div key={g.id} className="goal-row">
                  <div className="goal-name">
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {g.title}
                    </span>
                    <span
                      className="goal-status"
                      style={{ background: `${gColor}22`, color: gColor }}
                    >
                      {g.status === 'completed' ? '已完成' : g.status === 'active' ? '进行中' : g.status}
                    </span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${pct}%`, background: gColor }} />
                  </div>
                  <div className="progress-label">
                    <span>{pct}%</span>
                    <span>
                      {g.kpi_name && g.kpi_target
                        ? `${g.kpi_name} ${g.kpi_current ?? 0}/${g.kpi_target}`
                        : ''}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="dash-panel" style={{ cursor: 'pointer' }} onClick={() => navigate('/metrics')}>
          <div className="panel-head">
            <h2>💰 AI 成本（近 7 天）</h2>
            <button
              className="panel-link"
              onClick={(e) => { e.stopPropagation(); navigate('/metrics'); }}
            >
              指标中心 →
            </button>
          </div>
          {!cost ? (
            <div className="dash-empty">
              <span className="empty-icon">💰</span>
              暂无 AI 调用成本数据
              <div style={{ marginTop: 6, fontSize: 12 }}>执行过 AI 任务后这里会显示费用与 Token</div>
            </div>
          ) : (
            <>
              <div className="cost-line">
                <span style={{ color: 'rgba(255,255,255,0.55)' }}>累计成本</span>
                <strong style={{ color: COLORS.cyan }}>{fmtUsd(cost.total_cost_usd)}</strong>
              </div>
              <div className="cost-line">
                <span style={{ color: 'rgba(255,255,255,0.55)' }}>调用次数</span>
                <strong>{cost.total_requests}</strong>
              </div>
              <div className="cost-line">
                <span style={{ color: 'rgba(255,255,255,0.55)' }}>消耗 Token</span>
                <strong>{cost.total_tokens.toLocaleString()}</strong>
              </div>
              <div className="cost-line">
                <span style={{ color: 'rgba(255,255,255,0.55)' }}>失败次数</span>
                <strong style={{ color: cost.failed_requests > 0 ? COLORS.yellow : COLORS.green }}>
                  {cost.failed_requests}
                </strong>
              </div>
              <div className="cost-line">
                <span style={{ color: 'rgba(255,255,255,0.55)' }}>平均耗时</span>
                <strong>
                  {cost.avg_latency_ms > 1000
                    ? `${(cost.avg_latency_ms / 1000).toFixed(1)}s`
                    : `${Math.round(cost.avg_latency_ms)}ms`}
                </strong>
              </div>
            </>
          )}
          <div style={{ marginTop: 12, fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
            审计日志（登录/权限/API 访问）已归入「系统治理」
            <button
              className="panel-link"
              style={{ marginLeft: 6 }}
              onClick={(e) => { e.stopPropagation(); navigate('/security'); }}
            >
              安全治理 →
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
