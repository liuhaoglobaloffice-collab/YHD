import { describe, it, expect } from 'vitest';
import { deriveAICoreState, type LiveActivity } from './live';

/** 构造最小可用的 LiveActivity 测试夹具（字段均为真实接口返回结构） */
function makeLive(overrides: Partial<LiveActivity> = {}): LiveActivity {
  return {
    server_time: '2026-08-31T10:00:00Z',
    employees: [],
    active_employees: 11,
    total_employees: 11,
    running_tasks: 0,
    recent_tasks: [],
    workflows: [],
    goals: [],
    model_calls: [],
    knowledge: { documents: 0, memory_activity: [] },
    audit_activity: [],
    ...overrides,
  } as LiveActivity;
}

describe('deriveAICoreState — AI Core 统一状态机（真实数据派生）', () => {
  it('live 为 null（API 不可达）→ offline 连接中断', () => {
    const s = deriveAICoreState(null);
    expect(s.status).toBe('offline');
    expect(s.label).toContain('连接中断');
  });

  it('live 为 undefined → offline', () => {
    expect(deriveAICoreState(undefined).status).toBe('offline');
  });

  it('working_now 非空 → working 执行中，label 带任务数，detail 描述正在做什么', () => {
    const s = deriveAICoreState(
      makeLive({
        working_now: [
          {
            kind: 'task',
            id: 't1',
            title: '撰写市场分析报告',
            status: 'running',
            employee_name: '李外贸',
          },
        ],
      }),
    );
    expect(s.status).toBe('working');
    expect(s.label).toBe('执行中 · 1 项任务');
    expect(s.detail).toContain('李外贸');
    expect(s.detail).toContain('撰写市场分析报告');
  });

  it('working_now 多项 → label 计数正确', () => {
    const s = deriveAICoreState(
      makeLive({
        working_now: [
          { kind: 'task', id: '1', title: 'A', status: 'running' },
          { kind: 'workflow', id: '2', title: 'B', status: 'running', workflow_name: '线索获取流' },
        ] as LiveActivity['working_now'],
      }),
    );
    expect(s.label).toBe('执行中 · 2 项任务');
  });

  it('无执行 + failed_tasks > 0 → error 异常，detail 带失败任务信息', () => {
    const s = deriveAICoreState(
      makeLive({
        failed_tasks: 2,
        recent_tasks: [
          { id: 'f1', title: '供应商尽调', status: 'failed', summary: '', error: '超时' } as never,
        ],
      }),
    );
    expect(s.status).toBe('error');
    expect(s.label).toBe('异常 · 2 个任务失败');
    expect(s.detail).toContain('供应商尽调');
    expect(s.detail).toContain('超时');
  });

  it('无执行 + 无失败 + blocked_tasks > 0 → waiting 等待审批', () => {
    const s = deriveAICoreState(makeLive({ blocked_tasks: 3 }));
    expect(s.status).toBe('waiting');
    expect(s.label).toBe('等待审批 · 3 项');
    expect(s.detail).toContain('人工处理');
  });

  it('无执行 + 无失败 + 无阻塞 + 今日有完成 → completed 已完成', () => {
    const s = deriveAICoreState(
      makeLive({
        today: { completed: 5, failed: 0 },
        recent_tasks: [
          { id: 'c1', title: '客户跟进邮件', status: 'completed', summary: '' } as never,
        ],
      }),
    );
    expect(s.status).toBe('completed');
    expect(s.label).toBe('今日已完成 5 项');
    expect(s.detail).toContain('客户跟进邮件');
  });

  it('全部为零 → idle 待机，label 带在线人数', () => {
    const s = deriveAICoreState(makeLive({ active_employees: 11 }));
    expect(s.status).toBe('idle');
    expect(s.label).toBe('待机 · 11 名 AI 在线');
    expect(s.detail).toContain('目标中心');
  });

  // ===== 优先级测试：执行中 > 异常 > 等待审批 > 已完成 > 待机 =====
  it('优先级：执行中任务与失败任务并存 → working（当前在做什么优先）', () => {
    const s = deriveAICoreState(
      makeLive({
        working_now: [{ kind: 'task', id: 'w1', title: '进行中', status: 'running' }] as never,
        failed_tasks: 3,
        blocked_tasks: 1,
        today: { completed: 9, failed: 3 },
      }),
    );
    expect(s.status).toBe('working');
  });

  it('优先级：失败与阻塞并存（无执行）→ error', () => {
    const s = deriveAICoreState(
      makeLive({ failed_tasks: 1, blocked_tasks: 2, today: { completed: 4, failed: 1 } }),
    );
    expect(s.status).toBe('error');
  });

  it('优先级：阻塞与今日完成并存（无执行无失败）→ waiting', () => {
    const s = deriveAICoreState(
      makeLive({ blocked_tasks: 1, today: { completed: 4, failed: 0 } }),
    );
    expect(s.status).toBe('waiting');
  });

  it('字段缺失（旧后端兼容）→ 不抛异常，回退 idle', () => {
    const s = deriveAICoreState(makeLive());
    expect(s.status).toBe('idle');
  });
});
