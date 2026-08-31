import { useState } from 'react';
import { summarizeActivity, type LiveActivity } from '../services/live';

/**
 * GlobalAIStatusBar — 全局「AI 正在工作」状态条（Y1.0）。
 *
 * 挂载在 Layout 中，出现在每一个核心页面顶部：
 * - 数据由 Layout 统一轮询 /dashboard/live-activity 后通过 props 注入（全站单一数据源，不再自行轮询）
 * - 展示：在岗 AI 员工数 / 执行中任务 / 最近成败 / 模型调用活动 / 知识记忆活动
 * - 让用户在任何页面都能感知「这是一个正在工作的 AI 企业操作系统」
 */
export function GlobalAIStatusBar({ live }: { live: LiveActivity | null }) {
  const [expanded, setExpanded] = useState(false);

  if (!live) {
    return (
      <div className="ai-live-bar ai-live-bar-error" role="status">
        <span className="ai-live-dot" style={{ background: '#ff6b6b' }} />
        <span>AI 系统连接中…</span>
      </div>
    );
  }

  const { headline, detail, tone } = summarizeActivity(live);
  const toneColor =
    tone === 'working' ? '#4cc9f0' : tone === 'error' ? '#ff6b6b' : '#8fa0e0';
  const lastCall = live.model_calls?.[0];
  const lastMemory = live.knowledge?.memory_activity?.[0];

  return (
    <div
      className="ai-live-bar"
      role="status"
      aria-live="polite"
      onClick={() => setExpanded((v) => !v)}
      style={{ cursor: 'pointer', borderLeft: `3px solid ${toneColor}` }}
    >
      <div className="ai-live-bar-main">
        <span
          className="ai-live-dot"
          style={{
            background: toneColor,
            boxShadow: `0 0 6px ${toneColor}`,
            animation: tone === 'working' ? 'ai-pulse 2s ease-in-out infinite' : 'none',
          }}
        />
        <strong style={{ color: toneColor }}>{headline}</strong>
        {detail && <span className="ai-live-detail">{detail}</span>}
        <span className="ai-live-expand-hint">{expanded ? '收起 ▲' : '详情 ▼'}</span>
      </div>

      {expanded && (
        <div className="ai-live-bar-expanded">
          <div className="ai-live-col">
            <div className="ai-live-col-title">AI 员工（{live.active_employees}/{live.total_employees} 在岗）</div>
            {live.employees.slice(0, 6).map((e) => (
              <div key={e.id} className="ai-live-row">
                <span
                  className="ai-live-dot"
                  style={{
                    width: 6,
                    height: 6,
                    background:
                      e.status === 'active' ? '#4ade80' : e.status === 'created' ? '#facc15' : '#666',
                  }}
                />
                <span className="ai-live-name">{e.name}</span>
                <span className="ai-live-sub">{e.position || e.department || ''}</span>
                <span className="ai-live-sub">{e.provider ? `${e.provider}${e.model ? `/${e.model}` : ''}` : ''}</span>
              </div>
            ))}
          </div>

          <div className="ai-live-col">
            <div className="ai-live-col-title">最近执行</div>
            {live.recent_tasks.slice(0, 5).map((t) => (
              <div key={t.id} className="ai-live-row">
                <span
                  className="ai-live-dot"
                  style={{
                    width: 6,
                    height: 6,
                    background:
                      t.status === 'completed' ? '#4ade80' : t.status === 'failed' ? '#ff6b6b' : '#4cc9f0',
                  }}
                />
                <span className="ai-live-name">{t.title}</span>
                <span className="ai-live-sub">{t.summary || t.error || t.status}</span>
              </div>
            ))}
            {live.recent_tasks.length === 0 && <div className="ai-live-row ai-live-sub">暂无执行记录</div>}
          </div>

          <div className="ai-live-col">
            <div className="ai-live-col-title">目标进度</div>
            {live.goals.slice(0, 4).map((g) => (
              <div key={g.id} className="ai-live-row">
                <span className="ai-live-name">{g.title}</span>
                <span className="ai-live-sub">
                  {g.status} · {g.progress_pct ?? 0}%
                  {g.kpi_name ? ` · ${g.kpi_name} ${g.kpi_current ?? 0}/${g.kpi_target ?? '—'}` : ''}
                  {g.budget_total ? ` · 预算 $${g.budget_spent ?? 0}/${g.budget_total}` : ''}
                </span>
              </div>
            ))}
            {live.goals.length === 0 && <div className="ai-live-row ai-live-sub">暂无目标</div>}
          </div>

          <div className="ai-live-col">
            <div className="ai-live-col-title">模型 · 知识 · 审计</div>
            {lastCall && (
              <div className="ai-live-row">
                <span className="ai-live-dot" style={{ width: 6, height: 6, background: '#4cc9f0' }} />
                <span className="ai-live-name">模型调用</span>
                <span className="ai-live-sub">
                  {lastCall.provider}/{lastCall.model} · {lastCall.total_tokens ?? 0} tokens · {lastCall.status}
                </span>
              </div>
            )}
            {lastMemory && (
              <div className="ai-live-row">
                <span className="ai-live-dot" style={{ width: 6, height: 6, background: '#a78bfa' }} />
                <span className="ai-live-name">{lastMemory.agent_name} 写入记忆</span>
                <span className="ai-live-sub">{lastMemory.excerpt}</span>
              </div>
            )}
            {live.knowledge?.documents > 0 && (
              <div className="ai-live-row">
                <span className="ai-live-dot" style={{ width: 6, height: 6, background: '#4ade80' }} />
                <span className="ai-live-name">企业知识库</span>
                <span className="ai-live-sub">{live.knowledge.documents} 份文档已索引</span>
              </div>
            )}
            {live.audit_activity?.[0] && (
              <div className="ai-live-row">
                <span className="ai-live-dot" style={{ width: 6, height: 6, background: '#8fa0e0' }} />
                <span className="ai-live-name">审计</span>
                <span className="ai-live-sub">
                  {live.audit_activity[0].action} · {live.audit_activity[0].status}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
