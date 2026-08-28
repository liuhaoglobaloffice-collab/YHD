const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function getToken(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export interface Employee {
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

export interface ExecuteTaskRequest {
  prompt: string;
  temperature?: number;
  max_tokens?: number;
}

export interface ExecuteTaskResponse {
  execution_id: string;
  employee_id: string;
  employee_name: string;
  agent_type: string;
  status: string;
  output: string | null;
  error: string | null;
  response_time_ms: number | null;
}

export async function fetchEmployees(): Promise<Employee[]> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/employees`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch employees: ${res.status}`);
  return res.json();
}

export async function executeTask(employeeId: string, request: ExecuteTaskRequest): Promise<ExecuteTaskResponse> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/employees/${employeeId}/execute`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Task execution failed: ${res.status}`);
  }
  return res.json();
}

/** NDJSON 流式执行：onDelta 每次收到文本片段，返回最终完整输出 */
export async function executeTaskStream(
  employeeId: string,
  request: ExecuteTaskRequest,
  onDelta: (delta: string) => void
): Promise<{ output: string; error?: string }> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/employees/${employeeId}/execute/stream`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Task execution failed: ${res.status}`);
  }

  if (!res.body) throw new Error('No response body');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const chunks: string[] = [];
  let error: string | undefined;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value, { stream: true });
    const lines = text.split('\n').filter(Boolean);
    for (const line of lines) {
      try {
        const parsed = JSON.parse(line);
        if (parsed.delta) {
          chunks.push(parsed.delta);
          onDelta(parsed.delta);
        }
        if (parsed.error) error = parsed.error;
        if (parsed.done) {
          if (parsed.output) return { output: parsed.output, error };
        }
      } catch {
        // 忽略无法解析的行
      }
    }
  }

  return { output: chunks.join(''), error };
}

export interface ProviderStatus {
  provider: string;
  model: string;
  available: boolean;
  description: string;
}

export interface ExecutionRecord {
  task_id: string;
  employee_id: string;
  employee_name: string;
  agent_type: string;
  prompt: string;
  status: string;
  output: string;
  error: string | null;
  created_at: number | null;
  started_at: number | null;
  completed_at: number | null;
  elapsed_ms: number | null;
}

/** 提交异步任务到执行队列，立即返回 task_id */
export async function submitAsyncTask(employeeId: string, request: ExecuteTaskRequest): Promise<ExecutionRecord> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/employees/${employeeId}/tasks`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to submit task: ${res.status}`);
  }
  return res.json();
}

/** 查询异步任务状态 */
export async function fetchExecution(taskId: string): Promise<ExecutionRecord> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/tasks/${taskId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch execution: ${res.status}`);
  return res.json();
}

/** 列出异步执行记录 */
export async function fetchExecutions(status?: string): Promise<{ executions: ExecutionRecord[]; total: number }> {
  const params = status ? `?status=${status}` : '';
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/tasks${params}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch executions: ${res.status}`);
  return res.json();
}

/** 取消异步任务 */
export async function cancelAsyncTask(taskId: string): Promise<void> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/tasks/${taskId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to cancel execution: ${res.status}`);
}

export async function fetchProviderStatus(): Promise<ProviderStatus> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/workforce/provider/status`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch provider status: ${res.status}`);
  return res.json();
}