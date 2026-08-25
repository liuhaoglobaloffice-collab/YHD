/**
 * CEO Dashboard - 完整升级版
 * 包含：CEO今日简报、AI员工状态中心、企业核心指标、Sales Pipeline、实时数据
 */

import { useEffect, useState } from 'react';
import { 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  Users,
  DollarSign,
  Target,
  Activity,
  AlertTriangle,
  RefreshCw,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import { LineChart, BarChart, FunnelChart, RadarChart } from '../../components/Charts';
import { useDashboardStore } from '../../stores/dashboardStore';
import { CEOBriefItem } from '../../services/dashboard';

export default function CEODashboard() {
  const {
    data,
    loading,
    error,
    lastUpdate,
    wsConnected,
    realtimeEnabled,
    loadDashboard,
    refreshDashboard,
    connectWebSocket,
    disconnectWebSocket,
    markBriefAsRead,
    clearError,
  } = useDashboardStore();

  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    // 初始加载
    loadDashboard();

    // 连接WebSocket实时更新
    if (autoRefresh) {
      connectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, []);

  useEffect(() => {
    // 自动刷新（30秒）
    if (autoRefresh && !realtimeEnabled) {
      const interval = setInterval(() => {
        refreshDashboard();
      }, 30000);

      return () => clearInterval(interval);
    }
  }, [autoRefresh, realtimeEnabled]);

  const handleRefresh = () => {
    refreshDashboard();
  };

  const handleToggleRealtime = () => {
    if (realtimeEnabled) {
      disconnectWebSocket();
      setAutoRefresh(false);
    } else {
      connectWebSocket();
      setAutoRefresh(true);
    }
  };

  const getBriefIcon = (type: CEOBriefItem['type']) => {
    switch (type) {
      case 'decision':
        return Target;
      case 'problem':
        return AlertTriangle;
      case 'alert':
        return AlertCircle;
      case 'task':
        return Clock;
      default:
        return CheckCircle;
    }
  };

  const getBriefColor = (priority: CEOBriefItem['priority']) => {
    switch (priority) {
      case 'high':
        return 'text-neon-red border-neon-red/30 bg-neon-red/10';
      case 'medium':
        return 'text-neon-yellow border-neon-yellow/30 bg-neon-yellow/10';
      case 'low':
        return 'text-neon-green border-neon-green/30 bg-neon-green/10';
      default:
        return 'text-neon-blue border-neon-blue/30 bg-neon-blue/10';
    }
  };

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-primary-bg flex items-center justify-center">
        <div className="text-center">
          <div className="neon-text-blue text-2xl font-bold animate-pulse mb-4">
            加载CEO驾驶舱...
          </div>
          <div className="text-text-muted">正在获取企业运营数据</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-primary-bg flex items-center justify-center">
        <Card className="max-w-md">
          <div className="p-6 text-center">
            <AlertCircle className="w-12 h-12 text-neon-red mx-auto mb-4" />
            <h2 className="text-xl font-bold text-text-primary mb-2">加载失败</h2>
            <p className="text-text-muted mb-4">{error}</p>
            <Button onClick={() => { clearError(); loadDashboard(); }}>
              重新加载
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-primary-bg p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold neon-text-blue mb-2">CEO 驾驶舱</h1>
          <p className="text-text-muted">
            企业运营实时监控 · 最后更新: {lastUpdate ? new Date(lastUpdate).toLocaleTimeString('zh-CN') : '--'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={handleToggleRealtime}
            className={realtimeEnabled ? 'border-neon-green' : ''}
          >
            {wsConnected ? (
              <Wifi className="w-4 h-4 mr-2 text-neon-green" />
            ) : (
              <WifiOff className="w-4 h-4 mr-2" />
            )}
            {realtimeEnabled ? '实时更新' : '手动更新'}
          </Button>
          <Button onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* CEO 今日简报 */}
      {data.ceoBrief.length > 0 && (
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-surface-border/50">
            <h2 className="text-2xl font-bold text-text-primary flex items-center">
              <Target className="w-6 h-6 text-neon-cyan mr-2" />
              今日简报
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.ceoBrief.map((item) => {
                const Icon = getBriefIcon(item.type);
                return (
                  <div
                    key={item.id}
                    className={`p-4 rounded-lg border ${getBriefColor(item.priority)} relative group`}
                  >
                    <button
                      onClick={() => markBriefAsRead(item.id)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-4 h-4" />
                    </button>
                    <div className="flex items-start gap-3">
                      <Icon className="w-5 h-5 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-sm mb-1">{item.title}</h3>
                        <p className="text-xs opacity-80 mb-2">{item.description}</p>
                        <div className="flex items-center justify-between text-xs opacity-60">
                          <span>{new Date(item.timestamp).toLocaleTimeString('zh-CN')}</span>
                          {item.actionable && <span className="font-medium">需要处理</span>}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {/* 企业核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* 客户数量 */}
        <Card className="relative overflow-hidden hover-glow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-neon-blue/10 border border-neon-blue/30">
                <Users className="w-6 h-6 text-neon-blue" />
              </div>
              {data.metrics.customers.trend !== 0 && (
                <span className={`text-sm font-medium flex items-center ${data.metrics.customers.trend > 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                  {data.metrics.customers.trend > 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                  {Math.abs(data.metrics.customers.trend).toFixed(1)}%
                </span>
              )}
            </div>
            <p className="text-text-muted text-sm mb-2">客户总数</p>
            <p className="text-3xl font-bold text-text-primary">{data.metrics.customers.total}</p>
          </div>
        </Card>

        {/* 商机数量 */}
        <Card className="relative overflow-hidden hover-glow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-neon-purple/10 border border-neon-purple/30">
                <Target className="w-6 h-6 text-neon-purple" />
              </div>
              {data.metrics.opportunities.trend !== 0 && (
                <span className={`text-sm font-medium flex items-center ${data.metrics.opportunities.trend > 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                  {data.metrics.opportunities.trend > 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                  {Math.abs(data.metrics.opportunities.trend).toFixed(1)}%
                </span>
              )}
            </div>
            <p className="text-text-muted text-sm mb-2">商机总数</p>
            <p className="text-3xl font-bold text-text-primary">{data.metrics.opportunities.total}</p>
          </div>
        </Card>

        {/* 本月营收 */}
        <Card className="relative overflow-hidden hover-glow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-lg bg-neon-green/10 border border-neon-green/30">
                <DollarSign className="w-6 h-6 text-neon-green" />
              </div>
              {data.metrics.revenue.trend !== 0 && (
                <span className={`text-sm font-medium flex items-center ${data.metrics.revenue.trend > 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                  {data.metrics.revenue.trend > 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                  {Math.abs(data.metrics.revenue.trend).toFixed(1)}%
                </span>
              )}
            </div>
            <p className="text-text-muted text-sm mb-2">本月营收</p>
            <p className="text-3xl font-bold text-text-primary">
              {data.metrics.revenue.currency} {data.metrics.revenue.value.toLocaleString()}
            </p>
          </div>
        </Card>

        {/* 系统健康 */}
        <Card className="relative overflow-hidden hover-glow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-lg ${
                data.metrics.systemHealth.status === 'healthy' ? 'bg-neon-green/10 border-neon-green/30' :
                data.metrics.systemHealth.status === 'warning' ? 'bg-neon-yellow/10 border-neon-yellow/30' :
                'bg-neon-red/10 border-neon-red/30'
              } border`}>
                <Activity className={`w-6 h-6 ${
                  data.metrics.systemHealth.status === 'healthy' ? 'text-neon-green' :
                  data.metrics.systemHealth.status === 'warning' ? 'text-neon-yellow' :
                  'text-neon-red'
                }`} />
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                data.metrics.systemHealth.status === 'healthy' ? 'bg-neon-green/20 text-neon-green' :
                data.metrics.systemHealth.status === 'warning' ? 'bg-neon-yellow/20 text-neon-yellow' :
                'bg-neon-red/20 text-neon-red'
              }`}>
                {data.metrics.systemHealth.status === 'healthy' ? '健康' :
                 data.metrics.systemHealth.status === 'warning' ? '警告' : '异常'}
              </span>
            </div>
            <p className="text-text-muted text-sm mb-2">系统健康度</p>
            <p className="text-3xl font-bold text-text-primary">{data.metrics.systemHealth.score}%</p>
          </div>
        </Card>
      </div>

      {/* AI 员工状态中心 */}
      <Card className="overflow-hidden">
        <div className="p-6 border-b border-surface-border/50">
          <h2 className="text-2xl font-bold text-text-primary flex items-center">
            <Users className="w-6 h-6 text-neon-cyan mr-2" />
            AI 员工状态中心
          </h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <div className="text-center">
              <div className="text-4xl font-bold text-neon-blue mb-2">{data.workforceStatus.total}</div>
              <div className="text-text-muted text-sm">员工总数</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-neon-green mb-2 flex items-center justify-center">
                🟢 {data.workforceStatus.active}
              </div>
              <div className="text-text-muted text-sm">工作中</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-neon-yellow mb-2 flex items-center justify-center">
                🟡 {data.workforceStatus.idle}
              </div>
              <div className="text-text-muted text-sm">等待任务</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-neon-red mb-2 flex items-center justify-center">
                🔴 {data.workforceStatus.error}
              </div>
              <div className="text-text-muted text-sm">异常</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-lg bg-glass-light border border-surface-border/30">
              <div className="text-text-muted text-sm mb-1">当前任务</div>
              <div className="text-2xl font-bold text-text-primary">{data.workforceStatus.currentTasks}</div>
            </div>
            <div className="p-4 rounded-lg bg-glass-light border border-surface-border/30">
              <div className="text-text-muted text-sm mb-1">今日完成</div>
              <div className="text-2xl font-bold text-text-primary">{data.workforceStatus.completedToday}</div>
            </div>
            <div className="p-4 rounded-lg bg-glass-light border border-surface-border/30">
              <div className="text-text-muted text-sm mb-1">工作效率</div>
              <div className="text-2xl font-bold text-neon-green">{data.workforceStatus.efficiency}%</div>
            </div>
          </div>

          {/* AI员工列表 */}
          {data.workforceStatus.employees.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-lg font-bold text-text-primary mb-3">活跃员工</h3>
              {data.workforceStatus.employees.slice(0, 6).map((employee) => (
                <div
                  key={employee.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-glass-light border border-surface-border/30 hover:border-neon-blue/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${
                      employee.status === 'active' ? 'bg-neon-green' :
                      employee.status === 'created' ? 'bg-neon-yellow' :
                      'bg-neon-red'
                    } animate-pulse`} />
                    <div>
                      <div className="font-medium text-text-primary">{employee.name}</div>
                      <div className="text-sm text-text-muted">{employee.position}</div>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    employee.status === 'active' ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' :
                    employee.status === 'created' ? 'bg-neon-yellow/20 text-neon-yellow border border-neon-yellow/30' :
                    'bg-neon-red/20 text-neon-red border border-neon-red/30'
                  }`}>
                    {employee.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Sales Pipeline + 趋势图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sales Pipeline */}
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-surface-border/50">
            <h2 className="text-2xl font-bold text-text-primary flex items-center">
              <Target className="w-6 h-6 text-neon-purple mr-2" />
              Sales Pipeline
            </h2>
          </div>
          <div className="p-6">
            <FunnelChart
              data={data.pipeline.stages.map(stage => ({
                name: stage.name,
                value: stage.count,
              }))}
              height={350}
            />
            <div className="mt-4 pt-4 border-t border-surface-border/30 grid grid-cols-2 gap-4">
              <div>
                <div className="text-text-muted text-sm mb-1">转化率</div>
                <div className="text-xl font-bold text-neon-green">{data.pipeline.conversionRate.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-text-muted text-sm mb-1">平均成交时间</div>
                <div className="text-xl font-bold text-text-primary">{data.pipeline.avgDealTime}天</div>
              </div>
            </div>
          </div>
        </Card>

        {/* 趋势图 */}
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-surface-border/50">
            <h2 className="text-2xl font-bold text-text-primary flex items-center">
              <TrendingUp className="w-6 h-6 text-neon-blue mr-2" />
              7日趋势
            </h2>
          </div>
          <div className="p-6 space-y-6">
            <div>
              <h3 className="text-sm font-medium text-text-muted mb-3">新增客户</h3>
              <LineChart
                data={{
                  labels: data.trends.labels,
                  values: data.trends.customers,
                }}
                color="#00f0ff"
                height={200}
              />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
