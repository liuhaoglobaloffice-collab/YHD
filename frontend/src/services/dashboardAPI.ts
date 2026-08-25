import apiService from './apiService';

const normalizeSeverity = (value?: string): 'critical' | 'high' | 'warning' | 'info' => {
  const normalized = (value ?? 'info').toString().toLowerCase();
  if (normalized === 'critical') return 'critical';
  if (normalized === 'high') return 'high';
  if (normalized === 'warning' || normalized === 'medium') return 'warning';
  return 'info';
};

const normalizeAlertList = (alerts: any[] = []): DashboardAlert[] =>
  alerts.map((alert, index) => ({
    type: alert?.type ?? 'system',
    severity: normalizeSeverity(alert?.severity ?? alert?.level),
    title: alert?.title ?? alert?.message ?? '系统提醒',
    message: alert?.message ?? alert?.title ?? '系统提醒',
    supplier_id: alert?.supplier_id ?? alert?.supplierId,
    created_at: alert?.created_at ?? alert?.timestamp ?? new Date().toISOString(),
    id: alert?.id ?? index + 1,
  }));

const normalizeStats = (rawStats: any): DashboardStats => {
  const riskDistribution = rawStats?.risk_distribution ?? {};
  const suppliers = rawStats?.suppliers ?? {};
  const riskOverview = rawStats?.risk_overview ?? {};
  const businessMetrics = rawStats?.business_metrics ?? {};
  const systemStatus = rawStats?.system_status ?? {};

  return {
    timestamp: rawStats?.last_updated ?? rawStats?.timestamp ?? new Date().toISOString(),
    suppliers: {
      total: Number(rawStats?.total_suppliers ?? suppliers.total ?? 0),
      low_risk: Number(riskDistribution.low ?? suppliers.low_risk ?? 0),
      medium_risk: Number(riskDistribution.medium ?? suppliers.medium_risk ?? 0),
      high_risk: Number(riskDistribution.high ?? suppliers.high_risk ?? 0),
      critical_risk: Number(riskDistribution.critical ?? suppliers.critical_risk ?? 0),
    },
    risk_overview: {
      average_risk_score: Number(rawStats?.average_risk_score ?? riskOverview.average_risk_score ?? 0),
      suppliers_needing_attention: Number(rawStats?.suppliers_needing_attention ?? riskOverview.suppliers_needing_attention ?? 0),
      compliance_issues: Number(rawStats?.compliance_issues ?? riskOverview.compliance_issues ?? 0),
      quality_alerts: Number(rawStats?.quality_alerts ?? riskOverview.quality_alerts ?? 0),
    },
    business_metrics: {
      total_inquiries: Number(rawStats?.total_inquiries ?? businessMetrics.total_inquiries ?? 0),
      active_orders: Number(rawStats?.active_orders ?? businessMetrics.active_orders ?? 0),
      pending_quotes: Number(rawStats?.pending_quotes ?? businessMetrics.pending_quotes ?? 0),
      this_month_revenue: Number(rawStats?.this_month_revenue ?? businessMetrics.this_month_revenue ?? 0),
    },
    system_status: {
      ai_agents_active: Number(rawStats?.ai_agents_active ?? systemStatus.ai_agents_active ?? 0),
      tasks_in_progress: Number(rawStats?.tasks_in_progress ?? systemStatus.tasks_in_progress ?? 0),
      tasks_completed_today: Number(rawStats?.tasks_completed_today ?? systemStatus.tasks_completed_today ?? 0),
      system_health: String(rawStats?.system_health ?? systemStatus.system_health ?? 'healthy').toUpperCase(),
    },
    recent_alerts: normalizeAlertList(Array.isArray(rawStats?.recent_alerts) ? rawStats.recent_alerts : Array.isArray(rawStats?.alerts) ? rawStats.alerts : []),
  };
};

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
  recent_alerts: DashboardAlert[];
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
  id?: number;
  type: string;
  severity: 'critical' | 'high' | 'warning' | 'info';
  title?: string;
  message: string;
  supplier_id?: string;
  created_at?: string;
  timestamp?: string;
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
    const rawStats = await apiService.get<any>('/dashboard/stats');
    return normalizeStats(rawStats);
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
    const suppliers = await apiService.get<any[]>('/dashboard/top-suppliers', {
      params: { limit },
    });

    return Array.isArray(suppliers)
      ? suppliers.map((supplier) => ({
          id: String(supplier.id ?? ''),
          name: supplier.name ?? '未知供应商',
          business_type: supplier.business_type ?? supplier.supplier_type ?? 'unknown',
          risk_level: supplier.risk_level ?? 'unknown',
          status: supplier.status ?? 'active',
          contact_email: supplier.contact_email ?? supplier.email ?? '',
        }))
      : [];
  }

  /**
   * 获取警报
   */
  async getAlerts(): Promise<DashboardAlert[]> {
    const alerts = await apiService.get<any[]>('/dashboard/alerts');
    return normalizeAlertList(alerts);
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
    try {
      return await apiService.get<RecentActivity[]>('/dashboard/recent-activity', {
        params: { limit },
      });
    } catch (_error) {
      return [];
    }
  }
}

export const dashboardAPI = new DashboardAPI();
export default dashboardAPI;
