# 鎏灏 AI-OS UI 操作平台

## 🎯 概述

鎏灏 AI-OS 的前端控制台，提供完整的可视化操作界面。

## ✨ 新增功能

### 供应商情报系统 (Module 48)

**访问路径**: 业务运营 → 供应商情报 → 供应商列表

**功能特性**:
- ✅ 供应商列表展示
- ✅ 实时搜索过滤
- ✅ 状态筛选 (活跃/停用/待审核/黑名单)
- ✅ 类型筛选 (制造商/贸易商/代理商/分销商/服务商)
- ✅ 风险等级显示
- ✅ 统计卡片 (总数/活跃/待审核/高风险)
- ✅ 操作按钮 (查看/编辑/删除)

**技术实现**:
- React 18 + TypeScript
- Tailwind CSS (响应式设计)
- Lucide React Icons
- 与后端 API (`/api/v1/suppliers`) 集成

## 🚀 快速开始

### 前置条件
- Node.js 18+
- npm 或 yarn

### 安装依赖
```bash
cd D:\LiuHao-AI-OS\frontend
npm install
```

### 启动开发服务器
```bash
npm run dev
```

服务器将在 http://localhost:3000 启动（如果端口占用会自动切换）

### 构建生产版本
```bash
npm run build
```

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/          # 通用组件
│   │   ├── DashboardLayout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── Breadcrumb.tsx
│   ├── pages/              # 页面组件
│   │   ├── overview/       # 系统总览
│   │   ├── ai-team/        # AI团队
│   │   ├── supplier/       # 供应商情报 ✨新增
│   │   │   └── SupplierListPage.tsx
│   │   └── ...
│   ├── config/
│   │   └── menuConfig.ts   # 三级菜单配置
│   ├── services/
│   │   └── api.ts          # API服务
│   ├── App.tsx             # 主应用
│   └── main.tsx            # 入口文件
├── public/                 # 静态资源
└── package.json
```

## 🔐 认证与权限

### 默认测试账号
- **用户名**: `admin`
- **密码**: `admin123`

### API认证
系统使用 JWT Token 进行认证：
- Token 存储在 localStorage
- 请求头自动携带 `Authorization: Bearer {token}`
- Token 过期自动跳转登录页

## 🎨 UI 设计特点

### 配色方案
- 主色调：蓝色 (#3B82F6)
- 成功：绿色 (#10B981)
- 警告：黄色 (#F59E0B)
- 危险：红色 (#EF4444)
- 背景：深灰 (#111827)

### 响应式设计
- 桌面优先 (Desktop-first)
- 支持各种屏幕尺寸
- 移动端友好

### 图标系统
使用 Lucide React 图标库：
- 一致的视觉风格
- 轻量级 (Tree-shakeable)
- 完整的 TypeScript 支持

## 📋 可用路由

### 系统总览
- `/overview/dashboard/realtime` - 实时监控
- `/overview/dashboard/statistics` - 统计分析
- `/overview/performance/api` - API性能
- `/overview/alerts` - 告警中心

### AI 团队
- `/ai-team/employees/list` - AI员工列表
- `/ai-team/employees/add` - 添加AI员工
- `/ai-team/agents/list` - Agent列表
- `/ai-team/providers/list` - Provider列表

### 业务运营
- `/business/supplier/list` - **供应商列表 ✨新增**
- `/business/supplier/add` - 添加供应商
- `/business/supplier/intelligence` - 情报分析
- `/business/sales/leads` - 销售线索
- `/business/sales/customers` - 客户管理

### 知识中心
- `/knowledge/documents/list` - 文档列表
- `/knowledge/memory/search` - 知识检索

### 工作流管理
- `/workflow/designer/list` - 流程列表
- `/workflow/tasks/list` - 任务列表

## 🔧 配置说明

### API 基础URL
在 `src/services/api.ts` 中配置:
```typescript
const API_BASE_URL = 'http://localhost:8000';
```

### 开发代理
在 `vite.config.ts` 中配置代理，避免 CORS 问题:
```typescript
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

## 🐛 故障排除

### 端口占用
```bash
# 检查端口占用
netstat -ano | findstr :3000

# 或修改端口
vite --port 3001
```

### 依赖问题
```bash
# 清除缓存重装
rm -rf node_modules package-lock.json
npm install
```

### API 连接失败
1. 确认后端服务运行: `http://localhost:8000`
2. 检查网络请求是否被 CORS 阻止
3. 验证 Token 是否有效

## 📞 技术支持

- **项目文档**: `/docs`
- **API 文档**: http://localhost:8000/docs
- **开发者**: 鎏灏AI团队

---

**最后更新**: 2026-08-23  
**版本**: Y1.0 Week 2
