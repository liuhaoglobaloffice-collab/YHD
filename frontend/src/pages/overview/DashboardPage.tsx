/**
 * 系统总览 - 仪表板页面
 * 数据来源: /api/v1/dashboard/stats
 */

import React, { useState, useEffect } from 'react';
import {
  Activity,
  Users,
  Package,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  DollarSign,
  FileText,
  ShoppingCart,
} from 'lucide-react';
import { dashboardAPI, DashboardStats } from '../../services/dashboardAPI';
import { useUIStore } from '../../stores/uiStore';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  
  const { showNotification } = useUIStore();

  // 加载数据
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await dashboardAPI.getStats();
      setStats(data);
      setLastRefresh(new Date());
    } catch (err: any) {
      const errorMsg = err?.detail || '加载仪表板数据失败';
      setError(errorMsg);
      showNotification('error', errorMsg);
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    fetchData();
    
    // 每 30 秒自动刷新
    const interval = setInterval(() => {
      fetchData();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  // 手动刷新
  const handleRefresh = () => {
    showNotification('info', '正在刷新数据...');
    fetchData();
  };

  // 加载状态
  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error && !stats) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  // 供应商统计卡片
  const supplierCards = [
    {
      name: '供应商总数',
      value: stats.suppliers.total,
      icon: Package,
      color: 'blue',
      bgColor: 'bg-blue-100',
      textColor: 'text-blue-600',
    },
    {
      name: '低风险',
      value: stats.suppliers.low_risk,
      icon: Activity,
      color: 'green',
      bgColor: 'bg-green-100',
      textColor: 'text-green-600',
    },
    {
      name: '中风险',
      value: stats.suppliers.medium_risk,
      icon: TrendingUp,
      color: 'yellow',
      bgColor: 'bg-yellow-100',
      textColor: 'text-yellow-600',
    },
    {
      name: '高风险',
      value: stats.suppliers.high_risk,
      icon: AlertTriangle,
      color: 'orange',
      bgColor: 'bg-orange-100',
      textColor: 'text-orange-600',
    },
    {
      name: '严重风险',
      value: stats.suppliers.critical_risk,
      icon: AlertTriangle,
      color: 'red',
      bgColor: 'bg-red-100',
      textColor: 'text-red-600',
    },
  ];

  // 业务指标卡片
  const businessCards = [
    {
      name: '询盘总数',
      value: stats.business_metrics.total_inquiries,
      icon: FileText,
      bgColor: 'bg-indigo-100',
      textColor: 'text-indigo-600',
    },
    {
      name: '活跃订单',
      value: stats.business_metrics.active_orders,
      icon: ShoppingCart,
      bgColor: 'bg-purple-100',
      textColor: 'text-purple-600',
    },
    {
      name: '待报价',
      value: stats.business_metrics.pending_quotes,
      icon: FileText,
      bgColor: 'bg-pink-100',
      textColor: 'text-pink-600',
    },
    {
      name: '本月营收',
      value: `$${stats.business_metrics.this_month_revenue.toLocaleString()}`,
      icon: DollarSign,
      bgColor: 'bg-emerald-100',
      textColor: 'text-emerald-600',
    },
  ];

  return (
    <div className="space-y-6 p-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">系统总览</h1>
          <p className="text-gray-600 mt-1">
            实时监控系统运行状态与关键指标
          </p>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>刷新</span>
        </button>
      </div>

      {/* 供应商统计 */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">供应商统计</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {supplierCards.map((card) => (
            <div
              key={card.name}
              className="bg-white rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">{card.name}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">
                    {card.value}
                  </p>
                </div>
                <div className={`w-12 h-12 rounded-lg ${card.bgColor} flex items-center justify-center`}>
                  <card.icon className={`w-6 h-6 ${card.textColor}`} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 业务指标 */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">业务指标</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {businessCards.map((card) => (
            <div
              key={card.name}
              className="bg-white rounded-lg p-6 border border-gray-200 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">{card.name}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-2">
                    {card.value}
                  </p>
                </div>
                <div className={`w-12 h-12 rounded-lg ${card.bgColor} flex items-center justify-center`}>
                  <card.icon className={`w-6 h-6 ${card.textColor}`} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 风险概览 */}
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">风险概览</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-gray-900">{stats.risk_overview.average_risk_score.toFixed(1)}</p>
            <p className="text-sm text-gray-600 mt-1">平均风险分</p>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <p className="text-2xl font-bold text-orange-600">{stats.risk_overview.suppliers_needing_attention}</p>
            <p className="text-sm text-gray-600 mt-1">需关注</p>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <p className="text-2xl font-bold text-yellow-600">{stats.risk_overview.compliance_issues}</p>
            <p className="text-sm text-gray-600 mt-1">合规问题</p>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <p className="text-2xl font-bold text-red-600">{stats.risk_overview.quality_alerts}</p>
            <p className="text-sm text-gray-600 mt-1">质量告警</p>
          </div>
        </div>
      </div>

      {/* 系统状态 */}
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">系统状态</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <p className="text-2xl font-bold text-blue-600">{stats.system_status.ai_agents_active}</p>
            <p className="text-sm text-gray-600 mt-1">AI 代理运行中</p>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <p className="text-2xl font-bold text-purple-600">{stats.system_status.tasks_in_progress}</p>
            <p className="text-sm text-gray-600 mt-1">任务进行中</p>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <p className="text-2xl font-bold text-green-600">{stats.system_status.tasks_completed_today}</p>
            <p className="text-sm text-gray-600 mt-1">今日完成</p>
          </div>
          <div className="text-center p-4 bg-emerald-50 rounded-lg">
            <p className="text-2xl font-bold text-emerald-600 uppercase">{stats.system_status.system_health}</p>
            <p className="text-sm text-gray-600 mt-1">系统健康度</p>
          </div>
        </div>
      </div>

      {/* 最近告警 */}
      {stats.recent_alerts.length > 0 && (
        <div className="bg-white rounded-lg p-6 border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">最近告警</h2>
          <div className="space-y-3">
            {stats.recent_alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border-l-4 ${
                  alert.severity === 'high' || alert.severity === 'critical'
                    ? 'bg-red-50 border-red-500'
                    : alert.severity === 'medium'
                    ? 'bg-yellow-50 border-yellow-500'
                    : 'bg-blue-50 border-blue-500'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-gray-900">
                      [{alert.type.toUpperCase()}] {alert.message}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      {new Date(alert.timestamp).toLocaleString('zh-CN')}
                    </p>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded ${
                      alert.severity === 'high' || alert.severity === 'critical'
                        ? 'bg-red-100 text-red-700'
                        : alert.severity === 'medium'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {alert.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 最后更新时间 */}
      <div className="text-center text-sm text-gray-500">
        最后更新: {new Date(lastRefresh).toLocaleString('zh-CN')}
        {stats.timestamp && (
          <> | 数据时间: {new Date(stats.timestamp).toLocaleString('zh-CN')}</>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
