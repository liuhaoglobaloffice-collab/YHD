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

export function AIWorkStatus({ name, status, currentTask, todayCompleted, recentActivity, suggestion, position, model, compact }: AIWorkStatusProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.offline;

  const pulseStyle = cfg.pulse ? { animation: 'ai-pulse 2s ease-in-out infinite' } : {};

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