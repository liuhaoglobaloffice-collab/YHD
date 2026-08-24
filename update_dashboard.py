#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重写 DashboardPage.tsx，接入真实 API"""

content = """/**
 * 系统总览 - 仪表板页面
 * 数据来源: /api/v1/dashboard/*
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

  // 统计卡片数据
  const statCards = [
    {
      name: '供应商总数',
      value: stats.total_suppliers,
      icon: Package,
      color: 'blue',
      bgColor: 'bg-blue-100',
      textColor: 'text-blue-600',
    },
    {
      name: '活跃供应商',
      value: stats.active_suppliers,
      icon: Activity,
      color: 'green',
      bgColor: 'bg-green-100',
      textColor: 'text-green-600',
    },
    {
      name: '本月新增',
      value: stats.new_suppliers_this_month,
      icon: TrendingUp,
      color: 'purple',
      bgColor: 'bg-purple-100',
      textColor: 'text-purple-600',
    },
    {
      name: '高风险供应商',
      value: stats.high_risk_suppliers,
      icon: AlertTriangle,
      color: 'orange',
      bgColor: 'bg-orange-100',
      textColor: 'text-orange-600',
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

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((card) => (
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

      {/* 业务类型分布 */}
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">业务类型分布</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.business_type_distribution.map((item) => (
            <div key={item.type} className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{item.count}</p>
              <p className="text-sm text-gray-600 mt-1">{item.type}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 风险等级分布 */}
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">风险等级分布</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <p className="text-2xl font-bold text-green-600">{stats.risk_distribution.low}</p>
            <p className="text-sm text-gray-600 mt-1">低风险</p>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <p className="text-2xl font-bold text-yellow-600">{stats.risk_distribution.medium}</p>
            <p className="text-sm text-gray-600 mt-1">中风险</p>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <p className="text-2xl font-bold text-orange-600">{stats.risk_distribution.high}</p>
            <p className="text-sm text-gray-600 mt-1">高风险</p>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <p className="text-2xl font-bold text-red-600">{stats.risk_distribution.critical}</p>
            <p className="text-sm text-gray-600 mt-1">严重风险</p>
          </div>
        </div>
      </div>

      {/* 最后更新时间 */}
      <div className="text-center text-sm text-gray-500">
        最后更新: {new Date(lastRefresh).toLocaleString('zh-CN')}
      </div>
    </div>
  );
};

export default DashboardPage;
"""

target_file = r"D:\LiuHao-AI-OS\frontend\src\pages\overview\DashboardPage.tsx"

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated: {target_file}")
