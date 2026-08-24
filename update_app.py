#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新 App.tsx 文件"""

content = """/**
 * LiuHao AI-OS Y1.0
 * CEO Dashboard 应用主入口
 * 
 * 使用三级菜单系统 + Zustand 状态管理
 */

import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { authAPI } from './services/authAPI';

// 页面组件
import Login from './pages/Login';
import { DashboardLayout } from './components/DashboardLayout';
import DashboardPage from './pages/overview/DashboardPage';
import AIEmployeesListPage from './pages/ai-team/AIEmployeesListPage';
import PlaceholderPage from './pages/PlaceholderPage';

/**
 * 路由保护组件
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
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
        
        {/* 受保护的路由 */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <DashboardLayout>
                <Routes>
                  {/* 默认重定向到仪表板 */}
                  <Route path="/" element={<Navigate to="/overview/dashboard/realtime" replace />} />
                  
                  {/* ===== 1. 系统总览 ===== */}
                  <Route path="/overview/dashboard/realtime" element={<DashboardPage />} />
                  <Route path="/overview/dashboard/statistics" element={<PlaceholderPage module="系统总览" page="统计分析" />} />
                  <Route path="/overview/performance/api" element={<PlaceholderPage module="系统总览" page="API性能" />} />
                  <Route path="/overview/performance/database" element={<PlaceholderPage module="系统总览" page="数据库性能" />} />
                  <Route path="/overview/alerts" element={<PlaceholderPage module="系统总览" page="告警中心" />} />

                  {/* ===== 2. AI团队 ===== */}
                  <Route path="/ai-team/employees/list" element={<AIEmployeesListPage />} />
                  <Route path="/ai-team/employees/add" element={<PlaceholderPage module="AI团队" page="添加员工" />} />
                  <Route path="/ai-team/employees/performance" element={<PlaceholderPage module="AI团队" page="绩效管理" />} />
                  <Route path="/ai-team/agents/list" element={<PlaceholderPage module="AI团队" page="Agent列表" />} />
                  <Route path="/ai-team/agents/capabilities" element={<PlaceholderPage module="AI团队" page="能力管理" />} />
                  <Route path="/ai-team/providers/list" element={<PlaceholderPage module="AI团队" page="Provider列表" />} />
                  <Route path="/ai-team/providers/models" element={<PlaceholderPage module="AI团队" page="模型配置" />} />

                  {/* ===== 3. 业务运营 ===== */}
                  <Route path="/business/research/projects" element={<PlaceholderPage module="业务运营" page="研发项目" />} />
                  <Route path="/business/research/innovation" element={<PlaceholderPage module="业务运营" page="创新管理" />} />
                  <Route path="/business/sales/leads" element={<PlaceholderPage module="业务运营" page="销售线索" />} />
                  <Route path="/business/sales/opportunities" element={<PlaceholderPage module="业务运营" page="商机管理" />} />
                  <Route path="/business/sales/customers" element={<PlaceholderPage module="业务运营" page="客户管理" />} />
                  <Route path="/business/operations/daily" element={<PlaceholderPage module="业务运营" page="日常运营" />} />
                  <Route path="/business/operations/reports" element={<PlaceholderPage module="业务运营" page="运营报表" />} />

                  {/* ===== 4. 知识中心 ===== */}
                  <Route path="/knowledge/documents/list" element={<PlaceholderPage module="知识中心" page="文档列表" />} />
                  <Route path="/knowledge/documents/upload" element={<PlaceholderPage module="知识中心" page="上传文档" />} />
                  <Route path="/knowledge/documents/categories" element={<PlaceholderPage module="知识中心" page="分类管理" />} />
                  <Route path="/knowledge/memory/search" element={<PlaceholderPage module="知识中心" page="知识检索" />} />
                  <Route path="/knowledge/memory/manage" element={<PlaceholderPage module="知识中心" page="记忆管理" />} />
                  <Route path="/knowledge/brain/entities" element={<PlaceholderPage module="知识中心" page="实体管理" />} />
                  <Route path="/knowledge/brain/graph" element={<PlaceholderPage module="知识中心" page="关系图谱" />} />

                  {/* ===== 5. 工作流管理 ===== */}
                  <Route path="/workflow/design/list" element={<PlaceholderPage module="工作流管理" page="流程列表" />} />
                  <Route path="/workflow/design/create" element={<PlaceholderPage module="工作流管理" page="创建流程" />} />
                  <Route path="/workflow/tasks/list" element={<PlaceholderPage module="工作流管理" page="任务列表" />} />
                  <Route path="/workflow/tasks/create" element={<PlaceholderPage module="工作流管理" page="创建任务" />} />
                  <Route path="/workflow/tasks/calendar" element={<PlaceholderPage module="工作流管理" page="任务日历" />} />
                  <Route path="/workflow/monitoring/realtime" element={<PlaceholderPage module="工作流管理" page="实时监控" />} />
                  <Route path="/workflow/monitoring/history" element={<PlaceholderPage module="工作流管理" page="执行历史" />} />

                  {/* ===== 6. 多租户管理 ===== */}
                  <Route path="/tenant/accounts/main" element={<PlaceholderPage module="多租户管理" page="主账号管理" />} />
                  <Route path="/tenant/accounts/sub" element={<PlaceholderPage module="多租户管理" page="子账号管理" />} />
                  <Route path="/tenant/tokens/pool" element={<PlaceholderPage module="多租户管理" page="Token池管理" />} />
                  <Route path="/tenant/tokens/usage" element={<PlaceholderPage module="多租户管理" page="使用统计" />} />
                  <Route path="/tenant/tokens/stealth" element={<PlaceholderPage module="多租户管理" page="隐秘调度" />} />
                  <Route path="/tenant/permissions" element={<PlaceholderPage module="多租户管理" page="权限配置" />} />

                  {/* ===== 7. 系统设置 ===== */}
                  <Route path="/settings/system/general" element={<PlaceholderPage module="系统设置" page="通用设置" />} />
                  <Route path="/settings/system/security" element={<PlaceholderPage module="系统设置" page="安全设置" />} />
                  <Route path="/settings/users/list" element={<PlaceholderPage module="系统设置" page="用户列表" />} />
                  <Route path="/settings/users/roles" element={<PlaceholderPage module="系统设置" page="角色管理" />} />
                  <Route path="/settings/users/permissions" element={<PlaceholderPage module="系统设置" page="权限管理" />} />
                  <Route path="/settings/audit" element={<PlaceholderPage module="系统设置" page="审计日志" />} />

                  {/* ===== 8. 帮助中心 ===== */}
                  <Route path="/help/docs" element={<PlaceholderPage module="帮助中心" page="使用文档" />} />
                  <Route path="/help/videos" element={<PlaceholderPage module="帮助中心" page="视频教程" />} />
                  <Route path="/help/support" element={<PlaceholderPage module="帮助中心" page="技术支持" />} />

                  {/* 404 */}
                  <Route path="*" element={<PlaceholderPage module="404" page="页面未找到" />} />
                </Routes>
              </DashboardLayout>
            </ProtectedRoute>
          }
        />
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
