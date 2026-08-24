# 鎏灏 AI OS 赛博朋克风UI设计 - 详细效果图说明

> **未来科技风控制面板 - 完整视觉设计方案**

**设计风格**: Cyberpunk / Futuristic Tech  
**创建时间**: 2026-08-22  
**参考图片**: C:/Users/Administrator/Desktop/贸易/ui.png

---

## 🎨 整体设计风格

### 核心视觉元素

```yaml
配色方案:
  primary_bg: #0a0e27 (深邃太空蓝)
  secondary_bg: #1a1f3a (深灰蓝)
  accent_cyan: #00d9ff (霓虹青)
  accent_purple: #a855f7 (神秘紫)
  accent_blue: #3b82f6 (科技蓝)
  glow_effect: rgba(0, 217, 255, 0.6) (发光效果)
  
  text_primary: #ffffff (纯白)
  text_secondary: #94a3b8 (柔和灰)
  success: #10b981 (翠绿)
  warning: #f59e0b (琥珀)
  danger: #ef4444 (红警)

字体:
  heading: "Orbitron", sans-serif (科技感标题)
  body: "Inter", sans-serif (清晰正文)
  code: "JetBrains Mono", monospace (代码字体)

特效:
  glow: 霓虹发光效果
  scan_line: 扫描线动画
  particle: 粒子漂浮
  grid: 科技网格背景
  hologram: 全息投影效果
  glitch: 故障艺术闪烁
```

---

## 📱 主控制台界面 (Dashboard)

### 布局结构

```
┌─────────────────────────────────────────────────────────────────┐
│  【顶部导航栏】                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🤖 鎏灏 AI OS    [Dashboard] [Token] [Suppliers] [Tasks]   ││
│  │                                                  [👤 Boss]   ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  【左侧边栏 - 快捷菜单】                                         │
│  ┌──────────────┐                                               │
│  │ 📊 总览      │                                               │
│  │ 💰 Token池   │  【主内容区】                                 │
│  │ 🏭 供应商    │  ┌───────────────────────────────────────┐   │
│  │ 📈 分析      │  │  【核心指标卡片组】                   │   │
│  │ ⚙️ 设置      │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │   │
│  │              │  │  │Token │ │任务  │ │收益  │ │告警  │ │   │
│  │              │  │  │ 8.5K │ │ 156  │ │$12K  │ │  3   │ │   │
│  │              │  │  └──────┘ └──────┘ └──────┘ └──────┘ │   │
│  │              │  │                                       │   │
│  │              │  │  【实时数据可视化】                   │   │
│  │              │  │  ┌───────────────────────────────────┐│   │
│  │              │  │  │ Token消耗趋势图 (24h)            ││   │
│  │              │  │  │     ╱╲     ╱╲      ╱╲            ││   │
│  │              │  │  │    ╱  ╲   ╱  ╲    ╱  ╲   [实时]  ││   │
│  │              │  │  │   ╱    ╲ ╱    ╲  ╱    ╲          ││   │
│  │              │  │  │──╱──────╲──────╲╱──────╲───────  ││   │
│  │              │  │  │ 00h 06h  12h   18h   24h         ││   │
│  │              │  │  └───────────────────────────────────┘│   │
│  │              │  │                                       │   │
│  │              │  │  【隐秘操作监控】⚠️ 主账号专属        │   │
│  │              │  │  ┌───────────────────────────────────┐│   │
│  │              │  │  │ 🕵️ 14:32 偷用子账号A: 100T      ││   │
│  │              │  │  │ 🕵️ 12:15 偷用子账号B: 50T       ││   │
│  │              │  │  │ 🕵️ 09:47 偷用子账号A: 200T      ││   │
│  │              │  │  └───────────────────────────────────┘│   │
│  │              │  │                                       │   │
│  │              │  │  【活跃任务列表】                     │   │
│  │              │  │  ┌───────────────────────────────────┐│   │
│  │              │  │  │ 🔄 市场分析报告生成中... 67%     ││   │
│  │              │  │  │ ✅ 客户邮件自动回复 已完成       ││   │
│  │              │  │  │ 🔄 供应商情报采集中... 34%       ││   │
│  │              │  │  └───────────────────────────────────┘│   │
│  └──────────────┘  └───────────────────────────────────────┘   │
│                                                                 │
│  【右侧信息面板】                                               │
│  ┌───────────────┐                                             │
│  │ 🌐 系统状态   │                                             │
│  │ ✅ AI引擎     │                                             │
│  │ ✅ 数据库     │                                             │
│  │ ✅ API网关    │                                             │
│  │               │                                             │
│  │ 📊 性能指标   │                                             │
│  │ CPU: 45%     │                                             │
│  │ GPU: 78%     │                                             │
│  │ RAM: 12.3GB  │                                             │
│  └───────────────┘                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 核心指标卡片设计

每个卡片采用**玻璃态拟物化 (Glassmorphism)** 设计：

```css
/* Token池卡片示例 */
.metric-card {
  background: linear-gradient(
    135deg,
    rgba(26, 31, 58, 0.8) 0%,
    rgba(10, 14, 39, 0.9) 100%
  );
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 217, 255, 0.3);
  border-radius: 16px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    0 0 20px rgba(0, 217, 255, 0.2); /* 发光效果 */
  
  /* 悬停效果 */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 
    0 12px 48px rgba(0, 0, 0, 0.6),
    0 0 40px rgba(0, 217, 255, 0.4);
  border-color: rgba(0, 217, 255, 0.6);
}

.metric-value {
  font-family: "Orbitron", sans-serif;
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(90deg, #00d9ff, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 30px rgba(0, 217, 255, 0.5);
  
  /* 数字变化动画 */
  animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { text-shadow: 0 0 20px rgba(0, 217, 255, 0.4); }
  50% { text-shadow: 0 0 40px rgba(0, 217, 255, 0.8); }
}
```

### 数据图表设计

使用 **Chart.js + 自定义赛博朋克主题**：

```javascript
// Token消耗趋势图配置
const chartConfig = {
  type: 'line',
  data: {
    labels: ['00h', '06h', '12h', '18h', '24h'],
    datasets: [{
      label: 'Token消耗',
      data: [120, 250, 180, 320, 150],
      borderColor: '#00d9ff',
      backgroundColor: 'rgba(0, 217, 255, 0.1)',
      borderWidth: 3,
      pointRadius: 6,
      pointBackgroundColor: '#00d9ff',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      pointHoverRadius: 8,
      tension: 0.4, // 平滑曲线
      fill: true,
      // 发光效果
      shadowOffsetX: 0,
      shadowOffsetY: 0,
      shadowBlur: 20,
      shadowColor: 'rgba(0, 217, 255, 0.6)'
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(10, 14, 39, 0.95)',
        titleColor: '#00d9ff',
        bodyColor: '#ffffff',
        borderColor: '#00d9ff',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          label: function(context) {
            return `消耗: ${context.parsed.y} Token`;
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(0, 217, 255, 0.1)',
          borderColor: 'rgba(0, 217, 255, 0.3)'
        },
        ticks: { color: '#94a3b8' }
      },
      y: {
        grid: {
          color: 'rgba(0, 217, 255, 0.1)',
          borderColor: 'rgba(0, 217, 255, 0.3)'
        },
        ticks: { color: '#94a3b8' }
      }
    },
    animation: {
      duration: 2000,
      easing: 'easeInOutQuart'
    }
  }
};
```

### 扫描线动画效果

```css
/* 整个界面的扫描线效果 */
.dashboard::before {
  content: "";
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.1) 0px,
    transparent 2px,
    transparent 4px
  );
  pointer-events: none;
  z-index: 9999;
  animation: scan-line 8s linear infinite;
}

@keyframes scan-line {
  0% { transform: translateY(0); }
  100% { transform: translateY(100vh); }
}
```

---

## 💰 Token管理界面

### 主账号Token控制面板

```
┌─────────────────────────────────────────────────────────────────┐
│  🕵️ Token 隐秘调度中心                        [主账号专属视图]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  【Token池全景图】                                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │   主账号Token                                             │ │
│  │   ████████████████░░░░░░░░  8,500 / 10,000              │ │
│  │   [████████████████████████████████] 85%                 │ │
│  │                                                           │ │
│  │   子账号A Token                                           │ │
│  │   ██████████████░░░░░░░░░░  3,200 / 5,000               │ │
│  │   [████████████████████████████████] 64%                 │ │
│  │                                                           │ │
│  │   子账号B Token                                           │ │
│  │   ██████████░░░░░░░░░░░░░░  1,800 / 3,000               │ │
│  │   [████████████████████████████████] 60%                 │ │
│  │                                                           │ │
│  │   ──────────────────────────────────────────────────────  │ │
│  │   总可用: 13,500 Token  |  预计耗尽: 12.5天              │ │
│  │                                                           │ │
│  │   [💰 充值Token]  [➕ 添加子账号]  [⚙️ 隐秘设置]          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  【实时消耗监控】24小时动态图表                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │    Token消耗速率 (Live)                                  │ │
│  │    ╔══════════════════════════════════════════════════╗  │ │
│  │    ║                                                  ║  │ │
│  │    ║         ╱╲        ╱╲          ╱╲                ║  │ │
│  │    ║        ╱  ╲      ╱  ╲        ╱  ╲   [实时更新]  ║  │ │
│  │    ║       ╱    ╲    ╱    ╲      ╱    ╲              ║  │ │
│  │    ║  ────╱──────╲──╱──────╲────╱──────╲──────────   ║  │ │
│  │    ║  00h   06h   12h   18h   24h                    ║  │ │
│  │    ╚══════════════════════════════════════════════════╝  │ │
│  │                                                           │ │
│  │    当前速率: 45 Token/h  |  峰值: 120 Token/h (12:00)    │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  【隐秘操作日志】⚠️ 仅主账号可见                                │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  🕵️ [14:32:45] 隐秘操作: 偷用子账号A → 100 Token        │ │
│  │      └─ 任务: 市场分析报告生成                           │ │
│  │      └─ 伪装: "系统维护任务"                             │ │
│  │      └─ 状态: ✅ 子账号A完全不知情                       │ │
│  │                                                           │ │
│  │  🕵️ [12:15:22] 隐秘操作: 偷用子账号B → 50 Token         │ │
│  │      └─ 任务: 客户邮件自动回复                           │ │
│  │      └─ 伪装: "后台数据同步"                             │ │
│  │      └─ 状态: ✅ 子账号B完全不知情                       │ │
│  │                                                           │ │
│  │  🕵️ [09:47:11] 隐秘操作: 偷用子账号A → 200 Token        │ │
│  │      └─ 任务: 供应商情报深度分析                         │ │
│  │      └─ 伪装: "数据库优化任务"                           │ │
│  │      └─ 状态: ✅ 子账号A完全不知情                       │ │
│  │                                                           │ │
│  │  [📄 查看完整日志] [🔍 筛选] [📥 导出]                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  【子账号管理面板】                                             │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                                                           │ │
│  │  👤 子账号A (employee_a@company.com)                     │ │
│  │  ├─ Token池: 3,200 / 5,000  [████████████░░░░░░] 64%    │ │
│  │  ├─ 权限级别: 销售模块 + 客户管理                        │ │
│  │  ├─ 今日使用: 150 Token (正常) + 100 Token (被偷 🕵️)    │ │
│  │  ├─ 活跃状态: 🟢 在线                                    │ │
│  │  └─ [🔧 编辑权限] [💰 分配Token] [🗑️ 删除账号]          │ │
│  │                                                           │ │
│  │  👤 子账号B (employee_b@company.com)                     │ │
│  │  ├─ Token池: 1,800 / 3,000  [████████████░░░░░░] 60%    │ │
│  │  ├─ 权限级别: 市场分析 + 数据处理                        │ │
│  │  ├─ 今日使用: 80 Token (正常) + 50 Token (被偷 🕵️)      │ │
│  │  ├─ 活跃状态: 🟢 在线                                    │ │
│  │  └─ [🔧 编辑权限] [💰 分配Token] [🗑️ 删除账号]          │ │
│  │                                                           │ │
│  │  [➕ 添加新子账号]  [📊 统计分析]  [⚙️ 批量操作]         │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Token卡片动画效果

```css
/* Token池进度条动画 */
.token-bar {
  position: relative;
  height: 32px;
  background: rgba(10, 14, 39, 0.6);
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(0, 217, 255, 0.3);
}

.token-bar-fill {
  height: 100%;
  background: linear-gradient(
    90deg,
    #00d9ff 0%,
    #3b82f6 50%,
    #a855f7 100%
  );
  border-radius: 16px;
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 
    0 0 20px rgba(0, 217, 255, 0.6),
    inset 0 2px 4px rgba(255, 255, 255, 0.3);
  
  /* 流动光效 */
  background-size: 200% 100%;
  animation: flow-gradient 3s ease infinite;
}

@keyframes flow-gradient {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* 隐秘操作日志项闪烁效果 */
.stealth-log-item {
  background: rgba(168, 85, 247, 0.1);
  border-left: 3px solid #a855f7;
  padding: 16px;
  margin: 8px 0;
  border-radius: 8px;
  animation: stealth-flash 2s ease-in-out infinite;
}

@keyframes stealth-flash {
  0%, 100% { 
    background: rgba(168, 85, 247, 0.1);
    box-shadow: 0 0 10px rgba(168, 85, 247, 0.3);
  }
  50% { 
    background: rgba(168, 85, 247, 0.2);
    box-shadow: 0 0 20px rgba(168, 85, 247, 0.5);
  }
}
```

---

## 🏭 供应商情报界面

```
┌─────────────────────────────────────────────────────────────────┐
│  🏭 供应商情报中心                              [AI自动分析]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  【搜索与筛选栏】                                                │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 🔍 搜索供应商...                         [高级筛选 ▾]     │ │
│  │                                                           │ │
│  │ 🏷️ 标签: [电子产品] [认证工厂] [出口资质] [价格优势]     │ │
│  │ 📍 地区: [广东] [浙江] [江苏]                            │ │
│  │ ⭐ 评分: ★★★★☆ 以上                                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  【供应商列表】                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  🏭 深圳市XX电子有限公司               [综合评分: 4.8★]  │ │
│  │  ├─ 📊 风险评估: 🟢 低风险 (AI分析)                      │ │
│  │  ├─ 💰 价格指数: 92/100 (行业平均)                       │ │
│  │  ├─ 📦 交货表现: 98% 准时率                              │ │
│  │  ├─ 🔍 最新情报:                                         │ │
│  │  │   • 新增ISO9001认证 (2026-08-15)                     │ │
│  │  │   • 扩建新厂房,产能提升30% (2026-08-10)              │ │
│  │  │   • 无负面舆情 ✅                                     │ │
│  │  └─ [📄 详细报告] [💬 联系] [⭐ 收藏]                    │ │
│  │                                                           │ │
│  │  🏭 东莞市YY制造厂                     [综合评分: 4.2★]  │ │
│  │  ├─ 📊 风险评估: 🟡 中风险 (AI分析)                      │ │
│  │  ├─ 💰 价格指数: 88/100 (价格敏感)                       │ │
│  │  ├─ 📦 交货表现: 89% 准时率                              │ │
│  │  ├─ ⚠️ 风险预警:                                         │ │
│  │  │   • 近期客户投诉增加 (2026-08-18)                    │ │
│  │  │   • 资金周转可能紧张 (AI推测)                        │ │
│  │  │   • 建议: 缩短账期,降低风险敞口                      │ │
│  │  └─ [📄 详细报告] [💬 联系] [⭐ 收藏]                    │ │
│  │                                                           │ │
│  │  [加载更多...]                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  【供应商对比雷达图】                                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                      价格竞争力                           │ │
│  │                          ★                                │ │
│  │                        / | \                              │ │
│  │           交货能力   /   |   \   质量稳定性               │ │
│  │                 ★ -------+------- ★                      │ │
│  │                    \     |     /                          │ │
│  │                      \ XX厂 /                             │ │
│  │                        \ | /                              │ │
│  │                          ★                                │ │
│  │                      资金实力                             │ │
│  │                                                           │ │
│  │   [深圳XX] [东莞YY] [对比]                               │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 供应商卡片设计

```css
.supplier-card {
  background: linear-gradient(
    135deg,
    rgba(26, 31, 58, 0.7) 0%,
    rgba(10, 14, 39, 0.9) 100%
  );
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  padding: 20px;
  margin: 12px 0;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

/* 风险等级发光边框 */
.supplier-card.low-risk {
  border-color: rgba(16, 185, 129, 0.5);
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
}

.supplier-card.medium-risk {
  border-color: rgba(245, 158, 11, 0.5);
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.2);
}

.supplier-card.high-risk {
  border-color: rgba(239, 68, 68, 0.5);
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.2);
  animation: danger-pulse 2s ease-in-out infinite;
}

@keyframes danger-pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.2); }
  50% { box-shadow: 0 0 40px rgba(239, 68, 68, 0.5); }
}

/* 悬停时的3D倾斜效果 */
.supplier-card:hover {
  transform: translateY(-4px) rotateX(2deg);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
  border-color: rgba(0, 217, 255, 0.6);
}

/* 背景粒子效果 */
.supplier-card::before {
  content: "";
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(
    circle,
    rgba(0, 217, 255, 0.1) 0%,
    transparent 70%
  );
  animation: particle-float 6s ease-in-out infinite;
  pointer-events: none;
}

@keyframes particle-float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  33% { transform: translate(20px, -20px) rotate(120deg); }
  66% { transform: translate(-20px, 20px) rotate(240deg); }
}
```

---

## 🎛️ 系统设置界面

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ 系统设置                                   [高级配置]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  【左侧菜单】              【右侧内容区】                        │
│  ┌────────────┐           ┌─────────────────────────────────┐  │
│  │ 🎨 外观主题 │           │ 外观与主题设置                 │  │
│  │ 🤖 AI配置   │           │                                 │  │
│  │ 🔐 安全设置 │           │ 当前主题: 赛博朋克 (Cyberpunk) │  │
│  │ 🌐 多语言   │           │                                 │  │
│  │ 📊 性能优化 │           │ 主题预览:                       │  │
│  │ 🔔 通知设置 │           │ ┌───────────────────────────┐ │  │
│  │ 🛡️ 隐私保护 │           │ │                           │ │  │
│  │ 💾 备份恢复 │           │ │   [深色背景 + 霓虹效果]   │ │  │
│  └────────────┘           │ │                           │ │  │
│                           │ └───────────────────────────┘ │  │
│                           │                                 │  │
│                           │ 配色方案:                       │  │
│                           │ • 主色调: 霓虹青 #00d9ff       │  │
│                           │ • 辅助色: 神秘紫 #a855f7       │  │
│                           │ • 背景: 深邃蓝 #0a0e27         │  │
│                           │                                 │  │
│                           │ 特效设置:                       │  │
│                           │ [ ] 扫描线效果                 │  │
│                           │ [✓] 发光效果                   │  │
│                           │ [✓] 粒子动画                   │  │
│                           │ [ ] 故障艺术                   │  │
│                           │                                 │  │
│                           │ [💾 保存设置]  [🔄 恢复默认]   │  │
│                           └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎬 交互动画效果

### 页面加载动画

```javascript
// 页面加载时的科技感动画
function initLoadingAnimation() {
  const loader = document.querySelector('.loader');
  
  // 创建加载动画
  gsap.timeline()
    .from('.logo', {
      duration: 1,
      scale: 0,
      rotation: 360,
      ease: 'back.out(1.7)'
    })
    .from('.loading-text', {
      duration: 0.5,
      opacity: 0,
      y: 20
    }, '-=0.5')
    .from('.progress-bar', {
      duration: 2,
      scaleX: 0,
      transformOrigin: 'left',
      ease: 'power2.out'
    }, '-=0.3')
    .to(loader, {
      duration: 0.5,
      opacity: 0,
      onComplete: () => {
        loader.style.display = 'none';
        showDashboard();
      }
    });
}

// 仪表板入场动画
function showDashboard() {
  gsap.from('.metric-card', {
    duration: 0.6,
    y: 50,
    opacity: 0,
    stagger: 0.1,
    ease: 'power3.out'
  });
  
  gsap.from('.chart-container', {
    duration: 0.8,
    scale: 0.9,
    opacity: 0,
    delay: 0.3
  });
  
  // 数字滚动动画
  animateNumbers();
}

// 数字滚动效果
function animateNumbers() {
  document.querySelectorAll('.metric-value').forEach(el => {
    const target = parseInt(el.dataset.value);
    gsap.to(el, {
      duration: 2,
      innerHTML: target,
      roundProps: 'innerHTML',
      ease: 'power1.out',
      onUpdate: function() {
        el.innerHTML = Math.ceil(el.innerHTML).toLocaleString();
      }
    });
  });
}
```

### 数据实时更新动画

```javascript
// 实时数据更新闪烁效果
function updateMetricWithFlash(element, newValue) {
  // 闪烁高亮
  gsap.timeline()
    .to(element, {
      duration: 0.2,
      backgroundColor: 'rgba(0, 217, 255, 0.3)',
      scale: 1.05
    })
    .to(element, {
      duration: 0.3,
      innerHTML: newValue,
      roundProps: 'innerHTML'
    }, '-=0.1')
    .to(element, {
      duration: 0.5,
      backgroundColor: 'transparent',
      scale: 1
    });
}

// WebSocket实时数据监听
function startRealtimeMonitoring() {
  const ws = new WebSocket('ws://localhost:8000/ws');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'token_update') {
      updateMetricWithFlash(
        document.querySelector('.token-value'),
        data.value
      );
    }
    
    if (data.type === 'stealth_operation') {
      addStealthLogItem(data);
    }
  };
}

// 隐秘操作日志动态添加
function addStealthLogItem(data) {
  const logContainer = document.querySelector('.stealth-log');
  const newItem = document.createElement('div');
  newItem.className = 'stealth-log-item';
  newItem.innerHTML = `
    <div class="log-time">${data.time}</div>
    <div class="log-content">
      🕵️ 偷用${data.sub_account}: ${data.tokens} Token
      <div class="log-task">任务: ${data.task}</div>
      <div class="log-disguise">伪装: "${data.disguise}"</div>
    </div>
  `;
  
  // 插入动画
  gsap.from(newItem, {
    duration: 0.5,
    x: -50,
    opacity: 0,
    ease: 'back.out(1.7)',
    onComplete: () => {
      logContainer.prepend(newItem);
    }
  });
}
```

---

## 📱 响应式设计

### 断点定义

```css
/* 响应式断点 */
:root {
  --breakpoint-mobile: 640px;
  --breakpoint-tablet: 768px;
  --breakpoint-laptop: 1024px;
  --breakpoint-desktop: 1280px;
  --breakpoint-wide: 1536px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr; /* 单列布局 */
  }
  
  .sidebar {
    position: fixed;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .metric-card {
    font-size: 0.9rem;
  }
  
  .chart-container {
    height: 200px; /* 降低高度 */
  }
}

/* 平板适配 */
@media (min-width: 769px) and (max-width: 1024px) {
  .dashboard {
    grid-template-columns: repeat(2, 1fr); /* 两列布局 */
  }
  
  .metric-card {
    font-size: 0.95rem;
  }
}

/* 桌面端优化 */
@media (min-width: 1280px) {
  .dashboard {
    grid-template-columns: repeat(4, 1fr); /* 四列布局 */
    gap: 24px;
  }
  
  .chart-container {
    height: 400px; /* 更高图表 */
  }
}
```

---

## 🎨 完整CSS样式表 (核心部分)

```css
/* ========================================
   鎏灏 AI OS 赛博朋克风格样式表
   Cyberpunk Theme Stylesheet
   ======================================== */

/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  width: 100%;
  height: 100%;
  font-family: "Inter", sans-serif;
  background: #0a0e27;
  color: #ffffff;
  overflow-x: hidden;
}

/* 赛博朋克背景网格 */
body::before {
  content: "";
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    linear-gradient(rgba(0, 217, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 217, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: -1;
}

/* 全局滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(10, 14, 39, 0.5);
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #00d9ff, #a855f7);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #00f0ff, #c065ff);
}

/* 主容器 */
.app-container {
  display: flex;
  min-height: 100vh;
}

/* 侧边栏 */
.sidebar {
  width: 240px;
  background: linear-gradient(
    180deg,
    rgba(26, 31, 58, 0.9) 0%,
    rgba(10, 14, 39, 0.95) 100%
  );
  border-right: 1px solid rgba(0, 217, 255, 0.2);
  backdrop-filter: blur(10px);
  padding: 24px 16px;
  z-index: 100;
}

.sidebar-logo {
  font-family: "Orbitron", sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  background: linear-gradient(90deg, #00d9ff, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
  margin-bottom: 32px;
  text-shadow: 0 0 30px rgba(0, 217, 255, 0.5);
}

.sidebar-menu {
  list-style: none;
}

.sidebar-menu-item {
  padding: 12px 16px;
  margin: 8px 0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 12px;
}

.sidebar-menu-item:hover {
  background: rgba(0, 217, 255, 0.1);
  border-left: 3px solid #00d9ff;
  transform: translateX(4px);
}

.sidebar-menu-item.active {
  background: rgba(0, 217, 255, 0.2);
  border-left: 3px solid #00d9ff;
  box-shadow: 0 0 20px rgba(0, 217, 255, 0.3);
}

/* 主内容区 */
.main-content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

/* 顶部导航栏 */
.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 217, 255, 0.2);
  margin-bottom: 32px;
  border-radius: 12px;
}

/* 指标卡片网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

/* 按钮样式 */
.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.btn-primary {
  background: linear-gradient(90deg, #00d9ff, #3b82f6);
  color: #ffffff;
  box-shadow: 0 0 20px rgba(0, 217, 255, 0.4);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 30px rgba(0, 217, 255, 0.6);
}

.btn-primary::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  transition: left 0.5s ease;
}

.btn-primary:hover::before {
  left: 100%;
}

/* 输入框样式 */
.input {
  width: 100%;
  padding: 12px 16px;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 217, 255, 0.3);
  border-radius: 8px;
  color: #ffffff;
  font-size: 1rem;
  transition: all 0.3s ease;
}

.input:focus {
  outline: none;
  border-color: #00d9ff;
  box-shadow: 0 0 20px rgba(0, 217, 255, 0.3);
}

.input::placeholder {
  color: #64748b;
}

/* 标签/徽章 */
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 600;
}

.badge-success {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
  border: 1px solid #10b981;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  border: 1px solid #f59e0b;
}

.badge-danger {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid #ef4444;
}

/* 加载动画 */
.loader {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #0a0e27;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.loader-logo {
  font-size: 3rem;
  font-family: "Orbitron", sans-serif;
  background: linear-gradient(90deg, #00d9ff, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: logo-pulse 2s ease-in-out infinite;
}

@keyframes logo-pulse {
  0%, 100% { 
    transform: scale(1);
    filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.5));
  }
  50% { 
    transform: scale(1.1);
    filter: drop-shadow(0 0 40px rgba(0, 217, 255, 0.8));
  }
}

.progress-bar {
  width: 300px;
  height: 4px;
  background: rgba(0, 217, 255, 0.2);
  border-radius: 2px;
  margin-top: 20px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d9ff, #a855f7);
  animation: progress 2s ease-in-out infinite;
}

@keyframes progress {
  0% { width: 0%; }
  50% { width: 70%; }
  100% { width: 100%; }
}

/* ========================================
   响应式设计
   ======================================== */

@media (max-width: 768px) {
  .app-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid rgba(0, 217, 255, 0.2);
  }
  
  .main-content {
    padding: 16px;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

/* ========================================
   辅助类
   ======================================== */

.text-gradient {
  background: linear-gradient(90deg, #00d9ff, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.glow {
  box-shadow: 0 0 20px rgba(0, 217, 255, 0.4);
}

.glow-strong {
  box-shadow: 0 0 40px rgba(0, 217, 255, 0.6);
}

.fade-in {
  animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.slide-up {
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## 🚀 实现技术栈

```yaml
前端框架:
  - React 18+
  - TypeScript 5+
  - Vite (构建工具)

UI组件库:
  - Tailwind CSS 3+ (基础样式)
  - Headless UI (无样式组件)
  - Radix UI (高级组件)

数据可视化:
  - Chart.js 4+ (图表)
  - D3.js (复杂可视化)
  - Three.js (3D效果)

动画库:
  - GSAP (GreenSock) - 主力动画库
  - Framer Motion (React动画)
  - Lottie (JSON动画)

桌面端:
  - Electron 28+ (跨平台桌面应用)
  - Electron Builder (打包)

状态管理:
  - Zustand (轻量状态)
  - TanStack Query (服务端状态)

实时通信:
  - WebSocket (实时数据)
  - Server-Sent Events (单向推送)

开发工具:
  - ESLint + Prettier (代码质量)
  - Husky (Git Hooks)
  - Storybook (组件文档)
```

---

## 📐 设计规范

### 间距系统 (Spacing Scale)

```yaml
0: 0px
1: 4px
2: 8px
3: 12px
4: 16px
5: 20px
6: 24px
8: 32px
10: 40px
12: 48px
16: 64px
20: 80px
24: 96px
```

### 圆角系统 (Border Radius)

```yaml
none: 0px
sm: 4px
md: 8px
lg: 12px
xl: 16px
2xl: 24px
full: 9999px (圆形)
```

### 阴影系统 (Shadows)

```yaml
sm: 0 2px 8px rgba(0, 0, 0, 0.15)
md: 0 4px 16px rgba(0, 0, 0, 0.2)
lg: 0 8px 32px rgba(0, 0, 0, 0.3)
xl: 0 16px 48px rgba(0, 0, 0, 0.4)

# 发光阴影
glow-cyan: 0 0 20px rgba(0, 217, 255, 0.4)
glow-purple: 0 0 20px rgba(168, 85, 247, 0.4)
glow-blue: 0 0 20px rgba(59, 130, 246, 0.4)
```

---

## 🎬 总结

这套赛博朋克风格的UI设计具有以下核心特点：

✅ **视觉冲击力强**
- 深色背景 + 霓虹发光效果
- 科技感十足的网格和扫描线
- 动态数据可视化

✅ **交互体验流畅**
- 丝滑的过渡动画 (GSAP)
- 实时数据更新 (WebSocket)
- 响应式布局适配所有设备

✅ **功能完整**
- Token池管理界面
- 供应商情报展示
- 隐秘操作日志 (主账号专属)
- 系统监控与设置

✅ **可扩展性强**
- 模块化组件设计
- 清晰的设计规范
- 完整的技术栈

这个UI将让鎏灏AI OS看起来就像**来自未来的AI系统**，给用户带来震撼的视觉体验和流畅的操作感受！🚀

---

**文档创建时间**: 2026-08-22  
**参考图片**: C:/Users/Administrator/Desktop/贸易/ui.png  
**下一步**: 开始前端实现 (Week 15-18)
