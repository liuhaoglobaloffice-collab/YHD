import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, AlertCircle, Package, Globe, Users, BarChart3, Activity } from 'lucide-react';

const SupplierCommandCenter = () => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatDateTime = (date) => {
    return date.toLocaleString('zh-CN', { 
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  // Mock data
  const todayBrief = [
    { id: 1, title: '新增供应商待审核', count: 8, status: 'urgent', color: 'red' },
    { id: 2, title: '供应商质量已提升', count: 20, status: 'good', color: 'green' },
    { id: 3, title: '供应商资料待完善', count: 5, status: 'warning', color: 'yellow' },
    { id: 4, title: '优质供应商新增', count: 12, status: 'good', color: 'cyan' },
  ];

  const pipelineStages = [
    { name: 'Prospect', count: 20, change: '+8', color: 'cyan' },
    { name: 'Qualified', count: 5, change: '+2', color: 'blue' },
    { name: '待开发', count: 3, change: '+1', color: 'purple' },
    { name: '已联系', count: 0, change: '-', color: 'indigo' },
    { name: '回复', count: 0, change: '-', color: 'blue' },
    { name: '审查提议', count: 0, change: '-', color: 'cyan' },
    { name: '报价', count: 0, change: '-', color: 'purple' },
    { name: '谈判', count: 0, change: '-', color: 'pink' },
    { name: '成交', count: 0, change: '-', color: 'green' },
  ];

  const businessReality = [
    { icon: Package, label: 'Company', value: '待完善', status: 'pending', bgColor: 'cyan' },
    { icon: Package, label: 'Product', value: '已完善', status: 'complete', bgColor: 'green' },
    { icon: AlertCircle, label: 'Supplier', value: '待补充', status: 'warning', bgColor: 'yellow' },
    { icon: Globe, label: 'Market', value: '待完善', status: 'pending', bgColor: 'blue' },
    { icon: Users, label: 'Customer', value: '待激活', status: 'inactive', bgColor: 'purple' },
    { icon: BarChart3, label: 'Pipeline', value: '进程中', status: 'progress', bgColor: 'pink' },
  ];

  const marketFocus = [
    { rank: 1, country: 'China', flag: '🇨🇳', score: 96, label: '优先市场' },
    { rank: 2, country: 'Thailand', flag: '🇹🇭', score: 92, label: '优先市场' },
    { rank: 3, country: 'Vietnam', flag: '🇻🇳', score: 85, label: '' },
    { rank: 4, country: 'Malaysia', flag: '🇲🇾', score: 82, label: '' },
    { rank: 5, country: 'Indonesia', flag: '🇮🇩', score: 80, label: '' },
  ];

  const aiTasks = [
    { title: '智能供应商资质审核系统', status: '高优先级', color: 'red' },
    { title: '美国市场分析与开拓策略', status: '进行中', color: 'cyan' },
    { title: '供应成本计算与报告', status: '待审批', color: 'yellow' },
    { title: '独立站分析与优化建议', status: '运作稳定', color: 'green' },
  ];

  const systemHealth = [
    { name: 'Governance', status: 'normal' },
    { name: 'Audit', status: 'normal' },
    { name: 'Business Reality', status: 'normal' },
    { name: 'Agent Runtime', status: 'normal' },
    { name: 'Provider (离线)', status: 'warning' },
    { name: 'Execution Lock', status: 'locked' },
    { name: 'Browser Guard', status: 'locked' },
    { name: 'API 服务 (离线)', status: 'warning' },
  ];

  const recentActivity = [
    { time: '16:30', event: 'AI 完成供应商市场分析报告', user: '系统AI', type: 'system' },
    { time: '16:25', event: '新增 8 家泰国供应商进入审核', user: '客户开发', type: 'user' },
    { time: '15:40', event: '产品定价算分析完成', user: '产品部', type: 'dept' },
    { time: '14:20', event: '系统安全审计通过', user: '系统', type: 'system' },
    { time: '10:00', event: 'CEO 助手全面功能启动', user: 'CEO', type: 'vip' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0e27] via-[#0f1433] to-[#1a1f4d] text-white font-sans overflow-x-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-30">
        <div className="absolute top-0 left-0 w-96 h-96 bg-cyan-500 rounded-full filter blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-500 rounded-full filter blur-3xl animate-pulse delay-1000"></div>
      </div>

      {/* Grid Pattern */}
      <div className="fixed inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAgTSAwIDIwIEwgNDAgMjAgTSAyMCAwIEwgMjAgNDAgTSAwIDMwIEwgNDAgMzAgTSAzMCAwIEwgMzAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgwLDE5OSwyNTUsMC4xKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-20"></div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-cyan-500/30 bg-black/20 backdrop-blur-sm">
          <div className="container mx-auto px-6 py-4 flex items-center justify-between">
            {/* Logo */}
            <div className="flex items-center space-x-4">
              <div className="relative w-12 h-12">
                <div className="absolute inset-0 bg-cyan-500 rounded-full animate-ping opacity-20"></div>
                <div className="relative w-12 h-12 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-full flex items-center justify-center border-2 border-cyan-400 shadow-lg shadow-cyan-500/50">
                  <span className="text-xl font-bold">鎏</span>
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                  鎏灏 AI
                </h1>
                <p className="text-xs text-cyan-300">LIUHAO AI <span className="text-cyan-500">Global Partner</span></p>
              </div>
            </div>

            {/* Title */}
            <div className="flex-1 text-center">
              <h2 className="text-3xl font-bold tracking-wider bg-gradient-to-r from-cyan-300 via-blue-300 to-purple-300 bg-clip-text text-transparent">
                SUPPLIER COMMAND CENTER
              </h2>
              <p className="text-cyan-400 text-sm mt-1">老板驾驶舱 <span className="text-white/60">Intelligent · Autonomous · Global</span></p>
            </div>

            {/* Right Info */}
            <div className="flex items-center space-x-6">
              <div className="text-right">
                <p className="text-cyan-300 text-sm">{formatDateTime(time)}</p>
                <p className="text-xs text-white/60">26°C 深圳</p>
              </div>
              <div className="flex items-center space-x-2">
                <Activity className="w-5 h-5 text-green-400 animate-pulse" />
                <span className="text-xs text-green-400">在线</span>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center border-2 border-cyan-400">
                <span className="text-sm font-bold">叶</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="container mx-auto px-6 py-6">
          <div className="grid grid-cols-12 gap-6">
            {/* Left Column */}
            <div className="col-span-3 space-y-4">
              {/* Today's Brief */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-cyan-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-cyan-300">今日CEO简报</h3>
                  <span className="text-xs text-cyan-400">Today's Brief</span>
                </div>
                <div className="space-y-3">
                  {todayBrief.map((item) => (
                    <div key={item.id} className="flex items-start space-x-3 group hover:bg-white/5 p-2 rounded transition-all">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        item.color === 'red' ? 'bg-red-500' :
                        item.color === 'green' ? 'bg-green-400' :
                        item.color === 'yellow' ? 'bg-yellow-400' :
                        'bg-cyan-400'
                      } shadow-lg ${
                        item.color === 'red' ? 'shadow-red-500/50' :
                        item.color === 'green' ? 'shadow-green-400/50' :
                        item.color === 'yellow' ? 'shadow-yellow-400/50' :
                        'shadow-cyan-400/50'
                      }`}></div>
                      <div className="flex-1">
                        <p className="text-sm text-white/90">{item.title}</p>
                        <p className="text-xs text-white/60 mt-1">共 {item.count} 个供应商需要处理</p>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        item.status === 'urgent' ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
                        item.status === 'good' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                        'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                      }`}>
                        {item.status === 'urgent' ? '重点关注' :
                         item.status === 'good' ? '进行中' : '中等处理'}
                      </span>
                    </div>
                  ))}
                </div>
                <button className="w-full mt-4 py-2 bg-gradient-to-r from-cyan-600/30 to-blue-600/30 hover:from-cyan-600/50 hover:to-blue-600/50 border border-cyan-500/30 rounded-lg text-cyan-300 text-sm transition-all">
                  查看完整 AI 建议 →
                </button>
              </div>

              {/* AI Tasks */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-purple-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-purple-300">AI 任务中心</h3>
                  <span className="text-xs text-purple-400">Mission & Tasks</span>
                </div>
                <div className="space-y-2">
                  {aiTasks.map((task, index) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded hover:bg-white/5 transition-all group">
                      <div className="flex-1">
                        <p className="text-sm text-white/90">{task.title}</p>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ml-2 ${
                        task.color === 'red' ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
                        task.color === 'cyan' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' :
                        task.color === 'yellow' ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30' :
                        'bg-green-500/20 text-green-300 border border-green-500/30'
                      }`}>
                        {task.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Center Column */}
            <div className="col-span-6 space-y-4">
              {/* AI Assistant */}
              <div className="bg-gradient-to-br from-black/60 to-black/30 backdrop-blur-md rounded-lg border-2 border-cyan-500/50 p-6 relative overflow-hidden">
                {/* Holographic Effect */}
                <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/10 via-transparent to-purple-500/10 pointer-events-none"></div>
                
                <div className="relative">
                  <div className="text-center mb-4">
                    <div className="inline-block relative">
                      {/* Outer Ring */}
                      <div className="absolute inset-0 w-48 h-48 mx-auto">
                        <div className="absolute inset-0 rounded-full border-2 border-cyan-400/30 animate-spin-slow"></div>
                        <div className="absolute inset-2 rounded-full border border-cyan-400/20 animate-spin-slower"></div>
                        <div className="absolute inset-4 rounded-full border border-cyan-400/10"></div>
                      </div>
                      
                      {/* AI Avatar */}
                      <div className="relative w-48 h-48 mx-auto bg-gradient-to-br from-cyan-500/20 to-blue-600/20 rounded-full flex items-center justify-center border-4 border-cyan-400/50 shadow-2xl shadow-cyan-500/50">
                        <div className="text-6xl font-bold bg-gradient-to-br from-cyan-300 to-blue-400 bg-clip-text text-transparent">
                          AI
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="text-center mt-6">
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-cyan-300 to-blue-300 bg-clip-text text-transparent mb-2">
                      JARVIS
                    </h2>
                    <p className="text-cyan-400 text-sm mb-4">Your AI Business Partner</p>
                    
                    <p className="text-xl text-white/90 mb-4">老板，我已准确就绪！</p>
                    <p className="text-lg text-cyan-300 mb-6">今天想可以为您分析什么？</p>

                    {/* Search Input */}
                    <div className="relative">
                      <input
                        type="text"
                        placeholder="请输入您想要分析的..."
                        className="w-full bg-black/40 border-2 border-cyan-500/30 rounded-full px-6 py-3 text-white placeholder-white/40 focus:outline-none focus:border-cyan-400/60 transition-all"
                      />
                      <button className="absolute right-2 top-1/2 -translate-y-1/2 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 p-2 rounded-full transition-all">
                        <Search className="w-5 h-5" />
                      </button>
                    </div>

                    {/* Quick Actions */}
                    <div className="flex justify-center gap-2 mt-4 flex-wrap">
                      {['市场分析', '项目追踪', '产品策略', 'SEO 优化', '智能报告'].map((action) => (
                        <button key={action} className="px-4 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 rounded-full text-cyan-300 text-sm transition-all">
                          {action}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Pipeline */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-cyan-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-cyan-300">销售 Pipeline</h3>
                  <span className="text-xs text-cyan-400">5 个机会进行中</span>
                </div>
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {pipelineStages.map((stage, index) => (
                    <div key={index} className="flex-shrink-0 text-center min-w-[100px]">
                      <div className={`bg-gradient-to-br ${
                        stage.color === 'cyan' ? 'from-cyan-600/20 to-cyan-600/10 border-cyan-500/30' :
                        stage.color === 'blue' ? 'from-blue-600/20 to-blue-600/10 border-blue-500/30' :
                        stage.color === 'purple' ? 'from-purple-600/20 to-purple-600/10 border-purple-500/30' :
                        stage.color === 'indigo' ? 'from-indigo-600/20 to-indigo-600/10 border-indigo-500/30' :
                        stage.color === 'pink' ? 'from-pink-600/20 to-pink-600/10 border-pink-500/30' :
                        'from-green-600/20 to-green-600/10 border-green-500/30'
                      } border rounded-lg p-3 hover:scale-105 transition-all`}>
                        <p className="text-xs text-white/70 mb-2">{stage.name}</p>
                        <p className="text-2xl font-bold text-white">{stage.count}</p>
                        {stage.change !== '-' && (
                          <p className="text-xs text-green-400 mt-1 flex items-center justify-center">
                            <TrendingUp className="w-3 h-3 mr-1" />
                            {stage.change}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Business Reality */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-cyan-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-cyan-300">业务数据中心</h3>
                  <span className="text-xs text-cyan-400">Business Reality</span>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {businessReality.map((item, index) => {
                    const Icon = item.icon;
                    return (
                      <div key={index} className={`bg-gradient-to-br ${
                        item.bgColor === 'cyan' ? 'from-cyan-600/10 to-black/20 border-cyan-500/30' :
                        item.bgColor === 'green' ? 'from-green-600/10 to-black/20 border-green-500/30' :
                        item.bgColor === 'yellow' ? 'from-yellow-600/10 to-black/20 border-yellow-500/30' :
                        item.bgColor === 'blue' ? 'from-blue-600/10 to-black/20 border-blue-500/30' :
                        item.bgColor === 'purple' ? 'from-purple-600/10 to-black/20 border-purple-500/30' :
                        'from-pink-600/10 to-black/20 border-pink-500/30'
                      } border rounded-lg p-4 hover:scale-105 transition-all group`}>
                        <Icon className={`w-8 h-8 mb-2 ${
                          item.bgColor === 'cyan' ? 'text-cyan-400' :
                          item.bgColor === 'green' ? 'text-green-400' :
                          item.bgColor === 'yellow' ? 'text-yellow-400' :
                          item.bgColor === 'blue' ? 'text-blue-400' :
                          item.bgColor === 'purple' ? 'text-purple-400' :
                          'text-pink-400'
                        }`} />
                        <p className="text-xs text-white/60 mb-1">{item.label}</p>
                        <p className={`text-sm font-bold ${
                          item.status === 'complete' ? 'text-green-400' :
                          item.status === 'warning' ? 'text-yellow-400' :
                          item.status === 'inactive' ? 'text-purple-400' :
                          item.status === 'progress' ? 'text-pink-400' :
                          'text-cyan-400'
                        }`}>{item.value}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Market Focus */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-cyan-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-cyan-300">全球市场聚焦</h3>
                  <span className="text-xs text-cyan-400">Market Focus</span>
                </div>
                <div className="space-y-2">
                  {marketFocus.map((market) => (
                    <div key={market.rank} className="flex items-center justify-between p-2 rounded hover:bg-white/5 transition-all">
                      <div className="flex items-center space-x-3">
                        <span className="text-cyan-400 font-mono">{market.rank}</span>
                        <span className="text-2xl">{market.flag}</span>
                        <span className="text-white/90">{market.country}</span>
                        {market.label && (
                          <span className="text-xs px-2 py-1 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded-full">
                            {market.label}
                          </span>
                        )}
                      </div>
                      <span className="text-cyan-400 font-mono">{market.score}</span>
                    </div>
                  ))}
                </div>
                <button className="w-full mt-4 py-2 bg-gradient-to-r from-cyan-600/30 to-blue-600/30 hover:from-cyan-600/50 hover:to-blue-600/50 border border-cyan-500/30 rounded-lg text-cyan-300 text-sm transition-all">
                  查看市场分析 →
                </button>
              </div>
            </div>

            {/* Right Column */}
            <div className="col-span-3 space-y-4">
              {/* Key Metrics */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-cyan-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-cyan-300">核心业务数据</h3>
                  <span className="text-xs text-cyan-400">Key Metrics</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3">
                    <p className="text-xs text-white/60 mb-1">客户池</p>
                    <p className="text-2xl font-bold text-cyan-300">20</p>
                    <div className="flex items-center text-xs text-green-400 mt-1">
                      <TrendingUp className="w-3 h-3 mr-1" />
                      +8
                    </div>
                  </div>
                  <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                    <p className="text-xs text-white/60 mb-1">销售机会</p>
                    <p className="text-2xl font-bold text-green-300">5</p>
                    <div className="flex items-center text-xs text-green-400 mt-1">
                      <TrendingUp className="w-3 h-3 mr-1" />
                      +2
                    </div>
                  </div>
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                    <p className="text-xs text-white/60 mb-1">待审批</p>
                    <p className="text-2xl font-bold text-red-300">2</p>
                    <div className="flex items-center text-xs text-red-400 mt-1">
                      <AlertCircle className="w-3 h-3 mr-1" />
                      ↓0
                    </div>
                  </div>
                  <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3">
                    <p className="text-xs text-white/60 mb-1">任务完成率</p>
                    <p className="text-2xl font-bold text-purple-300">85%</p>
                    <div className="flex items-center text-xs text-green-400 mt-1">
                      <TrendingUp className="w-3 h-3 mr-1" />
                      +12%
                    </div>
                  </div>
                </div>
              </div>

              {/* System Health */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-green-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-green-300">系统状态</h3>
                  <span className="text-xs px-2 py-1 bg-green-500/20 text-green-300 border border-green-500/30 rounded-full">
                    全部正常
                  </span>
                </div>
                <div className="space-y-2">
                  {systemHealth.map((system, index) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded hover:bg-white/5 transition-all">
                      <div className="flex items-center space-x-2">
                        <div className={`w-2 h-2 rounded-full ${
                          system.status === 'normal' ? 'bg-green-400 shadow-lg shadow-green-400/50' :
                          system.status === 'warning' ? 'bg-yellow-400 shadow-lg shadow-yellow-400/50' :
                          'bg-gray-400'
                        }`}></div>
                        <span className="text-sm text-white/90">{system.name}</span>
                      </div>
                      <span className={`text-xs ${
                        system.status === 'normal' ? 'text-green-400' :
                        system.status === 'warning' ? 'text-yellow-400' :
                        'text-gray-400'
                      }`}>
                        {system.status === 'normal' ? '正常' :
                         system.status === 'warning' ? '警告' : '已锁定'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Activity */}
              <div className="bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md rounded-lg border border-cyan-500/30 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-cyan-300">最近动态</h3>
                  <span className="text-xs text-cyan-400">查看更多 →</span>
                </div>
                <div className="space-y-3">
                  {recentActivity.map((activity, index) => (
                    <div key={index} className="flex items-start space-x-3 group hover:bg-white/5 p-2 rounded transition-all">
                      <span className="text-xs text-cyan-400 font-mono mt-1">{activity.time}</span>
                      <div className="flex-1">
                        <p className="text-sm text-white/90">{activity.event}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${
                          activity.type === 'system' ? 'bg-blue-500/20 text-blue-300' :
                          activity.type === 'user' ? 'bg-cyan-500/20 text-cyan-300' :
                          activity.type === 'dept' ? 'bg-purple-500/20 text-purple-300' :
                          'bg-yellow-500/20 text-yellow-300'
                        }`}>
                          {activity.user}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Achievement */}
              <div className="bg-gradient-to-br from-yellow-600/20 to-orange-600/20 backdrop-blur-md rounded-lg border-2 border-yellow-500/50 p-4 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-yellow-400/10 rounded-full filter blur-2xl"></div>
                <div className="relative flex items-center space-x-4">
                  <div className="text-5xl">🏆</div>
                  <div className="flex-1">
                    <p className="text-yellow-300 font-bold">我们的目标</p>
                    <p className="text-white/90 text-sm mt-1">Build a Global Brand · Achieve 100M</p>
                  </div>
                  <button className="text-yellow-300 hover:text-yellow-200 transition-all">
                    →
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-black/40 backdrop-blur-md border-t border-cyan-500/30 py-2 px-6">
        <div className="container mx-auto flex items-center justify-between text-xs">
          <div className="flex items-center space-x-4">
            <span className="text-cyan-400">© 2025 LIUHAO AI Team</span>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-green-400">安全运行模式</span>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-white/60">Execution Lock</span>
            <span className="text-white/60">Browser Guard</span>
            <span className="text-yellow-400">External Action PENDING APPROVAL</span>
          </div>
        </div>
      </div>

      {/* Custom Animations */}
      <style jsx>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes spin-slower {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 10s linear infinite;
        }
        .animate-spin-slower {
          animation: spin-slower 15s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default SupplierCommandCenter;
