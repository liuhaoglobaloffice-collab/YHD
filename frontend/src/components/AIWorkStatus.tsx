import { useMemo } from 'react';

export type AIStatus = 'working' | 'idle' | 'waiting' | 'completed' | 'error' | 'offline';

export interface AIWorkStatusProps {
  name: string;
  status: AIStatus;
  currentTask?: string;
  todayCompleted?: number;
  recentActivity?: string;
  suggestion?: string;
  position?: string;
  model?: string;
  trust_score?: number | null;
  capability_score?: number | null;
  risk_score?: number | null;
  /** 紧凑模式，用于侧边栏/小卡片 */
  compact?: boolean;
}

const STATUS_CONFIG: Record<AIStatus, { label: string; color: string; bg: string; pulse: boolean }> = {
  working:   { label: '工作中',   color: '#4cc9f0', bg: 'rgba(76,201,240,0.12)', pulse: true },
  idle:      { label: '空闲中',   color: '#8fa0e0', bg: 'rgba(143,160,224,0.10)', pulse: false },
  waiting:   { label: '等待任务', color: '#facc15', bg: 'rgba(250,204,21,0.12)', pulse: false },
  completed: { label: '已完成',   color: '#4ade80', bg: 'rgba(74,222,128,0.10)', pulse: false },
  error:     { label: '异常',     color: '#ff6b6b', bg: 'rgba(255,107,107,0.12)', pulse: true },
  offline:   { label: '离线',     color: '#666',    bg: 'rgba(102,102,102,0.08)', pulse: false },
};

/** 获取状态配置（颜色/标签/脉冲），供 AI Core 等 chip 类组件复用同一套视觉。 */
export function getAIStatusConfig(status: AIStatus) {
  return STATUS_CONFIG[status] ?? STATUS_CONFIG.offline;
}

export function AIWorkStatus({ name, status, currentTask, todayCompleted, recentActivity, suggestion, position, model, trust_score, capability_score, risk_score, compact }: AIWorkStatusProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.offline;

  const pulseStyle = cfg.pulse ? { animation: 'ai-pulse 2s ease-in-out infinite' } : {};

  const scoreColor = (label: string, v: number | null | undefined): string => {
    if (v == null || Number.isNaN(v)) return '#888';
    if (label === 'risk') return v >= 0.5 ? '#ff6b6b' : v >= 0.25 ? '#facc15' : '#4ade80';
    // trust / capability: 越高越好
    return v >= 0.7 ? '#4ade80' : v >= 0.4 ? '#facc15' : '#ff6b6b';
  };
  const scorePct = (v: number | null | undefined): number => {
    if (v == null || Number.isNaN(v)) return 0;
    return Math.max(0, Math.min(100, Math.round(Number(v) * 100)));
  };
  const ScoreBadge = ({ label, value }: { label: string; value: number | null | undefined }) => {
    const color = scoreColor(label, value);
    const pct = scorePct(value);
    const text = value == null ? '—' : `${pct}%`;
    return (
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
          <span style={{ color: 'rgba(255,255,255,0.55)' }}>
            {label === 'trust' ? '信任' : label === 'cap' ? '能力' : '风险'}
          </span>
          <span style={{ color, fontWeight: 600 }}>{text}</span>
        </div>
        <div style={{ height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width .4s' }} />
        </div>
      </div>
    );
  };
  const hasScores = trust_score != null || capability_score != null || risk_score != null;

  if (compact) {
    return (
      <div className="ai-status-compact" style={{ borderLeft: `3px solid ${cfg.color}`, paddingLeft: 10, marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="ai-status-dot" style={{ ...pulseStyle, background: cfg.color, boxShadow: `0 0 6px ${cfg.color}` }} />
          <strong style={{ fontSize: 13 }}>{name}</strong>
          <span style={{ fontSize: 11, color: cfg.color, background: cfg.bg, padding: '1px 8px', borderRadius: 8 }}>{cfg.label}</span>
        </div>
        {currentTask && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 2 }}>{currentTask}</div>}
      </div>
    );
  }

  return (
    <div className="ai-status-card" style={{ borderTop: `3px solid ${cfg.color}` }}>
      <div className="ai-status-header">
        <div className="ai-status-left">
          <span className="ai-status-dot" style={{ ...pulseStyle, background: cfg.color, boxShadow: `0 0 8px ${cfg.color}` }} />
          <div>
            <strong className="ai-status-name">{name}</strong>
            {position && <span className="ai-status-position">{position}</span>}
          </div>
        </div>
        <span className="ai-status-badge" style={{ color: cfg.color, background: cfg.bg }}>{cfg.label}</span>
      </div>

      {model && <div className="ai-status-meta">模型: {model}</div>}

      <div className="ai-status-body">
        {currentTask && (
          <div className="ai-status-row">
            <span className="ai-status-label">当前任务</span>
            <span className="ai-status-value">{currentTask}</span>
          </div>
        )}
        {todayCompleted != null && (
          <div className="ai-status-row">
            <span className="ai-status-label">今日完成</span>
            <span className="ai-status-value">{todayCompleted} 项</span>
          </div>
        )}
        {recentActivity && (
          <div className="ai-status-row">
            <span className="ai-status-label">最近活动</span>
            <span className="ai-status-value">{recentActivity}</span>
          </div>
        )}
      </div>

      {hasScores && (
        <div style={{ display: 'flex', gap: 10, padding: '8px 4px 2px', borderTop: '1px dashed rgba(255,255,255,0.08)', marginTop: 6 }}>
          <ScoreBadge label="trust" value={trust_score} />
          <ScoreBadge label="cap" value={capability_score} />
          <ScoreBadge label="risk" value={risk_score} />
        </div>
      )}

      {suggestion && (
        <div className="ai-status-suggestion" style={{ borderLeft: `2px solid ${cfg.color}` }}>
          <span className="ai-status-suggestion-icon">💡</span>
          {suggestion}
        </div>
      )}
    </div>
  );
}

/** 工作状态指示灯（纯圆点） */
export function AIStatusDot({ status, size = 10 }: { status: AIStatus; size?: number }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.offline;
  const pulseStyle = cfg.pulse ? { animation: 'ai-pulse 2s ease-in-out infinite' } : {};
  return (
    <span
      className="ai-status-dot"
      style={{ ...pulseStyle, width: size, height: size, background: cfg.color, boxShadow: `0 0 6px ${cfg.color}`, display: 'inline-block', borderRadius: '50%' }}
    />
  );
}