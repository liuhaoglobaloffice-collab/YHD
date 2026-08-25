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
  Bot,
} from 'lucide-react';
import { dashboardAPI, DashboardStats } from '../../services/dashboardAPI';
import { useUIStore } from '../../stores/uiStore';
import JarvisHologram from '../../components/JarvisHologram';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isJarvisOpen, setIsJarvisOpen] = useState(false);
  
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
      console.warn('Dashboard API unavailable', err);
      setError('仪表板数据当前不可用，无法继续填充实时指标。');
      showNotification('warning', '仪表板数据暂不可用，请稍后重试。');
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
      iconColor: 'text-neon-blue',
      glowColor: 'border-glow-blue',
    },
    {
      name: '低风险',
      value: stats.suppliers.low_risk,
      icon: Activity,
      iconColor: 'text-neon-green',
      glowColor: 'border-glow-green',
    },
    {
      name: '中风险',
      value: stats.suppliers.medium_risk,
      icon: TrendingUp,
      iconColor: 'text-neon-yellow',
      glowColor: 'border-glow-yellow',
    },
    {
      name: '高风险',
      value: stats.suppliers.high_risk,
      icon: AlertTriangle,
      iconColor: 'text-orange-400',
      glowColor: 'border-glow-yellow',
    },
    {
      name: '严重风险',
      value: stats.suppliers.critical_risk,
      icon: AlertTriangle,
      iconColor: 'text-neon-red',
      glowColor: 'border-glow-red',
    },
  ];

  // 业务指标卡片
  const businessCards = [
    {
      name: '询盘总数',
      value: stats.business_metrics.total_inquiries,
      icon: FileText,
      iconColor: 'text-neon-purple',
      glowColor: 'border-glow-purple',
    },
    {
      name: '活跃订单',
      value: stats.business_metrics.active_orders,
      icon: ShoppingCart,
      iconColor: 'text-neon-cyan',
      glowColor: 'border-glow-cyan',
    },
    {
      name: '待报价',
      value: stats.business_metrics.pending_quotes,
      icon: FileText,
      iconColor: 'text-neon-yellow',
      glowColor: 'border-glow-yellow',
    },
    {
      name: '本月营收',
      value: `$${stats.business_metrics.this_month_revenue.toLocaleString()}`,
      icon: DollarSign,
      iconColor: 'text-neon-green',
      glowColor: 'border-glow-green',
    },
  ];

  return (
    <div className="space-y-6 p-6 min-h-screen">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neon-cyan neon-text-cyan">系统总览</h1>
          <p className="text-text-secondary mt-1">
            实时监控系统运行状态与关键指标
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          {/* Jarvis AI 助手按钮 */}
          <button
            onClick={() => setIsJarvisOpen(true)}
            className="flex items-center space-x-2 px-4 py-3 glass border-glow-cyan rounded-lg hover:border-glow-blue hover:scale-105 transition-all group"
          >
            <Bot className="w-5 h-5 text-neon-cyan group-hover:animate-pulse-glow" />
            <span className="text-neon-cyan font-semibold">Jarvis AI</span>
            <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
          </button>

          {/* 刷新按钮 */}
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 glass border-glow-blue rounded-lg hover:border-glow-cyan transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 text-neon-cyan ${loading ? 'animate-spin' : ''}`} />
            <span className="text-neon-cyan">刷新</span>
          </button>
        </div>
      </div>

      {/* 供应商统计 */}
      <div>
        <h2 className="text-xl font-bold text-neon-cyan neon-text-cyan mb-6">供应商统计</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {supplierCards.map((card) => (
            <div
              key={card.name}
              className={`glass rounded-lg p-6 ${card.glowColor} hover:scale-105 transition-all duration-300 animate-float`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-secondary mb-2">{card.name}</p>
                  <p className="text-4xl font-bold text-white neon-text-blue mt-1">
                    {card.value}
                  </p>
                </div>
                <div className="relative">
                  <card.icon className={`w-10 h-10 ${card.iconColor} animate-pulse-glow`} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 业务指标 */}
      <div>
        <h2 className="text-xl font-bold text-neon-cyan neon-text-cyan mb-6">业务指标</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {businessCards.map((card) => (
            <div
              key={card.name}
              className={`glass rounded-lg p-6 ${card.glowColor} hover:scale-105 transition-all duration-300`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-secondary mb-2">{card.name}</p>
                  <p className="text-3xl font-bold text-white neon-text-cyan mt-1">
                    {card.value}
                  </p>
                </div>
                <div className="relative">
                  <card.icon className={`w-10 h-10 ${card.iconColor} animate-pulse-glow`} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 风险概览 */}
      <div className="glass rounded-lg p-6 border-glow-yellow">
        <h2 className="text-xl font-bold text-neon-yellow neon-text-yellow mb-6">风险概览</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 glass-md rounded-lg border-glow-blue">
            <p className="text-3xl font-bold text-neon-blue neon-text-blue">{stats.risk_overview.average_risk_score.toFixed(1)}</p>
            <p className="text-sm text-text-secondary mt-2">平均风险分</p>
          </div>
          <div className="text-center p-4 glass-md rounded-lg border-glow-yellow">
            <p className="text-3xl font-bold text-neon-yellow neon-text-yellow">{stats.risk_overview.suppliers_needing_attention}</p>
            <p className="text-sm text-text-secondary mt-2">需关注</p>
          </div>
          <div className="text-center p-4 glass-md rounded-lg border-glow-yellow">
            <p className="text-3xl font-bold text-orange-400">{stats.risk_overview.compliance_issues}</p>
            <p className="text-sm text-text-secondary mt-2">合规问题</p>
          </div>
          <div className="text-center p-4 glass-md rounded-lg border-glow-red">
            <p className="text-3xl font-bold text-neon-red neon-text-red">{stats.risk_overview.quality_alerts}</p>
            <p className="text-sm text-text-secondary mt-2">质量告警</p>
          </div>
        </div>
      </div>

      {/* 系统状态 */}
      <div className="glass rounded-lg p-6 border-glow-green">
        <h2 className="text-xl font-bold text-neon-green neon-text-green mb-6">系统状态</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 glass-md rounded-lg border-glow-cyan animate-pulse">
            <p className="text-3xl font-bold text-neon-cyan neon-text-cyan">{stats.system_status.ai_agents_active}</p>
            <p className="text-sm text-text-secondary mt-2">AI 代理运行中</p>
          </div>
          <div className="text-center p-4 glass-md rounded-lg border-glow-purple">
            <p className="text-3xl font-bold text-neon-purple neon-text-purple">{stats.system_status.tasks_in_progress}</p>
            <p className="text-sm text-text-secondary mt-2">任务进行中</p>
          </div>
          <div className="text-center p-4 glass-md rounded-lg border-glow-green">
            <p className="text-3xl font-bold text-neon-green neon-text-green">{stats.system_status.tasks_completed_today}</p>
            <p className="text-sm text-text-secondary mt-2">今日完成</p>
          </div>
          <div className="text-center p-4 glass-md rounded-lg border-glow-green animate-glow">
            <p className="text-2xl font-bold text-neon-green neon-text-green uppercase">{stats.system_status.system_health}</p>
            <p className="text-sm text-text-secondary mt-2">系统健康度</p>
          </div>
        </div>
      </div>

      {/* 最近告警 */}
      {stats.recent_alerts.length > 0 && (
        <div className="glass rounded-lg p-6 border-glow-red animate-scan">
          <h2 className="text-xl font-bold text-neon-red neon-text-red mb-6">最近告警</h2>
          <div className="space-y-3">
            {stats.recent_alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border-l-4 ${
                  alert.severity === 'high' || alert.severity === 'critical'
                    ? 'glass-md border-neon-red animate-pulse-glow'
                    : alert.severity === 'warning'
                    ? 'glass-md border-neon-yellow'
                    : 'glass-md border-neon-blue'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-white">
                      [{alert.type.toUpperCase()}] {alert.message}
                    </p>
                    <p className="text-sm text-text-secondary mt-1">
                      {new Date(alert.timestamp ?? alert.created_at ?? Date.now().toString()).toLocaleString('zh-CN')}
                    </p>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded ${
                      alert.severity === 'high' || alert.severity === 'critical'
                        ? 'bg-neon-red/20 text-neon-red border border-neon-red'
                        : alert.severity === 'warning'
                        ? 'bg-neon-yellow/20 text-neon-yellow border border-neon-yellow'
                        : 'bg-neon-blue/20 text-neon-blue border border-neon-blue'
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
      <div className="text-center text-sm text-text-secondary glass-md rounded-lg p-3 border-glow-blue">
        最后更新: {new Date(lastRefresh).toLocaleString('zh-CN')}
        {stats.timestamp && (
          <> | 数据时间: {new Date(stats.timestamp).toLocaleString('zh-CN')}</>
        )}
      </div>

      {/* Jarvis AI 助手 */}
      <JarvisHologram
        isOpen={isJarvisOpen}
        onClose={() => setIsJarvisOpen(false)}
      />
    </div>
  );
};

export default DashboardPage;
