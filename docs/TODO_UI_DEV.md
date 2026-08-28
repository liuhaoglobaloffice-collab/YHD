# UI 前端开发计划

> 记录自 GPT 优化建议中可取的 UI 部分，剔除不可取的部分（3D Avatar、粒子背景等），形成可执行的轻量级方案。

---

## 技术栈

| 层 | 选型 | 说明 |
|---|------|------|
| 框架 | React 18 + TypeScript | 主流方案 |
| 构建 | Vite | 快速 HMR |
| 样式 | Tailwind CSS | 深色主题 |
| 路由 | React Router v6 | SPA 路由 |
| 动画 | GSAP | 页面转场、元素动画 |
| 状态管理 | Zustand | 轻量 |
| 图标 | Lucide React | 一致性好 |
| 图表 | Recharts | 简单够用 |
| 代码高亮 | Shiki | AI 对话需要 |

> 砍掉 Three.js / React Three Fiber / 3D Avatar / VRM 加载器等非核心依赖。

---

## 分步实施

### Week 1: 基础框架 + 核心页面

**Day 1-2: 项目初始化**
- `npm create vite@latest frontend -- --template react-ts`
- 配置 Tailwind CSS（深色赛博朋克主题）
- 设置路由结构（React Router v6）
- 配置 Zustand store

**Day 3-4: 登录页面 + 侧边栏菜单**
- 登录/注册表单（样式参考深色主题）
- 九宫格侧边栏导航（一级菜单 + 二级展开）
- 基础布局骨架（Sidebar + Content）

**Day 5-7: 总览仪表板 + AI对话界面**
- 仪表板：系统状态卡片、快速操作、统计数字
- AI对话：消息气泡、输入框、会话列表
- 对接后端 API（/api/ai-brain, /api/chat 等）

### Week 2: 业务页面 + 完善

**Day 8-9: Token管理面板**
- Token余额展示
- 按 Provider 分类统计
- 子账号 Token 列表
- 对接后端 API

**Day 10-11: 子账号管理界面**
- 子账号列表
- 创建/暂停/删除子账号
- 权限控制

**Day 12-14: 打磨 + 错误处理**
- 加载状态（Skeleton 骨架屏）
- 错误提示（Toast 通知）
- 空状态处理
- 响应式适配（先桌面，后移动）

---

## 赛博朋克主题 Token

```
深空蓝:    #0a0e27
霓虹青:    #00d9ff
电子紫:    #a855f7
琥珀橙:    #f59e0b
翡翠绿:    #10b981
赤红:      #ef4444
玻璃态:    rgba(15, 22, 41, 0.6) + backdrop-blur-xl
字体:      JetBrains Mono (英文) / 思源黑体 (中文)
```

---

## 目录结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/          # Sidebar, TopNav, Layout
│   │   ├── ui/              # Button, Card, Input, GlassPanel
│   │   ├── charts/          # TokenChart, UsageChart
│   │   └── chat/            # MessageBubble, ChatInput, SessionList
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── AIChat.tsx
│   │   ├── TokenManager.tsx
│   │   └── SubAccounts.tsx
│   ├── hooks/               # useAuth, useToken, useTheme
│   ├── services/            # api.ts, auth.service.ts, token.service.ts
│   ├── stores/              # authStore, tokenStore, uiStore
│   ├── styles/              # index.css, cyberpunk.css
│   ├── types/               # index.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

---

## 完成标准

- [ ] 登录/注册页面可用，对接后端认证
- [ ] 侧边栏菜单导航流畅
- [ ] 仪表板展示系统状态统计数据
- [ ] AI对话界面可收发消息
- [ ] Token管理面板展示余额和消耗
- [ ] 子账号管理可创建/禁用
- [ ] 所有页面错误处理和加载状态完整
- [ ] 赛博朋克主题一致