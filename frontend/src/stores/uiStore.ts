import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * UI 主题类型
 */
export type Theme = 'dark' | 'light';

/**
 * UI 状态接口
 */
interface UIState {
  // 侧边栏状态
  isSidebarCollapsed: boolean;
  
  // 主题设置
  theme: Theme;
  
  // 全局加载状态
  isLoading: boolean;
  
  // 全局通知
  notification: {
    visible: boolean;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
  } | null;
  
  // Actions
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: Theme) => void;
  setLoading: (loading: boolean) => void;
  showNotification: (type: 'success' | 'error' | 'warning' | 'info', message: string) => void;
  hideNotification: () => void;
}

/**
 * UI 状态管理 Store
 * 管理侧边栏、主题、加载状态等全局 UI 状态
 */
export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      isSidebarCollapsed: false,
      theme: 'dark',
      isLoading: false,
      notification: null,

      /**
       * 切换侧边栏折叠状态
       */
      toggleSidebar: () => {
        set((state) => ({
          isSidebarCollapsed: !state.isSidebarCollapsed,
        }));
      },

      /**
       * 设置侧边栏折叠状态
       */
      setSidebarCollapsed: (collapsed: boolean) => {
        set({ isSidebarCollapsed: collapsed });
      },

      /**
       * 设置主题
       */
      setTheme: (theme: Theme) => {
        set({ theme });
        // 更新 HTML root class
        if (typeof document !== 'undefined') {
          document.documentElement.classList.remove('light', 'dark');
          document.documentElement.classList.add(theme);
        }
      },

      /**
       * 设置全局加载状态
       */
      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      /**
       * 显示通知
       */
      showNotification: (type, message) => {
        set({
          notification: {
            visible: true,
            type,
            message,
          },
        });
        // 3秒后自动隐藏
        setTimeout(() => {
          set((state) => 
            state.notification?.visible
              ? { notification: { ...state.notification, visible: false } }
              : state
          );
        }, 3000);
      },

      /**
       * 隐藏通知
       */
      hideNotification: () => {
        set((state) =>
          state.notification
            ? { notification: { ...state.notification, visible: false } }
            : state
        );
      },
    }),
    {
      name: 'liuhao-ui-storage',
      partialize: (state) => ({
        isSidebarCollapsed: state.isSidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
);
