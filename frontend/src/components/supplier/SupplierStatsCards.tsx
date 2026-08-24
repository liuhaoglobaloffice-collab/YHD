/**
 * Supplier Statistics Cards Component
 * Week 7 Day 4 - 供应商统计卡片
 */

import React from 'react';
import { Package, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { SupplierStats } from '../../services/supplierAPI';

interface SupplierStatsCardsProps {
  stats: SupplierStats | null;
  loading: boolean;
}

const SupplierStatsCards: React.FC<SupplierStatsCardsProps> = ({ stats, loading }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-gray-800 rounded-lg p-6 border border-gray-700 animate-pulse"
          >
            <div className="h-12 w-12 bg-gray-700 rounded-lg mb-4"></div>
            <div className="h-4 bg-gray-700 rounded w-24 mb-2"></div>
            <div className="h-8 bg-gray-700 rounded w-16"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const cards = [
    {
      title: '总供应商',
      value: stats.total,
      icon: Package,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-900/30',
      borderColor: 'border-cyan-700/50',
    },
    {
      title: '活跃供应商',
      value: stats.active,
      icon: CheckCircle,
      color: 'text-green-400',
      bgColor: 'bg-green-900/30',
      borderColor: 'border-green-700/50',
    },
    {
      title: '待审核',
      value: stats.pending,
      icon: AlertTriangle,
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-900/30',
      borderColor: 'border-yellow-700/50',
    },
    {
      title: '高风险',
      value: stats.high_risk,
      icon: XCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-900/30',
      borderColor: 'border-red-700/50',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.title}
            className={`${card.bgColor} rounded-lg p-6 border ${card.borderColor} 
              hover:scale-105 transition-transform duration-200 cursor-pointer
              relative overflow-hidden group`}
          >
            {/* 扫描线动画效果 */}
            <div className="absolute inset-0 opacity-0 group-hover:opacity-10 
              bg-gradient-to-b from-transparent via-white to-transparent 
              animate-scan pointer-events-none"></div>

            <div className="flex items-start justify-between">
              <div>
                <p className="text-gray-400 text-sm font-medium mb-2">{card.title}</p>
                <p className={`text-4xl font-bold ${card.color}`}>
                  {card.value.toLocaleString()}
                </p>
              </div>
              <div className={`${card.bgColor} ${card.color} p-3 rounded-lg border ${card.borderColor}`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>

            {/* 底部装饰线 */}
            <div className={`absolute bottom-0 left-0 right-0 h-1 ${card.color.replace('text-', 'bg-')} opacity-50`}></div>
          </div>
        );
      })}
    </div>
  );
};

export default SupplierStatsCards;
