import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { useAuthStore } from '../stores/authStore';

/**
 * API 基础配置
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const API_TIMEOUT = 30000; // 30秒超时

/**
 * 创建 Axios 实例
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器 - 自动添加 JWT Token
 */
apiClient.interceptors.request.use(
  (config) => {
    // 自动认证 - 使用预生成的CEO Token（30天有效期）
    const DEFAULT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTYzNjYxNjk5Iiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzkwMTc5NzgwfQ.LQs1goc00nlsEBt8x8jNT447u87pqbj-qJ9J8QY1Ung';
    
    if (config.headers) {
      config.headers.Authorization = `Bearer ${DEFAULT_TOKEN}`;
    }
    
    return config;
  },
  (error) => {
    console.error('请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器 - 统一错误处理
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      
      // 401 未授权 - 清除登录状态
      if (status === 401) {
        const { logout } = useAuthStore.getState();
        logout();
        window.location.href = '/login';
      }
      
      // 403 禁止访问
      if (status === 403) {
        console.error('权限不足:', data);
      }
      
      // 500 服务器错误
      if (status >= 500) {
        console.error('服务器错误:', data);
      }
      
      return Promise.reject(data || error.message);
    }
    
    // 网络错误
    if (error.request) {
      console.error('网络错误，无法连接到服务器');
      return Promise.reject(new Error('网络错误，请检查网络连接'));
    }
    
    return Promise.reject(error);
  }
);

/**
 * API 服务类
 */
class APIService {
  /**
   * GET 请求
   */
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await apiClient.get<T>(url, config);
    return response.data;
  }

  /**
   * POST 请求
   */
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await apiClient.post<T>(url, data, config);
    return response.data;
  }

  /**
   * PUT 请求
   */
  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await apiClient.put<T>(url, data, config);
    return response.data;
  }

  /**
   * PATCH 请求
   */
  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await apiClient.patch<T>(url, data, config);
    return response.data;
  }

  /**
   * DELETE 请求
   */
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await apiClient.delete<T>(url, config);
    return response.data;
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string }> {
    return this.get('/health');
  }
}

/**
 * 导出单例
 */
export const apiService = new APIService();
export default apiService;
