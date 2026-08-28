import { useMemo } from 'react';

export interface ActivityItem {
  id: string;
  time: string;       // e.g. "09:30"
  aiName: string;
  action: string;
  status?: 'success' | 'running' | 'failed' | 'pending';
  detail?: string;
}

export interface AIActivityFeedProps {
  activities: ActivityItem[];
  /** 标题 */
  title?: string;
  /** 最大显示条数 */
  maxItems?: number;
  /** 无活动时显示的消息 */
  emptyMessage?: string;
  /** 紧凑模式 */
  compact?: boolean;
}

const STATUS_ICONS: Record<string, string> = {
  success: '✓',
  running: '◉',
  failed: '✕',
  pending: '○',
};

const STATUS_COLORS: Record<string, string> = {
  success: '#4ade80',
  running: '#4cc9f0',
  failed: '#ff6b6b',
  pending: '#facc15',
};

export function AIActivityFeed({ activities, title, maxItems = 10, emptyMessage, compact }: AIActivityFeedProps) {
  const items = useMemo(() => activities.slice(0, maxItems), [activities, maxItems]);

  return (
    <div className={`ai-activity-feed ${compact ? 'ai-activity-compact' : ''}`}>
      {title && <div className="ai-activity-title">{title}</div>}

      {items.length === 0 ? (
        <div className="ai-activity-empty">
          {emptyMessage || '暂无 AI 活动记录'}
        </div>
      ) : (
        <div className="ai-activity-list">
          {items.map((item, idx) => (
            <div key={item.id} className="ai-activity-item">
              {/* 时间线 */}
              <div className="ai-activity-timeline">
                <span className="ai-activity-time">{item.time}</span>
                <div className="ai-activity-line">
                  <span
                    className="ai-activity-dot"
                    style={{ borderColor: STATUS_COLORS[item.status ?? 'success'] ?? '#4cc9f0' }}
                  >
                    {item.status ? STATUS_ICONS[item.status] ?? '●' : '●'}
                  </span>
                  {idx < items.length - 1 && <div className="ai-activity-connector" />}
                </div>
              </div>
              {/* 内容 */}
              <div className="ai-activity-content">
                <div className="ai-activity-main">
                  <strong className="ai-activity-ai">{item.aiName}</strong>
                  <span className="ai-activity-action">{item.action}</span>
                  {item.status && (
                    <span className="ai-activity-status" style={{ color: STATUS_COLORS[item.status] }}>
                      {STATUS_ICONS[item.status]} {item.status === 'success' ? '成功' : item.status === 'running' ? '执行中' : item.status === 'failed' ? '失败' : '等待'}
                    </span>
                  )}
                </div>
                {item.detail && <div className="ai-activity-detail">{item.detail}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}