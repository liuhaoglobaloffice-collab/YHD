import { AIWorkStatus, type AIStatus } from './AIWorkStatus';

export interface AIEmptyStateProps {
  /** 主标题，例如 "AI销售团队已就绪" */
  title: string;
  /** 副标题描述 */
  description?: string;
  /** 当前 AI 状态 */
  aiStatus?: AIStatus;
  /** 当前可执行任务描述 */
  availableTasks?: string[];
  /** 下一步建议 */
  nextStep?: string;
  /** 操作按钮 */
  actionLabel?: string;
  actionDisabled?: boolean;
  onAction?: () => void;
  /** 是否为真正的 API 错误 */
  isError?: boolean;
  errorMessage?: string;
  onRetry?: () => void;
}

export function AIEmptyState({
  title,
  description,
  aiStatus,
  availableTasks,
  nextStep,
  actionLabel,
  actionDisabled,
  onAction,
  isError,
  errorMessage,
  onRetry,
}: AIEmptyStateProps) {
  // 真正的 API 错误：显示错误诊断 + 重试
  if (isError) {
    return (
      <div className="ai-empty-state ai-empty-error">
        <div className="ai-empty-icon">⚠</div>
        <div className="ai-empty-title">服务异常</div>
        <div className="ai-empty-desc">{errorMessage || '系统暂时无法响应，请稍后重试'}</div>

        <div className="ai-empty-diagnosis">
          <div className="ai-empty-diagnosis-title">AI 诊断</div>
          <div className="ai-empty-diagnosis-item">
            <span className="ai-diag-dot" style={{ background: '#ff6b6b' }} />
            服务连接异常
          </div>
          <div className="ai-empty-diagnosis-item">
            <span className="ai-diag-dot" style={{ background: '#facc15' }} />
            建议检查网络连接或稍后重试
          </div>
        </div>

        {onRetry && (
          <button className="btn btn-submit" onClick={onRetry} style={{ marginTop: 16 }}>
            重新连接
          </button>
        )}
      </div>
    );
  }

  // 正常空状态：AI 准备就绪
  return (
    <div className="ai-empty-state">
      <div className="ai-empty-pulse">
        <span className="ai-empty-pulse-dot" />
      </div>
      <div className="ai-empty-title">{title}</div>
      {description && <div className="ai-empty-desc">{description}</div>}

      {/* AI 当前状态 */}
      {aiStatus && (
        <div className="ai-empty-status">
          <AIWorkStatus
            name="AI 助手"
            status={aiStatus}
            compact
          />
        </div>
      )}

      {/* 可执行任务 */}
      {availableTasks && availableTasks.length > 0 && (
        <div className="ai-empty-tasks">
          <div className="ai-empty-tasks-title">当前可执行任务</div>
          {availableTasks.map((task, i) => (
            <div key={i} className="ai-empty-task-item">
              <span className="ai-empty-task-dot">→</span>
              {task}
            </div>
          ))}
        </div>
      )}

      {/* 下一步建议 */}
      {nextStep && (
        <div className="ai-empty-next">
          <span className="ai-empty-next-icon">💡</span>
          {nextStep}
        </div>
      )}

      {/* 操作按钮 */}
      {actionLabel && onAction && (
        <button className="btn btn-submit" onClick={onAction} disabled={actionDisabled} style={{ marginTop: 16 }}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}