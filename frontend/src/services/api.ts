import axios from 'axios';

const API_BASE_URL = '/api/v1';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AIEmployee {
  id: string;
  name: string;
  department: string;
  position: string;
  description: string;
  agent_type: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  task_id: string;
  title: string;
  description: string;
  task_type: string;
  status: string;
  priority: string;
  assigned_agents: string[];
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}

class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  private getHeaders() {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await axios.post(`${API_BASE_URL}/auth/login`, data);
    this.setToken(response.data.access_token);
    return response.data;
  }

  async register(data: { username: string; email: string; password: string; full_name?: string }) {
    const response = await axios.post(`${API_BASE_URL}/auth/register`, data);
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await axios.get(`${API_BASE_URL}/auth/me`, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async getHealth(): Promise<HealthResponse> {
    const response = await axios.get(`${API_BASE_URL}/health/`);
    return response.data;
  }

  async listEmployees(): Promise<AIEmployee[]> {
    const response = await axios.get(`${API_BASE_URL}/workforce/employees`, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async createEmployee(data: {
    name: string;
    department: string;
    position: string;
    description: string;
  }): Promise<AIEmployee> {
    const response = await axios.post(`${API_BASE_URL}/workforce/employees`, data, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async listTasks(): Promise<Task[]> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/tasks`, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async createTask(data: {
    title: string;
    description: string;
    task_type: string;
    priority: string;
  }): Promise<Task> {
    const response = await axios.post(`${API_BASE_URL}/api/v1/tasks`, data, {
      headers: this.getHeaders(),
    });
    return response.data;
  }
}

export const apiService = new ApiService();
