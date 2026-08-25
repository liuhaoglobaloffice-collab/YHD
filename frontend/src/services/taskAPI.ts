/**
 * Task Management API Service
 * 
 * LiuHao AI-OS - Week 6 Day 5
 * 任务中心 API 客户端
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加认证token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============ 枚举定义 ============

export enum TaskStatus {
  PENDING = 'pending',
  READY = 'ready',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  BLOCKED = 'blocked',
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
  CRITICAL = 'critical',
}

export enum TaskType {
  GENERAL = 'general',
  RESEARCH = 'research',
  ANALYSIS = 'analysis',
  CODING = 'coding',
  REVIEW = 'review',
  TESTING = 'testing',
  DEPLOYMENT = 'deployment',
  SALES = 'sales',
  MARKETING = 'marketing',
  CUSTOMER_SERVICE = 'customer_service',
  CONTENT_CREATION = 'content_creation',
  DATA_PROCESSING = 'data_processing',
  REPORTING = 'reporting',
}

// 中文标签映射
export const taskStatusLabels: Record<TaskStatus, string> = {
  [TaskStatus.PENDING]: '待处理',
  [TaskStatus.READY]: '准备就绪',
  [TaskStatus.RUNNING]: '执行中',
  [TaskStatus.COMPLETED]: '已完成',
  [TaskStatus.FAILED]: '失败',
  [TaskStatus.CANCELLED]: '已取消',
  [TaskStatus.BLOCKED]: '阻塞中',
};

export const taskPriorityLabels: Record<TaskPriority, string> = {
  [TaskPriority.LOW]: '低',
  [TaskPriority.MEDIUM]: '中',
  [TaskPriority.HIGH]: '高',
  [TaskPriority.URGENT]: '紧急',
  [TaskPriority.CRITICAL]: '严重',
};

export const taskTypeLabels: Record<TaskType, string> = {
  [TaskType.GENERAL]: '通用任务',
  [TaskType.RESEARCH]: '研发任务',
  [TaskType.ANALYSIS]: '分析任务',
  [TaskType.CODING]: '编码任务',
  [TaskType.REVIEW]: '审核任务',
  [TaskType.TESTING]: '测试任务',
  [TaskType.DEPLOYMENT]: '部署任务',
  [TaskType.SALES]: '销售任务',
  [TaskType.MARKETING]: '营销任务',
  [TaskType.CUSTOMER_SERVICE]: '客服任务',
  [TaskType.CONTENT_CREATION]: '内容创作',
  [TaskType.DATA_PROCESSING]: '数据处理',
  [TaskType.REPORTING]: '报表任务',
};

// ============ 类型定义 ============

const normalizeTaskType = (value?: string): TaskType => {
  const normalized = (value ?? TaskType.GENERAL).toString().toLowerCase();
  if (Object.values(TaskType).includes(normalized as TaskType)) return normalized as TaskType;
  return TaskType.GENERAL;
};

const normalizeTaskStatus = (value?: string): TaskStatus => {
  const normalized = (value ?? TaskStatus.PENDING).toString().toLowerCase();
  if (Object.values(TaskStatus).includes(normalized as TaskStatus)) return normalized as TaskStatus;
  return TaskStatus.PENDING;
};

const normalizeTaskPriority = (value?: string): TaskPriority => {
  const normalized = (value ?? TaskPriority.MEDIUM).toString().toLowerCase();
  if (Object.values(TaskPriority).includes(normalized as TaskPriority)) return normalized as TaskPriority;
  return TaskPriority.MEDIUM;
};

const normalizeTask = (task: any): Task => {
  const payload = task ?? {};
  const assignedAgents = Array.isArray(payload.assigned_agents)
    ? payload.assigned_agents
    : Array.isArray(payload.assigned_to)
      ? payload.assigned_to
      : Array.isArray(payload.agent_ids)
        ? payload.agent_ids
        : [];

  const dependencies = Array.isArray(payload.dependencies)
    ? payload.dependencies
    : Array.isArray(payload.deps)
      ? payload.deps
      : [];

  const resultValue = payload.result ?? payload.result_data ?? payload.output ?? undefined;

  return {
    task_id: String(payload.task_id ?? payload.id ?? payload.taskId ?? ''),
    title: payload.title ?? '未命名任务',
    description: payload.description ?? '',
    task_type: normalizeTaskType(payload.task_type ?? payload.type),
    status: normalizeTaskStatus(payload.status ?? payload.state),
    priority: normalizeTaskPriority(payload.priority),
    assigned_agents: assignedAgents.map((agent: any) => String(agent)),
    created_by: String(payload.created_by ?? payload.creator_id ?? payload.createdBy ?? 'system'),
    created_at: payload.created_at ?? payload.createdAt ?? new Date().toISOString(),
    updated_at: payload.updated_at ?? payload.updatedAt ?? payload.created_at ?? payload.createdAt ?? new Date().toISOString(),
    started_at: payload.started_at ?? payload.startedAt,
    completed_at: payload.completed_at ?? payload.completedAt,
    dependencies: dependencies.map((dep: any) => ({
      task_id: String(dep?.task_id ?? dep?.id ?? dep?.taskId ?? ''),
      type: dep?.type ?? dep?.dependency_type ?? dep?.dependencyType ?? 'finish_to_start',
    })),
    result: resultValue
      ? {
          success: Boolean(resultValue.success ?? true),
          output: resultValue.output ?? resultValue,
          error: resultValue.error,
          metadata: resultValue.metadata ?? resultValue.meta ?? {},
          completed_at: resultValue.completed_at ?? resultValue.completedAt ?? payload.completed_at ?? payload.completedAt ?? new Date().toISOString(),
        }
      : undefined,
    metadata: payload.metadata ?? payload.meta ?? {},
  };
};

export interface TaskDependency {
  task_id: string;
  type: string;
}

export interface TaskResult {
  success: boolean;
  output?: any;
  error?: string;
  metadata: Record<string, any>;
  completed_at: string;
}

export interface Task {
  task_id: string;
  title: string;
  description: string;
  task_type: TaskType;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_agents: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  dependencies: TaskDependency[];
  result?: TaskResult;
  metadata: Record<string, any>;
}
export interface CreateTaskRequest {
  title: string;
  description?: string;
  task_type: TaskType;
  priority?: TaskPriority;
  assigned_agents?: string[];
  dependencies?: string[];
  metadata?: Record<string, any>;
}

export interface UpdateTaskStatusRequest {
  status: TaskStatus;
  result?: Record<string, any>;
}

export interface AssignTaskRequest {
  agent_ids: string[];
}

export interface CompleteTaskRequest {
  result?: Record<string, any>;
}

export interface TaskListParams {
  status?: TaskStatus;
  task_type?: TaskType;
  priority?: TaskPriority;
  assigned_agent?: string;
}

// ============ API 方法 ============

/**
 * 获取任务列表
 */
export async function getTasks(params?: TaskListParams): Promise<Task[]> {
  try {
    const query = params ? {
      status: params.status,
      task_type: params.task_type,
      priority: params.priority,
      assigned_agent: params.assigned_agent,
    } : undefined;

    const response = await apiClient.get<any[]>('/tasks', { params: query });
    return Array.isArray(response.data) ? response.data.map(normalizeTask) : [];
  } catch (error) {
    console.error('Failed to fetch tasks:', error);
    throw error;
  }
}

/**
 * 获取准备就绪的任务
 */
export async function getReadyTasks(): Promise<Task[]> {
  try {
    const response = await apiClient.get<any[]>('/tasks/ready');
    return Array.isArray(response.data) ? response.data.map(normalizeTask) : [];
  } catch (error) {
    console.error('Failed to fetch ready tasks:', error);
    throw error;
  }
}

/**
 * 获取单个任务详情
 */
export async function getTask(taskId: string): Promise<Task> {
  try {
    const response = await apiClient.get<any>(`/tasks/${taskId}`);
    return normalizeTask(response.data);
  } catch (error) {
    console.error(`Failed to fetch task ${taskId}:`, error);
    throw error;
  }
}

/**
 * 创建任务
 */
export async function createTask(request: CreateTaskRequest): Promise<Task> {
  try {
    const response = await apiClient.post<any>('/tasks', request);
    return normalizeTask(response.data);
  } catch (error) {
    console.error('Failed to create task:', error);
    throw error;
  }
}

/**
 * 更新任务状态
 */
export async function updateTaskStatus(
  taskId: string,
  request: UpdateTaskStatusRequest
): Promise<Task> {
  try {
    const response = await apiClient.put<any>(`/tasks/${taskId}/status`, request);
    return normalizeTask(response.data);
  } catch (error) {
    console.error(`Failed to update task ${taskId} status:`, error);
    throw error;
  }
}

/**
 * 分配任务
 */
export async function assignTask(
  taskId: string,
  request: AssignTaskRequest
): Promise<Task> {
  try {
    const response = await apiClient.put<any>(`/tasks/${taskId}/assign`, request);
    return normalizeTask(response.data);
  } catch (error) {
    console.error(`Failed to assign task ${taskId}:`, error);
    throw error;
  }
}

/**
 * 完成任务
 */
export async function completeTask(
  taskId: string,
  request: CompleteTaskRequest
): Promise<Task> {
  try {
    const response = await apiClient.post<any>(`/tasks/${taskId}/complete`, request);
    return normalizeTask(response.data);
  } catch (error) {
    console.error(`Failed to complete task ${taskId}:`, error);
    throw error;
  }
}

/**
 * 删除任务
 */
export async function deleteTask(taskId: string): Promise<void> {
  try {
    await apiClient.delete(`/tasks/${taskId}`);
  } catch (error) {
    console.error(`Failed to delete task ${taskId}:`, error);
    throw error;
  }
}

export default {
  getTasks,
  getReadyTasks,
  getTask,
  createTask,
  updateTaskStatus,
  assignTask,
  completeTask,
  deleteTask,
};
