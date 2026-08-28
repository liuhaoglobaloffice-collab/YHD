import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AIWorkStatus, AIStatusDot, type AIStatus } from './AIWorkStatus';

describe('AIWorkStatus', () => {
  // ===== 基础渲染 =====
  it('渲染员工名称和状态标签', () => {
    render(<AIWorkStatus name="DeepSeek" status="working" />);
    expect(screen.getByText('DeepSeek')).toBeInTheDocument();
    expect(screen.getByText('工作中')).toBeInTheDocument();
  });

  it('渲染职位信息', () => {
    render(<AIWorkStatus name="Claude" status="idle" position="分析师" />);
    expect(screen.getByText('分析师')).toBeInTheDocument();
  });

  it('渲染模型信息', () => {
    render(<AIWorkStatus name="GPT" status="working" model="gpt-4" />);
    expect(screen.getByText('模型: gpt-4')).toBeInTheDocument();
  });

  // ===== 6 种状态各自渲染正确 =====
  it.each([
    ['working', '工作中'],
    ['idle', '空闲中'],
    ['waiting', '等待任务'],
    ['completed', '已完成'],
    ['error', '异常'],
    ['offline', '离线'],
  ] as [AIStatus, string][])('状态 %s 显示标签 %s', (status, label) => {
    render(<AIWorkStatus name="AI" status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  // ===== currentTask =====
  it('显示当前任务', () => {
    render(<AIWorkStatus name="AI" status="working" currentTask="分析市场数据" />);
    expect(screen.getByText('当前任务')).toBeInTheDocument();
    expect(screen.getByText('分析市场数据')).toBeInTheDocument();
  });

  it('不传 currentTask 时不显示任务行', () => {
    const { container } = render(<AIWorkStatus name="AI" status="idle" />);
    expect(container.querySelector('.ai-status-row')).not.toBeInTheDocument();
  });

  // ===== todayCompleted =====
  it('显示今日完成数量', () => {
    render(<AIWorkStatus name="AI" status="working" todayCompleted={5} />);
    expect(screen.getByText('今日完成')).toBeInTheDocument();
    expect(screen.getByText('5 项')).toBeInTheDocument();
  });

  it('todayCompleted=0 时显示 0 项', () => {
    render(<AIWorkStatus name="AI" status="working" todayCompleted={0} />);
    expect(screen.getByText('0 项')).toBeInTheDocument();
  });

  it('todayCompleted 大数显示正确', () => {
    render(<AIWorkStatus name="AI" status="working" todayCompleted={999} />);
    expect(screen.getByText('999 项')).toBeInTheDocument();
  });

  // ===== recentActivity =====
  it('显示最近活动', () => {
    render(<AIWorkStatus name="AI" status="working" recentActivity="刚刚完成代码审查" />);
    expect(screen.getByText('最近活动')).toBeInTheDocument();
    expect(screen.getByText('刚刚完成代码审查')).toBeInTheDocument();
  });

  // ===== suggestion =====
  it('显示 AI 建议', () => {
    render(<AIWorkStatus name="AI" status="idle" suggestion="该员工已就绪" />);
    expect(screen.getByText('💡')).toBeInTheDocument();
    expect(screen.getByText('该员工已就绪')).toBeInTheDocument();
  });

  it('不传 suggestion 时不显示建议区域', () => {
    const { container } = render(<AIWorkStatus name="AI" status="working" />);
    expect(container.querySelector('.ai-status-suggestion')).not.toBeInTheDocument();
  });

  // ===== 紧凑模式 =====
  it('紧凑模式渲染正确', () => {
    const { container } = render(<AIWorkStatus name="AI" status="working" compact />);
    expect(container.querySelector('.ai-status-compact')).toBeInTheDocument();
    expect(container.querySelector('.ai-status-card')).not.toBeInTheDocument();
  });

  it('紧凑模式显示名称和状态标签', () => {
    render(<AIWorkStatus name="DeepSeek" status="error" compact />);
    expect(screen.getByText('DeepSeek')).toBeInTheDocument();
    expect(screen.getByText('异常')).toBeInTheDocument();
  });

  it('紧凑模式显示当前任务', () => {
    render(<AIWorkStatus name="AI" status="working" currentTask="分析中" compact />);
    expect(screen.getByText('分析中')).toBeInTheDocument();
  });

  // ===== 未知状态降级 =====
  it('未知状态降级为 offline', () => {
    // @ts-expect-error 测试非法状态降级
    render(<AIWorkStatus name="AI" status="unknown" />);
    expect(screen.getByText('离线')).toBeInTheDocument();
  });

  // ===== 完整模式 vs 紧凑模式互斥 =====
  it('完整模式包含状态卡片容器', () => {
    const { container } = render(<AIWorkStatus name="AI" status="working" />);
    expect(container.querySelector('.ai-status-card')).toBeInTheDocument();
  });

  // ===== 所有数据同时渲染 =====
  it('同时渲染所有信息', () => {
    render(
      <AIWorkStatus
        name="GPT"
        status="working"
        position="数据科学家"
        model="gpt-4"
        currentTask="分析市场趋势"
        todayCompleted={3}
        recentActivity="完成客户分析报告"
        suggestion="建议查看输出结果"
      />,
    );
    expect(screen.getByText('GPT')).toBeInTheDocument();
    expect(screen.getByText('数据科学家')).toBeInTheDocument();
    expect(screen.getByText('模型: gpt-4')).toBeInTheDocument();
    expect(screen.getByText('工作中')).toBeInTheDocument();
    expect(screen.getByText('分析市场趋势')).toBeInTheDocument();
    expect(screen.getByText('3 项')).toBeInTheDocument();
    expect(screen.getByText('完成客户分析报告')).toBeInTheDocument();
    expect(screen.getByText('建议查看输出结果')).toBeInTheDocument();
  });

  // ===== working 状态应有脉冲动画 =====
  it('working 状态圆点有脉冲动画', () => {
    const { container } = render(<AIWorkStatus name="AI" status="working" />);
    const dot = container.querySelector('.ai-status-dot');
    expect(dot).toHaveStyle({ animation: 'ai-pulse 2s ease-in-out infinite' });
  });

  it('idle 状态圆点无脉冲动画', () => {
    const { container } = render(<AIWorkStatus name="AI" status="idle" />);
    const dot = container.querySelector('.ai-status-dot');
    expect(dot).not.toHaveStyle({ animation: 'ai-pulse 2s ease-in-out infinite' });
  });

  it('error 状态有脉冲动画', () => {
    const { container } = render(<AIWorkStatus name="AI" status="error" />);
    const dot = container.querySelector('.ai-status-dot');
    expect(dot).toHaveStyle({ animation: 'ai-pulse 2s ease-in-out infinite' });
  });

  it('offline 状态无脉冲动画', () => {
    const { container } = render(<AIWorkStatus name="AI" status="offline" />);
    const dot = container.querySelector('.ai-status-dot');
    expect(dot).not.toHaveStyle({ animation: 'ai-pulse 2s ease-in-out infinite' });
  });

  // ===== 边界：超长文本 =====
  it('超长名称不截断', () => {
    const longName = '一个非常长的 AI 员工名称是用来测试布局的'.repeat(3);
    render(<AIWorkStatus name={longName} status="working" />);
    expect(screen.getByText(longName)).toBeInTheDocument();
  });

  it('超长任务描述不截断', () => {
    const longTask = '这是一个非常长的任务描述，用来测试卡片布局在超长文本下的表现是否正常，不会出现布局断裂或文本溢出问题。'.repeat(5);
    render(<AIWorkStatus name="AI" status="working" currentTask={longTask} />);
    expect(screen.getByText(longTask)).toBeInTheDocument();
  });

  it('超长建议不截断', () => {
    const longSuggestion = '这是一个非常长的 AI 建议，用来测试建议区域在超长文本下的表现是否正常，不会出现布局断裂或文本溢出问题。'.repeat(5);
    render(<AIWorkStatus name="AI" status="idle" suggestion={longSuggestion} />);
    expect(screen.getByText(longSuggestion)).toBeInTheDocument();
  });

  // ===== 边界：空字符串 =====
  it('name 为空字符串时渲染空名称', () => {
    render(<AIWorkStatus name="" status="working" />);
    // 不应崩溃，名称区域存在但为空
    const { container } = render(<AIWorkStatus name="" status="working" />);
    expect(container.querySelector('.ai-status-name')).toBeInTheDocument();
  });

  it('position 为空字符串时渲染空职位', () => {
    render(<AIWorkStatus name="AI" status="working" position="" />);
    expect(screen.getByText('AI')).toBeInTheDocument();
  });

  it('model 为空字符串时不渲染模型行（空字符串为 falsy）', () => {
    const { container } = render(<AIWorkStatus name="AI" status="working" model="" />);
    expect(container.querySelector('.ai-status-meta')).not.toBeInTheDocument();
  });

  // ===== 边界：todayCompleted 未定义时不显示 =====
  it('todayCompleted 未定义时不显示完成行', () => {
    const { container } = render(<AIWorkStatus name="AI" status="working" />);
    expect(container.querySelector('.ai-status-row')).not.toBeInTheDocument();
  });

  // ===== 边界：compact 模式下 no suggestion =====
  it('紧凑模式不显示建议', () => {
    const { container } = render(<AIWorkStatus name="AI" status="idle" suggestion="建议" compact />);
    expect(container.querySelector('.ai-status-suggestion')).not.toBeInTheDocument();
  });
});

describe('AIStatusDot', () => {
  it('渲染状态圆点', () => {
    const { container } = render(<AIStatusDot status="working" />);
    const dot = container.firstChild;
    expect(dot).toBeInTheDocument();
    expect(dot).toHaveStyle({ borderRadius: '50%' });
  });

  it('working 状态有脉冲动画', () => {
    const { container } = render(<AIStatusDot status="working" />);
    expect(container.firstChild).toHaveStyle({ animation: 'ai-pulse 2s ease-in-out infinite' });
  });

  it('idle 状态无脉冲动画', () => {
    const { container } = render(<AIStatusDot status="idle" />);
    expect(container.firstChild).not.toHaveStyle({ animation: 'ai-pulse 2s ease-in-out infinite' });
  });

  it('error 状态有脉冲动画', () => {
    const { container } = render(<AIStatusDot status="error" />);
    expect(container.firstChild).toHaveStyle({ animation: 'ai-pulse 2s ease-in-out infinite' });
  });

  it('未知状态降级为 offline', () => {
    // @ts-expect-error 测试非法状态降级
    const { container } = render(<AIStatusDot status="unknown" />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('支持自定义尺寸', () => {
    const { container } = render(<AIStatusDot status="working" size={16} />);
    expect(container.firstChild).toHaveStyle({ width: '16px', height: '16px' });
  });

  it('默认尺寸为 10px', () => {
    const { container } = render(<AIStatusDot status="working" />);
    expect(container.firstChild).toHaveStyle({ width: '10px', height: '10px' });
  });

  it('自定义最小尺寸 4px', () => {
    const { container } = render(<AIStatusDot status="working" size={4} />);
    expect(container.firstChild).toHaveStyle({ width: '4px', height: '4px' });
  });

  it('自定义最大尺寸 32px', () => {
    const { container } = render(<AIStatusDot status="working" size={32} />);
    expect(container.firstChild).toHaveStyle({ width: '32px', height: '32px' });
  });
});