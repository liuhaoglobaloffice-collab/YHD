import apiService from './apiService';

/**
 * Dashboard 统计数据响应(匹配后端实际返回格式)
 */
export interface DashboardStats {
  timestamp: string;
  suppliers: {
    total: number;
    low_risk: number;
    medium_risk: number;
    high_risk: number;
    critical_risk: number;
  };
  risk_overview: {
    average_risk_score: number;
    suppliers_needing_attention: number;
    compliance_issues: number;
    quality_alerts: number;
  };
  business_metrics: {
    total_inquiries: number;
    active_orders: number;
    pending_quotes: number;
    this_month_revenue: number;
  };
  system_status: {
    ai_agents_active: number;
    tasks_in_progress: number;
    tasks_completed_today: number;
    system_health: string;
  };
  recent_alerts: Array<{
    id: number;
    type: string;
    severity: string;
    message: string;
    timestamp: string;
  }>;
}

/**
 * 趋势数据响应
 */
export interface DashboardTrends {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  daily_new_suppliers: Array<{
    date: string;
    count: number;
  }>;
}

/**
 * 优质供应商
 */
export interface TopSupplier {
  id: string;
  name: string;
  business_type: string;
  risk_level: string;
  status: string;
  contact_email: string;
}

/**
 * 警报
 */
export interface DashboardAlert {
  type: string;
  severity: 'critical' | 'high' | 'warning' | 'info';
  title: string;
  message: string;
  supplier_id?: string;
  created_at: string;
}

/**
 * 系统健康状态
 */
export interface SystemHealth {
  overall_status: string;
  components: Array<{
    name: string;
    status: string;
    load: number;
    last_check: string;
  }>;
  last_updated: string;
}

/**
 * 最近活动
 */
export interface RecentActivity {
  type: string;
  icon: string;
  event: string;
  time: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

/**
 * Dashboard API 服务
 */
class DashboardAPI {
  /**
   * 获取仪表板统计数据
   */
  async getStats(): Promise<DashboardStats> {
    return apiService.get<DashboardStats>('/dashboard/stats');
  }

  /**
   * 获取趋势数据
   */
  async getTrends(days: number = 30): Promise<DashboardTrends> {
    return apiService.get<DashboardTrends>('/dashboard/trends', {
      params: { days },
    });
  }

  /**
   * 获取优质供应商列表
   */
  async getTopSuppliers(limit: number = 10): Promise<TopSupplier[]> {
    return apiService.get<TopSupplier[]>('/dashboard/top-suppliers', {
      params: { limit },
    });
  }

  /**
   * 获取警报
   */
  async getAlerts(): Promise<DashboardAlert[]> {
    return apiService.get<DashboardAlert[]>('/dashboard/alerts');
  }

  /**
   * 获取系统健康状态
   */
  async getSystemHealth(): Promise<SystemHealth> {
    return apiService.get<SystemHealth>('/dashboard/system-health');
  }

  /**
   * 获取最近活动
   */
  async getRecentActivity(limit: number = 20): Promise<RecentActivity[]> {
    return apiService.get<RecentActivity[]>('/dashboard/recent-activity', {
      params: { limit },
    });
  }
}

export const dashboardAPI = new DashboardAPI();
export default dashboardAPI;
