import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AIEmptyState } from './AIEmptyState';

describe('AIEmptyState', () => {
  // ===== 基础渲染 =====
  it('渲染标题', () => {
    render(<AIEmptyState title="AI 就绪" />);
    expect(screen.getByText('AI 就绪')).toBeInTheDocument();
  });

  it('渲染描述', () => {
    render(<AIEmptyState title="就绪" description="等待任务分配" />);
    expect(screen.getByText('等待任务分配')).toBeInTheDocument();
  });

  // ===== 正常空状态 =====
  it('显示脉冲动画圆点', () => {
    const { container } = render(<AIEmptyState title="就绪" />);
    expect(container.querySelector('.ai-empty-pulse-dot')).toBeInTheDocument();
  });

  it('渲染 AI 状态组件', () => {
    render(<AIEmptyState title="就绪" aiStatus="waiting" />);
    expect(screen.getByText('AI 助手')).toBeInTheDocument();
    expect(screen.getByText('等待任务')).toBeInTheDocument();
  });

  // ===== availableTasks =====
  it('渲染可执行任务列表', () => {
    render(<AIEmptyState title="就绪" availableTasks={['任务 A', '任务 B', '任务 C']} />);
    expect(screen.getByText('当前可执行任务')).toBeInTheDocument();
    expect(screen.getByText('任务 A')).toBeInTheDocument();
    expect(screen.getByText('任务 B')).toBeInTheDocument();
    expect(screen.getByText('任务 C')).toBeInTheDocument();
  });

  it('空任务列表不显示', () => {
    const { container } = render(<AIEmptyState title="就绪" availableTasks={[]} />);
    expect(container.querySelector('.ai-empty-tasks')).not.toBeInTheDocument();
  });

  it('不传 availableTasks 时不显示', () => {
    const { container } = render(<AIEmptyState title="就绪" />);
    expect(container.querySelector('.ai-empty-tasks')).not.toBeInTheDocument();
  });

  // ===== nextStep =====
  it('渲染下一步建议', () => {
    render(<AIEmptyState title="就绪" nextStep="建议先创建任务" />);
    expect(screen.getByText('建议先创建任务')).toBeInTheDocument();
  });

  it('不传 nextStep 时不显示', () => {
    const { container } = render(<AIEmptyState title="就绪" />);
    expect(container.querySelector('.ai-empty-next')).not.toBeInTheDocument();
  });

  // ===== 操作按钮 =====
  it('渲染操作按钮', () => {
    const fn = vi.fn();
    render(<AIEmptyState title="就绪" actionLabel="开始" onAction={fn} />);
    expect(screen.getByText('开始')).toBeInTheDocument();
  });

  it('点击操作按钮触发回调', () => {
    const fn = vi.fn();
    render(<AIEmptyState title="就绪" actionLabel="开始" onAction={fn} />);
    fireEvent.click(screen.getByText('开始'));
    expect(fn).toHaveBeenCalledOnce();
  });

  it('不传 actionLabel 时不显示按钮', () => {
    const { container } = render(<AIEmptyState title="就绪" />);
    expect(container.querySelector('.btn-submit')).not.toBeInTheDocument();
  });

  it('按钮可被禁用', () => {
    const fn = vi.fn();
    render(<AIEmptyState title="就绪" actionLabel="开始" onAction={fn} actionDisabled />);
    const btn = screen.getByText('开始');
    expect(btn).toBeDisabled();
  });

  // ===== 错误状态 =====
  it('错误状态显示警告图标', () => {
    render(<AIEmptyState title="就绪" isError />);
    expect(screen.getByText('⚠')).toBeInTheDocument();
  });

  it('错误状态显示"服务异常"', () => {
    render(<AIEmptyState title="就绪" isError />);
    expect(screen.getByText('服务异常')).toBeInTheDocument();
  });

  it('错误状态显示自定义错误消息', () => {
    render(<AIEmptyState title="就绪" isError errorMessage="连接超时" />);
    expect(screen.getByText('连接超时')).toBeInTheDocument();
  });

  it('错误状态显示默认错误消息', () => {
    render(<AIEmptyState title="就绪" isError />);
    expect(screen.getByText('系统暂时无法响应，请稍后重试')).toBeInTheDocument();
  });

  it('错误状态显示 AI 诊断', () => {
    render(<AIEmptyState title="就绪" isError />);
    expect(screen.getByText('AI 诊断')).toBeInTheDocument();
    expect(screen.getByText('服务连接异常')).toBeInTheDocument();
    expect(screen.getByText('建议检查网络连接或稍后重试')).toBeInTheDocument();
  });

  it('错误状态显示重新连接按钮', () => {
    const fn = vi.fn();
    render(<AIEmptyState title="就绪" isError onRetry={fn} />);
    expect(screen.getByText('重新连接')).toBeInTheDocument();
  });

  it('点击重新连接触发回调', () => {
    const fn = vi.fn();
    render(<AIEmptyState title="就绪" isError onRetry={fn} />);
    fireEvent.click(screen.getByText('重新连接'));
    expect(fn).toHaveBeenCalledOnce();
  });

  it('错误状态不传 onRetry 时不显示按钮', () => {
    render(<AIEmptyState title="就绪" isError />);
    expect(screen.queryByText('重新连接')).not.toBeInTheDocument();
  });

  // ===== 正常状态 vs 错误状态互斥 =====
  it('正常状态不显示诊断区域', () => {
    const { container } = render(<AIEmptyState title="就绪" />);
    expect(container.querySelector('.ai-empty-diagnosis')).not.toBeInTheDocument();
  });

  it('错误状态不显示脉冲圆点', () => {
    const { container } = render(<AIEmptyState title="就绪" isError />);
    expect(container.querySelector('.ai-empty-pulse-dot')).not.toBeInTheDocument();
  });

  it('错误状态不显示操作按钮', () => {
    render(<AIEmptyState title="就绪" isError actionLabel="开始" onAction={() => {}} />);
    expect(screen.queryByText('开始')).not.toBeInTheDocument();
  });

  // ===== 全量数据同时渲染 =====
  it('同时渲染所有正常状态元素', () => {
    render(
      <AIEmptyState
        title="AI 销售团队已就绪"
        description="等待启动客户开发任务"
        aiStatus="waiting"
        availableTasks={['任务 A', '任务 B']}
        nextStep="建议先创建任务"
        actionLabel="开始"
        onAction={() => {}}
      />,
    );
    expect(screen.getByText('AI 销售团队已就绪')).toBeInTheDocument();
    expect(screen.getByText('等待启动客户开发任务')).toBeInTheDocument();
    expect(screen.getByText('AI 助手')).toBeInTheDocument();
    expect(screen.getByText('等待任务')).toBeInTheDocument();
    expect(screen.getByText('任务 A')).toBeInTheDocument();
    expect(screen.getByText('建议先创建任务')).toBeInTheDocument();
    expect(screen.getByText('开始')).toBeInTheDocument();
  });

  it('同时渲染所有错误状态元素', () => {
    const fn = vi.fn();
    render(
      <AIEmptyState
        title="忽略"
        isError
        errorMessage="服务不可用"
        onRetry={fn}
      />,
    );
    expect(screen.getByText('⚠')).toBeInTheDocument();
    expect(screen.getByText('服务异常')).toBeInTheDocument();
    expect(screen.getByText('服务不可用')).toBeInTheDocument();
    expect(screen.getByText('AI 诊断')).toBeInTheDocument();
    expect(screen.getByText('重新连接')).toBeInTheDocument();
  });
});