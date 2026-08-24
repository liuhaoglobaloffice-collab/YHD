#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 App.tsx 文件"""

content = """/**
 * LiuHao AI-OS Y1.0
 * CEO Dashboard 应用主入口
 */

import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { authAPI } from './services/authAPI';

// 页面组件
import Login from './pages/Login';
import { DashboardLayout } from './components/DashboardLayout';
import { DashboardPage } from './pages/overview/DashboardPage';
import { AIEmployeesListPage } from './pages/ai-team/AIEmployeesListPage';
import PlaceholderPage from './pages/PlaceholderPage';

/**
 * 路由保护组件
 */
interface ProtectedRouteProps {
  children: React.ReactNode;
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

function App() {
  const { isAuthenticated, token, login } = useAuthStore();

  // 应用启动时验证 Token
  useEffect(() => {
    const verifyToken = async () => {
      if (token && !isAuthenticated) {
        try {
          const user = await authAPI.getCurrentUser();
          login(token, user);
        } catch (error) {
          console.error('Token verification failed:', error);
          useAuthStore.getState().logout();
        }
      }
    };
    
    verifyToken();
  }, []);

  return (
    <Router>
      <Routes>
        {/* 公开路由 */}
        <Route path="/login" element={<Login />} />
        
        {/* 受保护的路由 - 使用 DashboardLayout 作为布局 */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          {/* 默认重定向 */}
          <Route index element={<Navigate to="/overview/dashboard/realtime" replace />} />
          
          {/* 1. 系统总览 */}
          <Route path="overview/dashboard/realtime" element={<DashboardPage />} />
          <Route path="overview/dashboard/statistics" element={<PlaceholderPage title="统计分析" />} />
          <Route path="overview/performance/api" element={<PlaceholderPage title="API性能" />} />
          <Route path="overview/performance/database" element={<PlaceholderPage title="数据库性能" />} />
          <Route path="overview/alerts" element={<PlaceholderPage title="告警中心" />} />

          {/* 2. AI团队 */}
          <Route path="ai-team/employees/list" element={<AIEmployeesListPage />} />
          <Route path="ai-team/employees/add" element={<PlaceholderPage title="添加员工" />} />
          <Route path="ai-team/employees/performance" element={<PlaceholderPage title="绩效管理" />} />
          <Route path="ai-team/agents/list" element={<PlaceholderPage title="Agent列表" />} />
          <Route path="ai-team/agents/capabilities" element={<PlaceholderPage title="能力管理" />} />
          <Route path="ai-team/providers/list" element={<PlaceholderPage title="Provider列表" />} />
          <Route path="ai-team/providers/models" element={<PlaceholderPage title="模型配置" />} />

          {/* 3. 业务运营 */}
          <Route path="business/research/projects" element={<PlaceholderPage title="研发项目" />} />
          <Route path="business/research/innovation" element={<PlaceholderPage title="创新管理" />} />
          <Route path="business/sales/leads" element={<PlaceholderPage title="销售线索" />} />
          <Route path="business/sales/opportunities" element={<PlaceholderPage title="商机管理" />} />
          <Route path="business/sales/customers" element={<PlaceholderPage title="客户管理" />} />
          <Route path="business/operations/daily" element={<PlaceholderPage title="日常运营" />} />
          <Route path="business/operations/reports" element={<PlaceholderPage title="运营报表" />} />

          {/* 4. 知识中心 */}
          <Route path="knowledge/documents/list" element={<PlaceholderPage title="文档列表" />} />
          <Route path="knowledge/documents/upload" element={<PlaceholderPage title="上传文档" />} />
          <Route path="knowledge/documents/categories" element={<PlaceholderPage title="分类管理" />} />
          <Route path="knowledge/memory/search" element={<PlaceholderPage title="知识检索" />} />
          <Route path="knowledge/memory/manage" element={<PlaceholderPage title="记忆管理" />} />
          <Route path="knowledge/brain/entities" element={<PlaceholderPage title="实体管理" />} />
          <Route path="knowledge/brain/graph" element={<PlaceholderPage title="关系图谱" />} />

          {/* 5. 工作流管理 */}
          <Route path="workflow/design/list" element={<PlaceholderPage title="流程列表" />} />
          <Route path="workflow/design/create" element={<PlaceholderPage title="创建流程" />} />
          <Route path="workflow/tasks/list" element={<PlaceholderPage title="任务列表" />} />
          <Route path="workflow/tasks/create" element={<PlaceholderPage title="创建任务" />} />
          <Route path="workflow/tasks/calendar" element={<PlaceholderPage title="任务日历" />} />
          <Route path="workflow/monitoring/realtime" element={<PlaceholderPage title="实时监控" />} />
          <Route path="workflow/monitoring/history" element={<PlaceholderPage title="执行历史" />} />

          {/* 6. 多租户管理 */}
          <Route path="tenant/accounts/main" element={<PlaceholderPage title="主账号管理" />} />
          <Route path="tenant/accounts/sub" element={<PlaceholderPage title="子账号管理" />} />
          <Route path="tenant/tokens/pool" element={<PlaceholderPage title="Token池管理" />} />
          <Route path="tenant/tokens/usage" element={<PlaceholderPage title="使用统计" />} />
          <Route path="tenant/tokens/stealth" element={<PlaceholderPage title="隐秘调度" />} />
          <Route path="tenant/permissions" element={<PlaceholderPage title="权限配置" />} />

          {/* 7. 系统设置 */}
          <Route path="settings/system/general" element={<PlaceholderPage title="通用设置" />} />
          <Route path="settings/system/security" element={<PlaceholderPage title="安全设置" />} />
          <Route path="settings/users/list" element={<PlaceholderPage title="用户列表" />} />
          <Route path="settings/users/roles" element={<PlaceholderPage title="角色管理" />} />
          <Route path="settings/users/permissions" element={<PlaceholderPage title="权限管理" />} />
          <Route path="settings/audit" element={<PlaceholderPage title="审计日志" />} />

          {/* 8. 帮助中心 */}
          <Route path="help/docs" element={<PlaceholderPage title="使用文档" />} />
          <Route path="help/videos" element={<PlaceholderPage title="视频教程" />} />
          <Route path="help/support" element={<PlaceholderPage title="技术支持" />} />

          {/* 404 */}
          <Route path="*" element={<PlaceholderPage title="页面未找到" />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
"""

target_file = r"D:\LiuHao-AI-OS\frontend\src\App.tsx"

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated: {target_file}")
