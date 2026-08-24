import apiService from './apiService';
import { User } from '../stores/authStore';

/**
 * 登录请求参数
 */
export interface LoginRequest {
  username: string;
  password: string;
}

/**
 * 登录响应
 */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

/**
 * 注册请求参数
 */
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

/**
 * 认证 API 服务
 */
class AuthAPI {
  /**
   * 用户登录
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    return apiService.post<LoginResponse>('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  }

  /**
   * 用户注册
   */
  async register(data: RegisterRequest): Promise<User> {
    return apiService.post<User>('/api/v1/auth/register', data);
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    return apiService.get<User>('/api/v1/auth/me');
  }

  /**
   * 登出（如果后端有登出接口）
   */
  async logout(): Promise<void> {
    try {
      await apiService.post('/api/v1/auth/logout');
    } catch (error) {
      console.error('登出请求失败:', error);
    }
  }

  /**
   * 刷新 Token（如果后端支持）
   */
  async refreshToken(): Promise<{ access_token: string }> {
    return apiService.post('/api/v1/auth/refresh');
  }
}

export const authAPI = new AuthAPI();
export default authAPI;
