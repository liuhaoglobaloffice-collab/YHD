import type { Meta, StoryObj } from '@storybook/react';
import { AIWorkStatus, AIStatusDot } from './AIWorkStatus';
import '../index.css';

const meta = {
  title: 'Components/AIWorkStatus',
  component: AIWorkStatus,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
    backgrounds: { default: 'dark' },
  },
  argTypes: {
    status: {
      control: 'select',
      options: ['working', 'idle', 'waiting', 'completed', 'error', 'offline'],
      description: 'AI 工作状态',
    },
    name: { control: 'text', description: 'AI 员工名称' },
    position: { control: 'text', description: '职位' },
    model: { control: 'text', description: '使用模型' },
    currentTask: { control: 'text', description: '当前任务描述' },
    todayCompleted: { control: 'number', description: '今日完成任务数' },
    recentActivity: { control: 'text', description: '最近活动' },
    suggestion: { control: 'text', description: 'AI 建议' },
    compact: { control: 'boolean', description: '紧凑模式' },
  },
} satisfies Meta<typeof AIWorkStatus>;

export default meta;
type Story = StoryObj<typeof meta>;

// ===== 6 种基础状态 =====

export const Working: Story = {
  args: {
    name: 'DeepSeek',
    status: 'working',
    position: '数据分析师',
    model: 'deepseek-chat',
    currentTask: '分析东南亚市场趋势',
    todayCompleted: 5,
    recentActivity: '完成市场分析报告',
    suggestion: '建议查看最新的市场分析输出。',
  },
};

export const Idle: Story = {
  args: {
    name: 'Claude',
    status: 'idle',
    position: '代码审查员',
    model: 'claude-3-opus',
    currentTask: '等待任务分配',
    suggestion: '该员工已就绪，可以分配代码审查任务。',
  },
};

export const Waiting: Story = {
  args: {
    name: 'GPT',
    status: 'waiting',
    position: '策略分析师',
    model: 'gpt-4',
    currentTask: '配置 AI 能力中',
    suggestion: '该员工正在配置中，完成后即可分配任务。',
  },
};

export const Completed: Story = {
  args: {
    name: 'Kimi',
    status: 'completed',
    position: '客户关系专员',
    model: 'moonshot-v1',
    currentTask: '客户资料更新完成',
    todayCompleted: 12,
    recentActivity: '完成 50 条客户资料更新',
    suggestion: '该员工已完成当前批次任务，可分配新任务。',
  },
};

export const Error_: Story = {
  args: {
    name: 'Gemini',
    status: 'error',
    position: '市场研究员',
    model: 'gemini-pro',
    currentTask: '供应商分析任务异常',
    todayCompleted: 3,
    recentActivity: '任务执行中断',
    suggestion: '检测到任务执行异常，建议检查日志并重新调度。',
  },
};

export const Offline: Story = {
  args: {
    name: 'Grok',
    status: 'offline',
    position: '趋势预测师',
    model: 'grok-1',
    currentTask: '已暂停',
    suggestion: '该员工已暂停，需激活后才能使用。',
  },
};

// ===== 变化场景 =====

export const Minimal: Story = {
  args: {
    name: 'AI 助手',
    status: 'working',
  },
  parameters: { docs: { description: { story: '仅显示名称和状态，无额外信息。' } } },
};

export const WithAllData: Story = {
  args: {
    name: 'GPT',
    status: 'working',
    position: '数据科学家',
    model: 'gpt-4-turbo',
    currentTask: '分析客户行为模式',
    todayCompleted: 8,
    recentActivity: '完成客户分群报告',
    suggestion: '建议将分析结果同步到 CRM 系统。',
  },
  parameters: { docs: { description: { story: '所有可选属性同时传入，展示完整信息卡片。' } } },
};

export const NoSuggestions: Story = {
  args: {
    name: 'DeepSeek',
    status: 'working',
    position: '数据分析师',
    currentTask: '处理数据中',
    todayCompleted: 3,
  },
  parameters: { docs: { description: { story: '不显示建议区域，仅显示任务和完成数据。' } } },
};

// ===== 紧凑模式 =====

export const CompactWorking: Story = {
  args: {
    name: 'DeepSeek',
    status: 'working',
    currentTask: '分析市场数据',
    compact: true,
  },
  parameters: { docs: { description: { story: '紧凑模式，适合侧边栏或小卡片场景。' } } },
};

export const CompactError: Story = {
  args: {
    name: 'Gemini',
    status: 'error',
    currentTask: '任务执行异常',
    compact: true,
  },
};

export const CompactOffline: Story = {
  args: {
    name: 'Grok',
    status: 'offline',
    compact: true,
  },
};

// ===== 状态对比展示 =====

export const AllStates: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 400 }}>
      <AIWorkStatus name="DeepSeek" status="working" position="分析师" currentTask="分析市场数据" />
      <AIWorkStatus name="Claude" status="idle" position="审查员" />
      <AIWorkStatus name="GPT" status="waiting" position="策略师" currentTask="配置中" />
      <AIWorkStatus name="Kimi" status="completed" position="专员" todayCompleted={10} />
      <AIWorkStatus name="Gemini" status="error" position="研究员" currentTask="任务异常" />
      <AIWorkStatus name="Grok" status="offline" position="预测师" />
    </div>
  ),
  parameters: { docs: { description: { story: '6 种状态并排对比，方便视觉验收。' } } },
};

export const AllStatesCompact: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 300 }}>
      <AIWorkStatus name="DeepSeek" status="working" compact currentTask="分析中" />
      <AIWorkStatus name="Claude" status="idle" compact />
      <AIWorkStatus name="GPT" status="waiting" compact currentTask="配置中" />
      <AIWorkStatus name="Kimi" status="completed" compact />
      <AIWorkStatus name="Gemini" status="error" compact currentTask="异常" />
      <AIWorkStatus name="Grok" status="offline" compact />
    </div>
  ),
  parameters: { docs: { description: { story: '6 种状态紧凑模式并排对比。' } } },
};

// ===== AIStatusDot 子组件 =====

export const StatusDot: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 16, alignItems: 'center', padding: 20 }}>
      <div style={{ textAlign: 'center' }}><AIStatusDot status="working" /><div style={{ fontSize: 10, marginTop: 4 }}>working</div></div>
      <div style={{ textAlign: 'center' }}><AIStatusDot status="idle" /><div style={{ fontSize: 10, marginTop: 4 }}>idle</div></div>
      <div style={{ textAlign: 'center' }}><AIStatusDot status="waiting" /><div style={{ fontSize: 10, marginTop: 4 }}>waiting</div></div>
      <div style={{ textAlign: 'center' }}><AIStatusDot status="completed" /><div style={{ fontSize: 10, marginTop: 4 }}>completed</div></div>
      <div style={{ textAlign: 'center' }}><AIStatusDot status="error" /><div style={{ fontSize: 10, marginTop: 4 }}>error</div></div>
      <div style={{ textAlign: 'center' }}><AIStatusDot status="offline" /><div style={{ fontSize: 10, marginTop: 4 }}>offline</div></div>
    </div>
  ),
  parameters: { docs: { description: { story: 'AIStatusDot 纯圆点组件，6 种状态颜色对比。' } } },
};

export const StatusDotSizes: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 24, alignItems: 'center', padding: 20 }}>
      <AIStatusDot status="working" size={8} />
      <AIStatusDot status="working" size={12} />
      <AIStatusDot status="working" size={16} />
      <AIStatusDot status="working" size={24} />
    </div>
  ),
  parameters: { docs: { description: { story: 'AIStatusDot 支持自定义尺寸（8px / 12px / 16px / 24px）。' } } },
};