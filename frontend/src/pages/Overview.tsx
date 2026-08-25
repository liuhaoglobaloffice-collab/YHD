/**
 * CEO Dashboard Overview - 赛博朋克版本
 * 核心功能：业务数据可视化 + AI员工监控 + 系统健康度
 * 赛博朋克风格：霓虹卡片 + 玻璃态 + 动态图表 + 语音激活按钮
 */

import { useState, useEffect } from 'react';
import { TrendingUp, Users, ListTodo, DollarSign, Mic, Activity } from 'lucide-react';
import { apiService, AIEmployee } from '../services/api';
import { Card } from '../components/ui/Card';

export default function Overview() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const employeeData = await apiService.listEmployees();
      setEmployees(employeeData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const stats = [
    { 
      name: 'AI 员工总数', 
      value: employees.length, 
      icon: Users, 
      color: 'neon-blue',
      change: '+12%'
    },
    { 
      name: '活跃任务', 
      value: 0, 
      icon: ListTodo, 
      color: 'neon-green',
      change: '+8%'
    },
    { 
      name: '本月营收', 
      value: '$0', 
      icon: DollarSign, 
      color: 'neon-yellow',
      change: '+23%'
    },
    { 
      name: '系统效率', 
      value: '95%', 
      icon: TrendingUp, 
      color: 'neon-purple',
      change: '+5%'
    },
  ];

  if (loading) {
    return (
      <div className="p-8 min-h-screen bg-primary-bg">
        <div className="flex items-center justify-center h-screen">
          <div className="neon-text-blue text-2xl font-bold animate-pulse">
            系统启动中...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 min-h-screen bg-primary-bg relative">
      {/* 语音激活按钮 - 悬浮在右下角 */}
      <button 
        className="fixed bottom-8 right-8 w-16 h-16 rounded-full bg-neon-blue/20 border-2 border-neon-blue neon-glow-blue hover:scale-110 transition-transform duration-300 z-50 flex items-center justify-center group"
        title="嘿鎏灏 - 语音激活"
      >
        <Mic className="w-8 h-8 text-neon-blue group-hover:animate-pulse" />
      </button>
      
      <div className="mb-8">
        <h1 className="text-4xl font-bold neon-text-blue mb-2">CEO 控制台</h1>
        <p className="text-text-muted">欢迎回来，以下是您的业务概览</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.name} className="relative overflow-hidden hover-glow">
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg bg-${stat.color}/10 border border-${stat.color}/30`}>
                  <Icon className={`w-6 h-6 text-${stat.color}`} />
                </div>
                <span className="text-sm font-medium text-neon-green">{stat.change}</span>
              </div>
              <p className="text-text-muted text-sm">{stat.name}</p>
              <p className="text-3xl font-bold text-text-primary mt-2">{stat.value}</p>
              {/* 霓虹边框效果 */}
              <div className={`absolute inset-0 border border-${stat.color}/20 rounded-lg pointer-events-none`}></div>
            </Card>
          );
        })}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-surface-border/50">
            <h2 className="text-xl font-bold text-text-primary flex items-center">
              <Users className="w-6 h-6 text-neon-cyan mr-2" />
              AI 员工监控
            </h2>
          </div>
          <div className="p-6">
            {employees.length > 0 ? (
              <div className="space-y-4">
                {employees.slice(0, 5).map((employee) => (
                  <div key={employee.id} className="flex items-center justify-between py-3 border-b border-surface-border/30 last:border-0 hover:bg-glass-light transition-colors rounded px-2">
                    <div>
                      <p className="font-medium text-text-primary">{employee.name}</p>
                      <p className="text-sm text-text-muted">{employee.position}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      employee.status === 'active' ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' : 'bg-glass-light text-text-muted border border-surface-border/30'
                    }`}>
                      {employee.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-text-muted text-center py-8">暂无 AI 员工</p>
            )}
          </div>
        </Card>

        <Card className="overflow-hidden">
          <div className="p-6 border-b border-surface-border/50">
            <h2 className="text-xl font-bold text-text-primary flex items-center">
              <Activity className="w-6 h-6 text-neon-purple mr-2" />
              系统健康度
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-text-muted">CPU 使用率</span>
                  <span className="text-sm font-medium">25%</span>
                </div>
                <div className="w-full bg-glass-light rounded-full h-2 overflow-hidden border border-surface-border/30">
                  <div className="bg-neon-blue h-2 rounded-full neon-glow-blue animate-glow" style={{ width: '25%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-text-muted">内存使用率</span>
                  <span className="text-sm font-medium">45%</span>
                </div>
                <div className="w-full bg-glass-light rounded-full h-2 overflow-hidden border border-surface-border/30">
                  <div className="bg-neon-green h-2 rounded-full neon-glow-green animate-glow" style={{ width: '45%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-text-muted">API 响应时间</span>
                  <span className="text-sm font-medium">120ms</span>
                </div>
                <div className="w-full bg-glass-light rounded-full h-2 overflow-hidden border border-surface-border/30">
                  <div className="bg-neon-yellow h-2 rounded-full neon-glow-yellow animate-glow" style={{ width: '30%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
