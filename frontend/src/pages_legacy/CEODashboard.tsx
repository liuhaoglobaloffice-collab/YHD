/**
 * CEO 桌面 - 鎏灏 AI-OS 主控制台
 * 科技风格首页
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  Users,
  Briefcase,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  Zap,
  Globe,
  Package,
  BarChart3,
  ArrowRight,
  Clock,
  Target,
  Layers,
  Database,
  Cpu,
  Server,
  Shield,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  // 核心指标
  const coreMetrics = [
    {
      name: '供应商总数',
      value: '328',
      change: '+24',
      trend: 'up',
      icon: Package,
      color: 'cyan',
      path: '/business/supplier/list'
    },
    {
      name: 'AI 任务执行',
      value: '156',
      change: '+12',
      trend: 'up',
      icon: Zap,
      color: 'purple',
      path: '/ai-team/employees'
    },
    {
      name: '全球市场',
      value: '25',
      change: '+3',
      trend: 'up',
      icon: Globe,
      color: 'blue',
      path: '/business/supplier/command'
    },
    {
      name: '业务机会',
      value: '89',
      change: '+18',
      trend: 'up',
      icon: Target,
      color: 'green',
      path: '/business/supplier/command'
    },
  ];

  // 快速访问
  const quickAccess = [
    {
      title: '指挥中心',
      subtitle: 'Command Center',
      description: '全息AI助手 · 实时监控',
      icon: Layers,
      color: 'cyan',
      path: '/business/supplier/command',
      badge: 'HOT'
    },
    {
      title: '供应商管理',
      subtitle: 'Supplier Management',
      description: '情报分析 · 风险评估',
      icon: Package,
      color: 'blue',
      path: '/business/supplier/list',
      badge: 'NEW'
    },
    {
      title: 'AI 团队',
      subtitle: 'AI Employees',
      description: '24 个智能代理在线',
      icon: Users,
      color: 'purple',
      path: '/ai-team/employees',
      badge: null
    },
    {
      title: '数据分析',
      subtitle: 'Analytics',
      description: '业务洞察 · 智能报告',
      icon: BarChart3,
      color: 'green',
      path: '/business/supplier/intelligence',
      badge: null
    },
  ];

  // 系统状态
  const systemStatus = [
    { name: 'AI Brain', status: 'online', load: 85, color: 'green' },
    { name: 'Database', status: 'online', load: 62, color: 'green' },
    { name: 'API Gateway', status: 'online', load: 45, color: 'green' },
    { name: 'Security', status: 'protected', load: 100, color: 'blue' },
  ];

  // 最近活动
  const recentActivity = [
    { time: '刚刚', event: 'AI 完成泰国市场分析报告', type: 'success', icon: CheckCircle },
    { time: '2分钟前', event: '新增 8 家优质供应商', type: 'info', icon: Package },
    { time: '5分钟前', event: '智能审核系统运行正常', type: 'success', icon: Shield },
    { time: '10分钟前', event: '全球市场数据更新完成', type: 'info', icon: Globe },
    { time: '15分钟前', event: 'CEO 任务优先级调整', type: 'warning', icon: Target },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0e27] via-[#0f1433] to-[#1a1f4d] text-white p-6">
      {/* 背景效果 */}
      <div className="fixed inset-0 opacity-30 pointer-events-none">
        <div className="absolute top-0 left-0 w-96 h-96 bg-cyan-500 rounded-full filter blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-500 rounded-full filter blur-3xl animate-pulse"></div>
      </div>

      {/* 网格背景 */}
      <div className="fixed inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAgTSAwIDIwIEwgNDAgMjAgTSAyMCAwIEwgMjAgNDAgTSAwIDMwIEwgNDAgMzAgTSAzMCAwIEwgMzAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgwLDE5OSwyNTUsMC4xKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-20 pointer-events-none"></div>

      <div className="relative z-10 max-w-7xl mx-auto space-y-6">
        {/* 顶部欢迎区 */}
        <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-2xl border border-cyan-500/30 p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full filter blur-3xl"></div>
          <div className="relative flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-300 via-blue-300 to-purple-300 bg-clip-text text-transparent mb-2">
                欢迎回来，CEO
              </h1>
              <p className="text-cyan-400 text-lg">鎏灏 AI-OS · 您的智能商业伙伴</p>
              <p className="text-white/60 text-sm mt-2">Intelligent · Autonomous · Global</p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-mono text-cyan-300 mb-1">{formatTime(time)}</div>
              <div className="text-sm text-white/60">深圳 · 26°C · 晴</div>
              <div className="flex items-center justify-end space-x-2 mt-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-xs text-green-400">系统运行正常</span>
              </div>
            </div>
          </div>
        </div>

        {/* 核心指标 */}
        <div className="grid grid-cols-4 gap-4">
          {coreMetrics.map((metric, index) => {
            const Icon = metric.icon;
            return (
              <div
                key={index}
                onClick={() => navigate(metric.path)}
                className={`bg-gradient-to-br ${
                  metric.color === 'cyan' ? 'from-cyan-600/20 to-cyan-600/5 border-cyan-500/30' :
                  metric.color === 'purple' ? 'from-purple-600/20 to-purple-600/5 border-purple-500/30' :
                  metric.color === 'blue' ? 'from-blue-600/20 to-blue-600/5 border-blue-500/30' :
                  'from-green-600/20 to-green-600/5 border-green-500/30'
                } backdrop-blur-md rounded-xl border p-6 hover:scale-105 transition-all cursor-pointer group`}
              >
                <div className="flex items-start justify-between mb-4">
                  <Icon className={`w-10 h-10 ${
                    metric.color === 'cyan' ? 'text-cyan-400' :
                    metric.color === 'purple' ? 'text-purple-400' :
                    metric.color === 'blue' ? 'text-blue-400' :
                    'text-green-400'
                  }`} />
                  {metric.trend === 'up' && (
                    <div className="flex items-center text-green-400 text-sm">
                      <TrendingUp className="w-4 h-4 mr-1" />
                      <span>{metric.change}</span>
                    </div>
                  )}
                </div>
                <div className="text-3xl font-bold text-white mb-1">{metric.value}</div>
                <div className="text-sm text-white/70">{metric.name}</div>
                <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
                  <ArrowRight className="w-5 h-5 text-cyan-400" />
                </div>
              </div>
            );
          })}
        </div>

        {/* 快速访问 */}
        <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-2xl border border-cyan-500/30 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-cyan-300">快速访问</h2>
            <span className="text-sm text-cyan-400">Quick Access</span>
          </div>
          <div className="grid grid-cols-4 gap-4">
            {quickAccess.map((item, index) => {
              const Icon = item.icon;
              return (
                <div
                  key={index}
                  onClick={() => navigate(item.path)}
                  className={`relative bg-gradient-to-br ${
                    item.color === 'cyan' ? 'from-cyan-600/10 to-black/20 border-cyan-500/30 hover:border-cyan-400/60' :
                    item.color === 'blue' ? 'from-blue-600/10 to-black/20 border-blue-500/30 hover:border-blue-400/60' :
                    item.color === 'purple' ? 'from-purple-600/10 to-black/20 border-purple-500/30 hover:border-purple-400/60' :
                    'from-green-600/10 to-black/20 border-green-500/30 hover:border-green-400/60'
                  } backdrop-blur-sm rounded-xl border p-6 hover:scale-105 transition-all cursor-pointer group overflow-hidden`}
                >
                  {item.badge && (
                    <div className="absolute top-2 right-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        item.badge === 'HOT' ? 'bg-red-500/20 text-red-300 border border-red-500/50' :
                        'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                      }`}>
                        {item.badge}
                      </span>
                    </div>
                  )}
                  <Icon className={`w-12 h-12 mb-4 ${
                    item.color === 'cyan' ? 'text-cyan-400' :
                    item.color === 'blue' ? 'text-blue-400' :
                    item.color === 'purple' ? 'text-purple-400' :
                    'text-green-400'
                  }`} />
                  <h3 className="text-xl font-bold text-white mb-1">{item.title}</h3>
                  <p className="text-sm text-cyan-400 mb-2">{item.subtitle}</p>
                  <p className="text-xs text-white/60">{item.description}</p>
                  <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ArrowRight className="w-5 h-5 text-cyan-400" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 底部面板：系统状态 + 最近活动 */}
        <div className="grid grid-cols-2 gap-6">
          {/* 系统状态 */}
          <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-2xl border border-green-500/30 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-green-300">系统状态</h2>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-green-400">全部在线</span>
              </div>
            </div>
            <div className="space-y-4">
              {systemStatus.map((system, index) => (
                <div key={index} className="flex items-center justify-between p-3 rounded-lg hover:bg-white/5 transition-all">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      system.color === 'green' ? 'bg-green-400 shadow-lg shadow-green-400/50' :
                      'bg-blue-400 shadow-lg shadow-blue-400/50'
                    }`}></div>
                    <span className="text-white/90">{system.name}</span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="w-32 h-2 bg-white/10 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${
                          system.color === 'green' ? 'bg-green-400' : 'bg-blue-400'
                        } transition-all`}
                        style={{ width: `${system.load}%` }}
                      ></div>
                    </div>
                    <span className="text-sm text-white/60 w-12 text-right">{system.load}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 最近活动 */}
          <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-2xl border border-cyan-500/30 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-cyan-300">最近活动</h2>
              <Clock className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="space-y-3">
              {recentActivity.map((activity, index) => {
                const Icon = activity.icon;
                return (
                  <div key={index} className="flex items-start space-x-3 p-3 rounded-lg hover:bg-white/5 transition-all group">
                    <Icon className={`w-5 h-5 mt-0.5 ${
                      activity.type === 'success' ? 'text-green-400' :
                      activity.type === 'warning' ? 'text-yellow-400' :
                      'text-cyan-400'
                    }`} />
                    <div className="flex-1">
                      <p className="text-sm text-white/90">{activity.event}</p>
                      <span className="text-xs text-white/50">{activity.time}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 目标横幅 */}
        <div className="bg-gradient-to-r from-yellow-600/20 via-orange-600/20 to-red-600/20 backdrop-blur-md rounded-2xl border-2 border-yellow-500/50 p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-48 h-48 bg-yellow-400/10 rounded-full filter blur-3xl"></div>
          <div className="relative flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-6xl">🚀</div>
              <div>
                <h3 className="text-2xl font-bold text-yellow-300 mb-1">我们的目标</h3>
                <p className="text-white/90 text-lg">Build a Global Brand · Achieve 100 Million Revenue</p>
              </div>
            </div>
            <button 
              onClick={() => navigate('/business/supplier/command')}
              className="px-6 py-3 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-400 hover:to-orange-400 rounded-lg font-bold text-white transition-all shadow-lg shadow-yellow-500/50"
            >
              进入指挥中心 →
            </button>
          </div>
        </div>
      </div>

      {/* 自定义动画 */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .animate-pulse {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
      `}</style>
    </div>
  );
};
