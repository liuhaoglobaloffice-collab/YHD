/**
 * Dashboard Zustand Store
 * 管理CEO Dashboard状态、AI员工状态、系统状态、实时消息
 */

import { create } from 'zustand';
import { dashboardService, DashboardData, CEOBriefItem, AIWorkforceStatus } from '../services/dashboard';
import { websocketService } from '../services/websocket';

interface DashboardState {
  // 数据状态
  data: DashboardData | null;
  loading: boolean;
  error: string | null;
  lastUpdate: string | null;

  // 实时状态
  wsConnected: boolean;
  realtimeEnabled: boolean;

  // Actions
  loadDashboard: () => Promise<void>;
  refreshDashboard: () => Promise<void>;
  updateCEOBrief: (brief: CEOBriefItem[]) => void;
  updateWorkforceStatus: (status: AIWorkforceStatus) => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  markBriefAsRead: (id: string) => void;
  clearError: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // 初始状态
  data: null,
  loading: false,
  error: null,
  lastUpdate: null,
  wsConnected: false,
  realtimeEnabled: false,

  /**
   * 加载Dashboard数据
   */
  loadDashboard: async () => {
    set({ loading: true, error: null });

    try {
      const data = await dashboardService.getDashboardData();
      set({
        data,
        loading: false,
        lastUpdate: data.lastUpdate,
      });
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load dashboard',
      });
    }
  },

  /**
   * 刷新Dashboard数据
   */
  refreshDashboard: async () => {
    const { loadDashboard } = get();
    await loadDashboard();
  },

  /**
   * 更新CEO简报
   */
  updateCEOBrief: (brief: CEOBriefItem[]) => {
    const { data } = get();
    if (data) {
      set({
        data: {
          ...data,
          ceoBrief: brief,
          lastUpdate: new Date().toISOString(),
        },
      });
    }
  },

  /**
   * 更新AI员工状态
   */
  updateWorkforceStatus: (status: AIWorkforceStatus) => {
    const { data } = get();
    if (data) {
      set({
        data: {
          ...data,
          workforceStatus: status,
          lastUpdate: new Date().toISOString(),
        },
      });
    }
  },

  /**
   * 连接WebSocket
   */
  connectWebSocket: () => {
    if (websocketService.isConnected) {
      set({ wsConnected: true, realtimeEnabled: true });
      return;
    }

    // 订阅WebSocket事件
    websocketService.on('employee_status_change', async (data) => {
      console.log('[Dashboard] Employee status changed:', data);
      const status = await dashboardService.getWorkforceStatus();
      get().updateWorkforceStatus(status);
    });

    websocketService.on('task_completed', async (data) => {
      console.log('[Dashboard] Task completed:', data);
      const status = await dashboardService.getWorkforceStatus();
      get().updateWorkforceStatus(status);
    });

    websocketService.on('task_started', async (data) => {
      console.log('[Dashboard] Task started:', data);
      const status = await dashboardService.getWorkforceStatus();
      get().updateWorkforceStatus(status);
    });

    websocketService.on('system_alert', async (data) => {
      console.log('[Dashboard] System alert:', data);
      const brief = await dashboardService.getCEOBrief();
      get().updateCEOBrief(brief);
    });

    websocketService.on('metric_update', async (data) => {
      console.log('[Dashboard] Metric update:', data);
      await get().refreshDashboard();
    });

    // 连接WebSocket
    websocketService.connect();
    set({ wsConnected: true, realtimeEnabled: true });
  },

  /**
   * 断开WebSocket
   */
  disconnectWebSocket: () => {
    websocketService.disconnect();
    set({ wsConnected: false, realtimeEnabled: false });
  },

  /**
   * 标记简报已读
   */
  markBriefAsRead: (id: string) => {
    const { data } = get();
    if (data) {
      const updatedBrief = data.ceoBrief.filter(item => item.id !== id);
      set({
        data: {
          ...data,
          ceoBrief: updatedBrief,
        },
      });
    }
  },

  /**
   * 清除错误
   */
  clearError: () => {
    set({ error: null });
  },
}));

export default useDashboardStore;
