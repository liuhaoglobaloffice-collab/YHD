/**
 * Supplier Management API Service
 * 
 * LiuHao AI-OS - Week 6 Day 3-4 + Week 7 Day 1-2
 * 供应商管理 API 客户端
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

export enum SupplierType {
  MANUFACTURER = 'manufacturer',
  TRADER = 'trader',
  AGENT = 'agent',
  SERVICE_PROVIDER = 'service_provider',
}

export enum SupplierStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  BLACKLISTED = 'blacklisted',
}

// ============ 接口定义 ============

/**
 * 供应商基础信息
 */
export interface Supplier {
  id: number;
  name: string;
  name_en?: string;
  supplier_type: SupplierType;
  status: SupplierStatus;
  industry?: string;
  website?: string;
  description?: string;
  
  // 联系信息
  address?: string;
  phone?: string;
  email?: string;
  contact_email?: string;
  
  // 公司注册信息
  registration_number?: string;
  tax_id?: string;
  legal_representative?: string;
  registered_capital?: number;
  established_date?: string;
  business_scope?: string;
  
  // 业务信息
  country?: string;
  main_products?: string;
  
  // 风险评分
  risk_score?: number;
  
  // 时间戳
  created_at?: string;
  updated_at?: string;
}

/**
 * 供应商联系人
 */
export interface SupplierContact {
  id: number;
  supplier_id: number;
  name: string;
  job_title?: string;
  phone?: string;
  email?: string;
  wechat?: string;
  qq?: string;
  is_primary: boolean;
  remarks?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * 供应商证书
 */
export interface SupplierCertificate {
  id: string;
  supplier_id: number;
  certificate_type: string;
  certificate_number: string;
  issue_date: string;
  expiry_date?: string;
  issuing_authority?: string;
  attachment_url?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * 供应商风险评估
 */
export interface SupplierRiskAssessment {
  id: string;
  supplier_id: number;
  assessment_date: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  financial_risk?: number;
  operational_risk?: number;
  compliance_risk?: number;
  reputation_risk?: number;
  findings?: string;
  recommendations?: string;
  assessed_by?: string;
  created_at?: string;
}

/**
 * 分页参数
 */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

/**
 * 供应商查询参数
 */
export interface SupplierQueryParams extends PaginationParams {
  status?: SupplierStatus;
  supplier_type?: SupplierType;
  industry?: string;
  search?: string;
}

/**
 * 分页响应
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * 供应商创建请求
 */
export interface CreateSupplierRequest {
  name: string;
  name_en?: string;
  supplier_type: SupplierType;
  status?: SupplierStatus;
  industry?: string;
  website?: string;
  description?: string;
  address?: string;
  phone?: string;
  email?: string;
  registration_number?: string;
  tax_id?: string;
  legal_representative?: string;
  registered_capital?: number;
  established_date?: string;
  business_scope?: string;
}

/**
 * 供应商更新请求
 */
export interface UpdateSupplierRequest {
  name?: string;
  name_en?: string;
  supplier_type?: SupplierType;
  status?: SupplierStatus;
  industry?: string;
  website?: string;
  description?: string;
  address?: string;
  phone?: string;
  email?: string;
  registration_number?: string;
  tax_id?: string;
  legal_representative?: string;
  registered_capital?: number;
  established_date?: string;
  business_scope?: string;
}

// ============ API 方法 ============

/**
 * 获取供应商列表（分页）
 */
export const getSuppliers = async (
  params?: SupplierQueryParams
): Promise<PaginatedResponse<Supplier>> => {
  const response = await apiClient.get('/suppliers/', { params });
  return response.data;
};

/**
 * 获取单个供应商详情
 * Week 7 Day 1-2 新增
 */
export const getSupplier = async (supplierId: number): Promise<Supplier> => {
  const response = await apiClient.get(`/suppliers/${supplierId}`);
  return response.data;
};

/**
 * 创建供应商
 */
export const createSupplier = async (
  data: CreateSupplierRequest
): Promise<Supplier> => {
  const response = await apiClient.post('/suppliers/', data);
  return response.data;
};

/**
 * 更新供应商
 */
export const updateSupplier = async (
  supplierId: number,
  data: UpdateSupplierRequest
): Promise<Supplier> => {
  const response = await apiClient.put(`/suppliers/${supplierId}`, data);
  return response.data;
};

/**
 * 删除供应商
 */
export const deleteSupplier = async (supplierId: number): Promise<void> => {
  await apiClient.delete(`/suppliers/${supplierId}`);
};

/**
 * 获取供应商联系人列表
 * Week 7 Day 4
 */
export const getSupplierContacts = async (
  supplierId: number
): Promise<SupplierContact[]> => {
  const response = await apiClient.get(`/suppliers/${supplierId}/contacts`);
  return response.data;
};

/**
 * 创建供应商联系人
 * Week 7 Day 4
 */
export interface CreateContactRequest {
  name: string;
  job_title?: string;
  phone?: string;
  email?: string;
  wechat?: string;
  qq?: string;
  is_primary?: boolean;
  remarks?: string;
}

export const createSupplierContact = async (
  supplierId: number,
  data: CreateContactRequest
): Promise<SupplierContact> => {
  const response = await apiClient.post(`/suppliers/${supplierId}/contacts`, data);
  return response.data;
};

/**
 * 更新供应商联系人
 * Week 7 Day 4
 */
export interface UpdateContactRequest {
  name?: string;
  job_title?: string;
  phone?: string;
  email?: string;
  wechat?: string;
  qq?: string;
  is_primary?: boolean;
  remarks?: string;
}

export const updateSupplierContact = async (
  supplierId: number,
  contactId: number,
  data: UpdateContactRequest
): Promise<SupplierContact> => {
  const response = await apiClient.put(
    `/suppliers/${supplierId}/contacts/${contactId}`,
    data
  );
  return response.data;
};

/**
 * 删除供应商联系人
 * Week 7 Day 4
 */
export const deleteSupplierContact = async (
  supplierId: number,
  contactId: number
): Promise<void> => {
  await apiClient.delete(`/suppliers/${supplierId}/contacts/${contactId}`);
};


/**
 * 获取供应商证书列表
 * Week 7 Day 5 预留
 */
export const getSupplierCertificates = async (
  supplierId: number
): Promise<SupplierCertificate[]> => {
  const response = await apiClient.get(`/suppliers/${supplierId}/certificates`);
  return response.data;
};

/**
 * 获取供应商风险评估历史
 * Week 7 Day 3 预留
 */
export const getSupplierRiskHistory = async (
  supplierId: number
): Promise<SupplierRiskAssessment[]> => {
  const response = await apiClient.get(`/suppliers/${supplierId}/risk-history`);
  return response.data;
};

/**
 * 触发供应商风险评估
 * Week 7 Day 4
 */
export const triggerRiskAssessment = async (
  supplierId: number
): Promise<SupplierRiskAssessment> => {
  const response = await apiClient.post(`/suppliers/${supplierId}/assess-risk`);
  return response.data;
};

// ============ Dashboard API ============

/**
 * 供应商统计数据
 */
export interface SupplierStats {
  total: number;
  active: number;
  pending: number;
  blacklisted: number;
  high_risk: number;
}

/**
 * 风险分布数据
 */
export interface RiskDistribution {
  very_low: number;
  low: number;
  medium: number;
  high: number;
  total: number;
}

/**
 * 高风险供应商
 */
export interface HighRiskSupplier {
  supplier_id: number;
  supplier_name: string;
  risk_level: string;
  risk_score: number;
  assessment_date: string;
  recommendations: string[];
}

/**
 * 获取供应商统计数据
 * Week 7 Day 4
 */
export const getSupplierStats = async (): Promise<SupplierStats> => {
  const response = await apiClient.get('/ceo/suppliers/stats');
  return response.data;
};

/**
 * 获取供应商风险分布
 * Week 7 Day 4
 */
export const getSupplierRiskDistribution = async (): Promise<RiskDistribution> => {
  const response = await apiClient.get('/ceo/suppliers/risk-distribution');
  return response.data;
};

/**
 * 获取高风险供应商列表
 * Week 7 Day 4
 */
export const getHighRiskSuppliers = async (): Promise<HighRiskSupplier[]> => {
  const response = await apiClient.get('/suppliers/high-risk');
  return response.data;
};

export default {
  getSuppliers,
  getSupplier,
  createSupplier,
  updateSupplier,
  deleteSupplier,
  getSupplierContacts,
  createSupplierContact,
  updateSupplierContact,
  deleteSupplierContact,
  getSupplierCertificates,
  getSupplierRiskHistory,
  triggerRiskAssessment,
  getSupplierStats,
  getSupplierRiskDistribution,
  getHighRiskSuppliers,
};
