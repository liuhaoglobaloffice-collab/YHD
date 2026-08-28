import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AIActivityFeed, type ActivityItem } from './AIActivityFeed';

const sampleActivities: ActivityItem[] = [
  { id: '1', time: '09:30', aiName: 'DeepSeek', action: '完成市场分析', status: 'success' },
  { id: '2', time: '09:42', aiName: 'Claude', action: '代码审查中', status: 'running', detail: '审查 3 个文件' },
  { id: '3', time: '10:05', aiName: 'GPT', action: '生成方案', status: 'failed', detail: 'API 超时' },
  { id: '4', time: '10:20', aiName: 'Kimi', action: '更新资料', status: 'pending' },
];

describe('AIActivityFeed', () => {
  // ===== 基础渲染 =====
  it('渲染标题', () => {
    render(<AIActivityFeed activities={[]} title="AI 活动" />);
    expect(screen.getByText('AI 活动')).toBeInTheDocument();
  });

  it('渲染活动列表', () => {
    render(<AIActivityFeed activities={sampleActivities} />);
    expect(screen.getByText('DeepSeek')).toBeInTheDocument();
    expect(screen.getByText('Claude')).toBeInTheDocument();
    expect(screen.getByText('GPT')).toBeInTheDocument();
    expect(screen.getByText('Kimi')).toBeInTheDocument();
  });

  it('渲染活动时间', () => {
    render(<AIActivityFeed activities={sampleActivities} />);
    expect(screen.getByText('09:30')).toBeInTheDocument();
    expect(screen.getByText('10:05')).toBeInTheDocument();
  });

  it('渲染活动动作', () => {
    render(<AIActivityFeed activities={sampleActivities} />);
    expect(screen.getByText('完成市场分析')).toBeInTheDocument();
    expect(screen.getByText('代码审查中')).toBeInTheDocument();
  });

  // ===== 空状态 =====
  it('空状态显示默认消息', () => {
    render(<AIActivityFeed activities={[]} />);
    expect(screen.getByText('暂无 AI 活动记录')).toBeInTheDocument();
  });

  it('空状态显示自定义消息', () => {
    render(<AIActivityFeed activities={[]} emptyMessage="暂无活动" />);
    expect(screen.getByText('暂无活动')).toBeInTheDocument();
  });

  it('空状态不显示标题', () => {
    const { container } = render(<AIActivityFeed activities={[]} title="测试" />);
    // 标题应显示，但空状态消息也要显示
    expect(screen.getByText('测试')).toBeInTheDocument();
    expect(screen.getByText('暂无 AI 活动记录')).toBeInTheDocument();
  });

  // ===== maxItems 限制 =====
  it('默认最多显示 10 条', () => {
    const many = Array.from({ length: 15 }, (_, i) => ({
      id: String(i), time: '10:00', aiName: `AI-${i}`, action: '任务', status: 'success' as const,
    }));
    render(<AIActivityFeed activities={many} />);
    // 第 0 条和第 9 条应显示，第 10 条不应显示
    expect(screen.getByText('AI-0')).toBeInTheDocument();
    expect(screen.getByText('AI-9')).toBeInTheDocument();
    expect(screen.queryByText('AI-10')).not.toBeInTheDocument();
  });

  it('支持自定义 maxItems', () => {
    const many = Array.from({ length: 5 }, (_, i) => ({
      id: String(i), time: '10:00', aiName: `AI-${i}`, action: '任务', status: 'success' as const,
    }));
    render(<AIActivityFeed activities={many} maxItems={2} />);
    expect(screen.getByText('AI-0')).toBeInTheDocument();
    expect(screen.getByText('AI-1')).toBeInTheDocument();
    expect(screen.queryByText('AI-2')).not.toBeInTheDocument();
  });

  // ===== 状态图标和颜色 =====
  it('success 状态显示 ✓ 和 成功', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[0]]} />);
    const statusEl = container.querySelector('.ai-activity-status');
    expect(statusEl?.textContent).toContain('✓');
    expect(statusEl?.textContent).toContain('成功');
  });

  it('running 状态显示 ◉ 和 执行中', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[1]]} />);
    const statusEl = container.querySelector('.ai-activity-status');
    expect(statusEl?.textContent).toContain('◉');
    expect(statusEl?.textContent).toContain('执行中');
  });

  it('failed 状态显示 ✕ 和 失败', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[2]]} />);
    const statusEl = container.querySelector('.ai-activity-status');
    expect(statusEl?.textContent).toContain('✕');
    expect(statusEl?.textContent).toContain('失败');
  });

  it('pending 状态显示 ○ 和 等待', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[3]]} />);
    const statusEl = container.querySelector('.ai-activity-status');
    expect(statusEl?.textContent).toContain('○');
    expect(statusEl?.textContent).toContain('等待');
  });

  it('无 status 时不显示状态标签', () => {
    const noStatus: ActivityItem[] = [{ id: '5', time: '11:00', aiName: 'AI', action: '任务' }];
    const { container } = render(<AIActivityFeed activities={noStatus} />);
    expect(container.querySelector('.ai-activity-status')).not.toBeInTheDocument();
  });

  // ===== detail =====
  it('显示活动详情', () => {
    render(<AIActivityFeed activities={[sampleActivities[1]]} />);
    expect(screen.getByText('审查 3 个文件')).toBeInTheDocument();
  });

  it('无 detail 时不显示详情', () => {
    render(<AIActivityFeed activities={[sampleActivities[0]]} />);
    expect(screen.queryByText('审查 3 个文件')).not.toBeInTheDocument();
  });

  // ===== 紧凑模式 =====
  it('紧凑模式添加 ai-activity-compact class', () => {
    const { container } = render(<AIActivityFeed activities={sampleActivities} compact />);
    expect(container.querySelector('.ai-activity-compact')).toBeInTheDocument();
  });

  it('非紧凑模式没有 compact class', () => {
    const { container } = render(<AIActivityFeed activities={sampleActivities} />);
    expect(container.querySelector('.ai-activity-compact')).not.toBeInTheDocument();
  });

  // ===== 时间线连接线 =====
  it('多条活动时显示连接线', () => {
    const { container } = render(<AIActivityFeed activities={sampleActivities} />);
    const connectors = container.querySelectorAll('.ai-activity-connector');
    // 4 条活动应有 3 条连接线
    expect(connectors.length).toBe(3);
  });

  it('单条活动不显示连接线', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[0]]} />);
    expect(container.querySelector('.ai-activity-connector')).not.toBeInTheDocument();
  });

  // ===== 不同状态主题色 =====
  it('success 状态圆点颜色正确', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[0]]} />);
    const dot = container.querySelector('.ai-activity-dot');
    expect(dot).toHaveStyle({ borderColor: '#4ade80' });
  });

  it('running 状态圆点颜色正确', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[1]]} />);
    const dot = container.querySelector('.ai-activity-dot');
    expect(dot).toHaveStyle({ borderColor: '#4cc9f0' });
  });

  it('failed 状态圆点颜色正确', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[2]]} />);
    const dot = container.querySelector('.ai-activity-dot');
    expect(dot).toHaveStyle({ borderColor: '#ff6b6b' });
  });

  it('pending 状态圆点颜色正确', () => {
    const { container } = render(<AIActivityFeed activities={[sampleActivities[3]]} />);
    const dot = container.querySelector('.ai-activity-dot');
    expect(dot).toHaveStyle({ borderColor: '#facc15' });
  });
});