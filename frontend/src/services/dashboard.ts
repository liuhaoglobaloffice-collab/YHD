/**
 * Dashboard 数据服务层
 * 负责Dashboard相关的所有API调用、数据格式处理、状态同步
 */

import dashboardAPI, { DashboardStats } from './dashboardAPI';
import workforceAPI, { AIEmployee } from './workforceAPI';

/**
 * CEO今日简报项
 */
export interface CEOBriefItem {
  id: string;
  type: 'decision' | 'problem' | 'alert' | 'task';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  timestamp: string;
  actionable: boolean;
  link?: string;
}

/**
 * AI员工状态统计
 */
export interface AIWorkforceStatus {
  total: number;
  active: number;
  idle: number;
  error: number;
  employees: AIEmployee[];
  currentTasks: number;
  completedToday: number;
  efficiency: number; // 0-100
}

/**
 * 企业核心指标
 */
export interface EnterpriseMetrics {
  customers: {
    total: number;
    trend: number; // 百分比变化
  };
  opportunities: {
    total: number;
    trend: number;
  };
  revenue: {
    value: number;
    trend: number;
    currency: string;
  };
  systemHealth: {
    status: 'healthy' | 'warning' | 'critical';
    score: number; // 0-100
  };
}

/**
 * Sales Pipeline 数据
 */
export interface SalesPipelineData {
  stages: {
    name: string;
    count: number;
    value: number; // 金额
  }[];
  conversionRate: number;
  avgDealTime: number; // 平均成交时间（天）
}

/**
 * Dashboard 完整数据
 */
export interface DashboardData {
  ceoBrief: CEOBriefItem[];
  workforceStatus: AIWorkforceStatus;
  metrics: EnterpriseMetrics;
  pipeline: SalesPipelineData;
  trends: {
    labels: string[];
    revenue: number[];
    customers: number[];
    tasks: number[];
  };
  lastUpdate: string;
}

class DashboardService {
  /**
   * 获取CEO今日简报
   */
  async getCEOBrief(): Promise<CEOBriefItem[]> {
    try {
      // 获取系统警报
      const alerts = await dashboardAPI.getAlerts();
      const stats = await dashboardAPI.getStats();

      const brief: CEOBriefItem[] = [];

      // 1. 高优先级警报
      const criticalAlerts = alerts.filter(a => a.severity === 'critical');
      criticalAlerts.slice(0, 2).forEach(alert => {
        brief.push({
          id: `alert-${Date.now()}-${Math.random()}`,
          type: 'alert',
          priority: 'high',
          title: alert.title ?? '系统提醒',
          description: alert.message,
          timestamp: String(alert.created_at ?? alert.timestamp ?? new Date().toISOString()),
          actionable: true,
          link: alert.supplier_id ? `/suppliers/${alert.supplier_id}` : undefined,
        });
      });

      // 2. 需要关注的供应商
      if (stats.risk_overview.suppliers_needing_attention > 0) {
        brief.push({
          id: 'suppliers-attention',
          type: 'problem',
          priority: 'high',
          title: '供应商风险提醒',
          description: `有 ${stats.risk_overview.suppliers_needing_attention} 家供应商需要关注`,
          timestamp: stats.timestamp,
          actionable: true,
          link: '/suppliers?filter=risk',
        });
      }

      // 3. 系统任务进度
      if (stats.system_status.tasks_in_progress > 0) {
        brief.push({
          id: 'tasks-progress',
          type: 'task',
          priority: 'medium',
          title: 'AI任务执行中',
          description: `${stats.system_status.tasks_in_progress} 个任务正在处理，今日已完成 ${stats.system_status.tasks_completed_today} 个`,
          timestamp: stats.timestamp,
          actionable: false,
        });
      }

      // 4. 业务机会
      if (stats.business_metrics.pending_quotes > 0) {
        brief.push({
          id: 'pending-quotes',
          type: 'decision',
          priority: 'medium',
          title: '待处理报价',
          description: `有 ${stats.business_metrics.pending_quotes} 个报价等待处理`,
          timestamp: stats.timestamp,
          actionable: true,
          link: '/quotes',
        });
      }

      // 5. 合规问题
      if (stats.risk_overview.compliance_issues > 0) {
        brief.push({
          id: 'compliance',
          type: 'alert',
          priority: 'high',
          title: '合规问题',
          description: `发现 ${stats.risk_overview.compliance_issues} 个合规问题需要处理`,
          timestamp: stats.timestamp,
          actionable: true,
          link: '/compliance',
        });
      }

      // 按优先级排序
      return brief.sort((a, b) => {
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      }).slice(0, 6); // 最多6条

    } catch (error) {
      console.error('Failed to get CEO brief:', error);
      return [];
    }
  }

  /**
   * 获取AI员工状态
   */
  async getWorkforceStatus(): Promise<AIWorkforceStatus> {
    try {
      const employees = await workforceAPI.listEmployees();
      const stats = await dashboardAPI.getStats();

      const activeCount = employees.filter(e => e.status === 'active').length;
      const idleCount = employees.filter(e => e.status === 'created').length;
      const errorCount = employees.filter(e => e.status === 'suspended').length;

      // 效率计算：今日完成任务数 / (活跃员工数 * 8) * 100
      const efficiency = activeCount > 0
        ? Math.min(100, (stats.system_status.tasks_completed_today / (activeCount * 8)) * 100)
        : 0;

      return {
        total: employees.length,
        active: activeCount,
        idle: idleCount,
        error: errorCount,
        employees: employees.slice(0, 10), // 只返回前10个
        currentTasks: stats.system_status.tasks_in_progress,
        completedToday: stats.system_status.tasks_completed_today,
        efficiency: Math.round(efficiency),
      };
    } catch (error) {
      console.error('Failed to get workforce status:', error);
      return {
        total: 0,
        active: 0,
        idle: 0,
        error: 0,
        employees: [],
        currentTasks: 0,
        completedToday: 0,
        efficiency: 0,
      };
    }
  }

  /**
   * 获取企业核心指标
   */
  async getEnterpriseMetrics(): Promise<EnterpriseMetrics> {
    try {
      const stats = await dashboardAPI.getStats();
      const systemHealth = await dashboardAPI.getSystemHealth();

      // 计算系统健康分数
      const healthyComponents = systemHealth.components.filter(c => c.status === 'healthy').length;
      const healthScore = (healthyComponents / systemHealth.components.length) * 100;

      return {
        customers: {
          total: stats.suppliers.total,
          trend: 0, // TODO: 计算趋势需要历史数据
        },
        opportunities: {
          total: stats.business_metrics.total_inquiries,
          trend: 0,
        },
        revenue: {
          value: stats.business_metrics.this_month_revenue,
          trend: 0,
          currency: 'USD',
        },
        systemHealth: {
          status: systemHealth.overall_status === 'healthy' ? 'healthy' 
                 : systemHealth.overall_status === 'degraded' ? 'warning' 
                 : 'critical',
          score: Math.round(healthScore),
        },
      };
    } catch (error) {
      console.error('Failed to get enterprise metrics:', error);
      return {
        customers: { total: 0, trend: 0 },
        opportunities: { total: 0, trend: 0 },
        revenue: { value: 0, trend: 0, currency: 'USD' },
        systemHealth: { status: 'warning', score: 0 },
      };
    }
  }

  /**
   * 获取Sales Pipeline数据
   */
  async getSalesPipeline(): Promise<SalesPipelineData> {
    try {
      const stats = await dashboardAPI.getStats();

      // 模拟Pipeline数据（实际应该从专门的Sales API获取）
      return {
        stages: [
          { name: 'Lead', count: stats.business_metrics.total_inquiries, value: 0 },
          { name: 'Contact', count: Math.floor(stats.business_metrics.total_inquiries * 0.7), value: 0 },
          { name: 'Qualification', count: Math.floor(stats.business_metrics.total_inquiries * 0.5), value: 0 },
          { name: 'Proposal', count: stats.business_metrics.pending_quotes, value: 0 },
          { name: 'Negotiation', count: Math.floor(stats.business_metrics.pending_quotes * 0.6), value: 0 },
          { name: 'Order', count: stats.business_metrics.active_orders, value: stats.business_metrics.this_month_revenue },
        ],
        conversionRate: stats.business_metrics.total_inquiries > 0 
          ? (stats.business_metrics.active_orders / stats.business_metrics.total_inquiries) * 100 
          : 0,
        avgDealTime: 30, // 平均30天
      };
    } catch (error) {
      console.error('Failed to get sales pipeline:', error);
      return {
        stages: [],
        conversionRate: 0,
        avgDealTime: 0,
      };
    }
  }

  /**
   * 获取趋势数据
   */
  async getTrends(days: number = 7): Promise<DashboardData['trends']> {
    try {
      const trends = await dashboardAPI.getTrends(days);

      // 生成日期标签
      const labels = trends.daily_new_suppliers.map(d => {
        const date = new Date(d.date);
        return `${date.getMonth() + 1}/${date.getDate()}`;
      });

      // 模拟数据（实际应该从API获取）
      const revenue = trends.daily_new_suppliers.map(d => d.count * 5000);
      const customers = trends.daily_new_suppliers.map(d => d.count);
      const tasks = trends.daily_new_suppliers.map(d => Math.floor(d.count * 3));

      return {
        labels,
        revenue,
        customers,
        tasks,
      };
    } catch (error) {
      console.error('Failed to get trends:', error);
      return {
        labels: [],
        revenue: [],
        customers: [],
        tasks: [],
      };
    }
  }

  /**
   * 获取完整Dashboard数据
   */
  async getDashboardData(): Promise<DashboardData> {
    try {
      const [ceoBrief, workforceStatus, metrics, pipeline, trends] = await Promise.all([
        this.getCEOBrief(),
        this.getWorkforceStatus(),
        this.getEnterpriseMetrics(),
        this.getSalesPipeline(),
        this.getTrends(7),
      ]);

      return {
        ceoBrief,
        workforceStatus,
        metrics,
        pipeline,
        trends,
        lastUpdate: new Date().toISOString(),
      };
    } catch (error) {
      console.error('Failed to get dashboard data:', error);
      throw error;
    }
  }

  /**
   * 刷新Dashboard数据
   */
  async refreshDashboard(): Promise<DashboardData> {
    return this.getDashboardData();
  }
}

export const dashboardService = new DashboardService();
export default dashboardService;
