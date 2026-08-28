import { useState, useEffect } from 'react';
import { fetchDashboardOverview, type DashboardOverview } from '../services/dashboard';
import { fetchCostSummary, type CostSummary } from '../services/costs';
import { useI18n } from '../i18n';
import { AIWorkStatus, type AIStatus } from '../components/AIWorkStatus';
import { AIActivityFeed, type ActivityItem } from '../components/AIActivityFeed';
import { AIEmptyState } from '../components/AIEmptyState';

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI', anthropic: 'Anthropic', google: 'Gemini',
  deepseek: 'DeepSeek', moonshot: 'Moonshot', xai: 'Grok',
  ollama: 'Ollama 本地', mock: 'Mock 开发', unknown: '未知',
};

const fmtUsd = (v: number) => (v >= 0.01 ? `$${v.toFixed(2)}` : v > 0 ? `$${v.toFixed(4)}` : '$0.00');

export function DashboardPage() {
  const { t } = useI18n();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [cost, setCost] = useState<CostSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(7);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [overview, costSummary] = await Promise.all([
        fetchDashboardOverview(),
        fetchCostSummary(7).catch(() => null),
      ]);
      setData(overview);
      setCost(costSummary);
    } catch (e) {
      console.error('Failed to load dashboard', e);
      setError('加载仪表盘数据失败');
    }
    setLoading(false);
  };

  const switchDays = async (d: number) => {
    setDays(d);
    try {
      const costSummary = await fetchCostSummary(d);
      setCost(costSummary);
    } catch (e) {
      console.error('Failed to load cost summary', e);
    }
  };

  if (loading) {
    return (
      <section className="page">
        <h1>{t('ceoDashboard')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="page">
        <h1>{t('ceoDashboard')}</h1>
        <AIEmptyState
          isError
          errorMessage={error || '无法连接到后台服务'}
          onRetry={loadDashboard}
        />
      </section>
    );
  }

  // 计算 AI 团队状态
  const aiTeamStatus = {
    total: data.ai_employees || 0,
    working: data.running_tasks || 0,
    completed: data.completed_tasks || 0,
    error: data.failed_tasks || 0,
    idle: Math.max(0, (data.ai_employees || 0) - (data.running_tasks || 0) - (data.failed_tasks || 0)),
  };

  // Mock 活动数据（明确标注为演示状态）
  const demoActivities: ActivityItem[] = [
    { id: '1', time: '09:30', aiName: 'DeepSeek', action: '完成东南亚市场分析', status: 'success' as const },
    { id: '2', time: '09:42', aiName: 'Claude', action: '完成代码审查', status: 'success' as const },
    { id: '3', time: '10:05', aiName: 'GPT', action: '生成客户开发方案', status: 'running' as const },
    { id: '4', time: '10:20', aiName: 'Kimi', action: '更新客户资料', status: 'success' as const },
    { id: '5', time: '10:32', aiName: 'Gemini', action: '完成供应商分析', status: 'success' as const },
  ];

  return (
    <section className="page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <h1 style={{ margin: 0 }}>CEO 驾驶舱</h1>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', background: 'rgba(250,204,21,0.1)', padding: '2px 10px', borderRadius: 8 }}>
          ⚡ 演示模式 · 部分数据为 AI 模拟
        </span>
      </div>

      {/* ===== AI 团队概览 ===== */}
      <div className="grid" style={{ marginBottom: 20 }}>
        <div className="card" style={{ borderLeft: '3px solid #4cc9f0' }}>
          <div className="cost-label">在线 AI 员工</div>
          <div className="cost-value" style={{ color: '#4cc9f0' }}>{aiTeamStatus.total}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #4ade80' }}>
          <div className="cost-label">工作中</div>
          <div className="cost-value" style={{ color: '#4ade80' }}>{aiTeamStatus.working}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #facc15' }}>
          <div className="cost-label">等待任务</div>
          <div className="cost-value" style={{ color: '#facc15' }}>{aiTeamStatus.idle}</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #ff6b6b' }}>
          <div className="cost-label">异常</div>
          <div className="cost-value" style={{ color: '#ff6b6b' }}>{aiTeamStatus.error}</div>
        </div>
      </div>

      {/* ===== AI 今日工作 + 活动 + 建议 ===== */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 16, marginBottom: 20 }}>
        {/* 左侧：AI 今日工作 */}
        <div>
          <div className="card" style={{ marginBottom: 12 }}>
            <div className="cost-label" style={{ marginBottom: 12 }}>AI 今日工作</div>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 10, margin: 0 }}>
              <div style={{ textAlign: 'center', padding: '10px 0', background: 'rgba(76,201,240,0.06)', borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#4cc9f0' }}>{data.running_tasks}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>正在执行</div>
              </div>
              <div style={{ textAlign: 'center', padding: '10px 0', background: 'rgba(74,222,128,0.06)', borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#4ade80' }}>{data.completed_tasks}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>已完成</div>
              </div>
              <div style={{ textAlign: 'center', padding: '10px 0', background: 'rgba(255,107,107,0.06)', borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#ff6b6b' }}>{data.failed_tasks}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>异常</div>
              </div>
              <div style={{ textAlign: 'center', padding: '10px 0', background: 'rgba(250,204,21,0.06)', borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#facc15' }}>{data.completed_tasks > 0 ? Math.ceil(data.completed_tasks / 3) : 0}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>待决策</div>
              </div>
            </div>
          </div>

          {/* AI 建议 */}
          <div className="card" style={{ borderLeft: '3px solid #facc15' }}>
            <div className="cost-label" style={{ marginBottom: 8 }}>💡 AI 建议</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
              {data.ai_employees === 0
                ? 'AI 团队尚未配置，请前往 AI 员工中心创建你的第一个 AI 员工。'
                : data.failed_tasks > 0
                  ? `发现 ${data.failed_tasks} 项任务执行异常，建议检查系统日志并重新调度。`
                  : data.running_tasks === 0
                    ? 'AI 团队已就绪，可以开始分配任务。前往工作流中心启动业务流程。'
                    : 'AI 团队正在高效工作，建议定期检查工作流执行状态和输出质量。'}
            </div>
            <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
              <button className="btn btn-submit btn-sm" onClick={() => window.location.href = '/employees'}>
                查看 AI 团队
              </button>
              <button className="btn btn-sm" onClick={() => window.location.href = '/workflow'}>
                管理工作流
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：AI 活动时间线 */}
        <AIActivityFeed
          activities={demoActivities}
          title="AI 活动时间线（演示）"
          maxItems={8}
        />
      </div>

      {/* ===== AI 成本概览 ===== */}
      <div className="cost-days-header">
        <h2 className="section-title" style={{ margin: 0 }}>
          AI 成本概览（近 {cost?.days ?? days} 天）
        </h2>
        <div className="cost-days-tabs">
          {[7, 30, 90].map((d) => (
            <button key={d} className={`cost-days-tab ${days === d ? 'active' : ''}`} onClick={() => switchDays(d)}>
              {d}天
            </button>
          ))}
        </div>
      </div>
      {cost ? (
        <>
          <div className="grid">
            <div className="card">
              <div className="cost-label">累计成本</div>
              <div className="cost-value">{fmtUsd(cost.total_cost_usd)}</div>
              <div className="cost-sub">Token 均价 {cost.total_tokens ? fmtUsd(cost.total_cost_usd / cost.total_tokens * 1000) : '$0.00'}/1K</div>
            </div>
            <div className="card">
              <div className="cost-label">调用次数</div>
              <div className="cost-value">{cost.total_requests}</div>
              <div className="cost-sub">失败 {cost.failed_requests} 次</div>
            </div>
            <div className="card">
              <div className="cost-label">消耗 Token</div>
              <div className="cost-value">{cost.total_tokens.toLocaleString()}</div>
              <div className="cost-sub">近 {cost.days} 天累计</div>
            </div>
            <div className="card">
              <div className="cost-label">平均耗时</div>
              <div className="cost-value">
                {cost.avg_latency_ms > 1000 ? `${(cost.avg_latency_ms / 1000).toFixed(1)}s` : `${Math.round(cost.avg_latency_ms)}ms`}
              </div>
              <div className="cost-sub">单次调用响应</div>
            </div>
          </div>

          {Object.keys(cost.by_provider).length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="cost-label">按 Provider 拆分</div>
              {Object.entries(cost.by_provider).map(([provider, agg]) => (
                <div className="cost-provider-row" key={provider}>
                  <span className="cost-provider-name">{PROVIDER_LABELS[provider] ?? provider}</span>
                  <span className="cost-provider-stat">
                    {agg.requests} 次 · {agg.tokens.toLocaleString()} Tokens · <strong>{fmtUsd(agg.cost_usd)}</strong>
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="card">
          <p>暂无 AI 调用成本数据（执行过 AI 任务后这里会显示费用、Token 与耗时）。</p>
        </div>
      )}

      {/* 系统状态 */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="cost-label">系统状态</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
          <span className="ai-status-dot" style={{ background: data.system_health === 'online' ? '#4ade80' : '#ff6b6b', boxShadow: `0 0 6px ${data.system_health === 'online' ? '#4ade80' : '#ff6b6b'}` }} />
          <span style={{ fontSize: 13 }}>{data.system_health === 'online' ? '系统运行正常' : '系统异常'}</span>
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginLeft: 8 }}>
            最后更新: {data.last_updated ? new Date(data.last_updated).toLocaleString('zh-CN') : 'N/A'}
          </span>
        </div>
      </div>
    </section>
  );
}