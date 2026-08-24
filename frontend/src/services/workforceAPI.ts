/**
 * Workforce API Service - AI员工管理
 */

import apiService from './apiService';

/**
 * AI员工状态枚举
 */
export enum AIEmployeeStatus {
  CREATED = 'created',
  TRAINING = 'training',
  ACTIVE = 'active',
  SUSPENDED = 'suspended',
  RETIRED = 'retired',
}

/**
 * 部门枚举
 */
export enum Department {
  CEO_OFFICE = 'ceo_office',
  MARKETING = 'marketing',
  SALES = 'sales',
  RESEARCH = 'research',
  OPERATIONS = 'operations',
  ENGINEERING = 'engineering',
  ANALYTICS = 'analytics',
}

/**
 * 职位枚举
 */
export enum Position {
  // CEO Office
  CEO_ASSISTANT = 'ceo_assistant',
  STRATEGY_ANALYST = 'strategy_analyst',
  // Marketing
  MARKETING_SPECIALIST = 'marketing_specialist',
  SEO_SPECIALIST = 'seo_specialist',
  CONTENT_WRITER = 'content_writer',
  // Sales
  SALES_REPRESENTATIVE = 'sales_representative',
  ACCOUNT_MANAGER = 'account_manager',
  CUSTOMER_SUCCESS = 'customer_success',
  // Research
  MARKET_RESEARCHER = 'market_researcher',
  COMPETITIVE_ANALYST = 'competitive_analyst',
  PRODUCT_RESEARCHER = 'product_researcher',
  // Operations
  OPERATIONS_COORDINATOR = 'operations_coordinator',
  DATA_PROCESSOR = 'data_processor',
  TASK_MANAGER = 'task_manager',
  // Engineering
  SYSTEM_ENGINEER = 'system_engineer',
  INTEGRATION_SPECIALIST = 'integration_specialist',
  // Analytics
  DATA_ANALYST = 'data_analyst',
  BUSINESS_ANALYST = 'business_analyst',
}

/**
 * AI员工基本信息
 */
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

/**
 * 创建AI员工请求
 */
export interface CreateEmployeeRequest {
  name: string;
  department: Department;
  position: Position;
  description: string;
  agent_type?: string;
}

/**
 * 更新AI员工请求
 */
export interface UpdateEmployeeRequest {
  name?: string;
  description?: string;
  status?: AIEmployeeStatus;
}

/**
 * 绩效数据
 */
export interface PerformanceData {
  tasks_completed: number;
  tasks_failed: number;
  success_rate: number;
  avg_response_time: number;
  total_interactions: number;
}

/**
 * 成本数据
 */
export interface CostData {
  total_cost: number;
  token_usage: number;
  cost_per_task: number;
  period: string;
}

class WorkforceAPI {
  private baseURL = '/api/v1/workforce';

  /**
   * 获取AI员工列表
   */
  async listEmployees(params?: {
    department?: Department;
    position?: Position;
    status?: AIEmployeeStatus;
    skip?: number;
    limit?: number;
  }): Promise<AIEmployee[]> {
    const response = await apiService.get(`${this.baseURL}/employees`, { params });
    return response.data;
  }

  /**
   * 获取AI员工详情
   */
  async getEmployee(employeeId: string): Promise<AIEmployee> {
    const response = await apiService.get(`${this.baseURL}/employees/${employeeId}`);
    return response.data;
  }

  /**
   * 创建AI员工
   */
  async createEmployee(data: CreateEmployeeRequest): Promise<AIEmployee> {
    const response = await apiService.post(`${this.baseURL}/employees`, data);
    return response.data;
  }

  /**
   * 更新AI员工
   */
  async updateEmployee(employeeId: string, data: UpdateEmployeeRequest): Promise<AIEmployee> {
    const response = await apiService.patch(`${this.baseURL}/employees/${employeeId}`, data);
    return response.data;
  }

  /**
   * 激活AI员工
   */
  async activateEmployee(employeeId: string): Promise<AIEmployee> {
    const response = await apiService.post(`${this.baseURL}/employees/${employeeId}/activate`);
    return response.data;
  }

  /**
   * 获取AI员工绩效
   */
  async getEmployeePerformance(employeeId: string): Promise<PerformanceData> {
    const response = await apiService.get(`${this.baseURL}/employees/${employeeId}/performance`);
    return response.data;
  }

  /**
   * 获取AI员工成本
   */
  async getEmployeeCost(employeeId: string): Promise<CostData> {
    const response = await apiService.get(`${this.baseURL}/employees/${employeeId}/cost`);
    return response.data;
  }

  /**
   * 部门中文映射
   */
  getDepartmentLabel(dept: string): string {
    const labels: Record<string, string> = {
      ceo_office: 'CEO办公室',
      marketing: '市场部',
      sales: '销售部',
      research: '研发部',
      operations: '运营部',
      engineering: '工程部',
      analytics: '分析部',
    };
    return labels[dept] || dept;
  }

  /**
   * 职位中文映射
   */
  getPositionLabel(pos: string): string {
    const labels: Record<string, string> = {
      ceo_assistant: 'CEO助理',
      strategy_analyst: '战略分析师',
      marketing_specialist: '市场专员',
      seo_specialist: 'SEO专员',
      content_writer: '内容撰写',
      sales_representative: '销售代表',
      account_manager: '客户经理',
      customer_success: '客户成功',
      market_researcher: '市场研究员',
      competitive_analyst: '竞品分析师',
      product_researcher: '产品研究员',
      operations_coordinator: '运营协调员',
      data_processor: '数据处理员',
      task_manager: '任务管理员',
      system_engineer: '系统工程师',
      integration_specialist: '集成专家',
      data_analyst: '数据分析师',
      business_analyst: '业务分析师',
    };
    return labels[pos] || pos;
  }

  /**
   * 状态中文映射
   */
  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      created: '已创建',
      training: '培训中',
      active: '活跃',
      suspended: '暂停',
      retired: '已退役',
    };
    return labels[status] || status;
  }

  /**
   * 状态颜色映射
   */
  getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      created: 'text-gray-400',
      training: 'text-yellow-400',
      active: 'text-green-400',
      suspended: 'text-orange-400',
      retired: 'text-red-400',
    };
    return colors[status] || 'text-gray-400';
  }
}

export default new WorkforceAPI();
