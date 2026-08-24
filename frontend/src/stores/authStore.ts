import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * 用户信息接口
 */
export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role?: string;
  tenant_id?: string;
}

/**
 * 认证状态接口
 */
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  
  // Actions
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

/**
 * 认证状态管理 Store
 * 使用 zustand + persist 实现 JWT Token 持久化
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      /**
       * 登录 - 保存 Token 和用户信息
       */
      login: (token: string, user: User) => {
        set({
          token,
          user,
          isAuthenticated: true,
        });
      },

      /**
       * 登出 - 清除所有认证信息
       */
      logout: () => {
        set({
          token: null,
          user: null,
          isAuthenticated: false,
        });
      },

      /**
       * 更新用户信息
       */
      updateUser: (userData: Partial<User>) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        }));
      },
    }),
    {
      name: 'liuhao-auth-storage', // localStorage key
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
