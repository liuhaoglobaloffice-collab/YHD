# LiuHao AI-OS Frontend

现代化的 CEO 控制台前端应用

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 快速构建工具
- **Tailwind CSS** - 样式框架
- **React Router** - 路由管理
- **Axios** - HTTP 客户端
- **Lucide React** - 图标库

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器 (http://localhost:3000)
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 功能特性

- ✅ 用户认证（登录/登出）
- ✅ CEO 仪表板总览
- ✅ AI 员工管理
- ✅ 任务管理
- ✅ 系统状态监控
- ✅ 响应式设计

## 目录结构

```
frontend/
├── src/
│   ├── components/     # 可复用组件
│   ├── pages/          # 页面组件
│   ├── services/       # API 服务
│   ├── utils/          # 工具函数
│   ├── styles/         # 全局样式
│   ├── App.tsx         # 主应用组件
│   └── main.tsx        # 应用入口
├── public/             # 静态资源
└── index.html          # HTML 模板
```

## API 代理

开发服务器自动代理 `/api` 请求到后端 `http://localhost:8000`

## 默认账号

```
用户名: sysadmin
密码: SysAdmin123
```
