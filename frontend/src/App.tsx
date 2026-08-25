/**
 * LiuHao AI-OS Y1.0
 * CEO Dashboard 应用主入口
 * 🚀 已移除登录验证 - 直接访问所有页面
 */

import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { DEFAULT_LOCALE, getText, Locale, localeOptions } from './i18n';

// 页面组件
import { DashboardLayout } from './components/DashboardLayout';
import { DashboardPage } from './pages/overview/DashboardPage';
import AlertsPage from './pages/overview/AlertsPage';
import AIEmployeesListPage from './pages/ai-team/AIEmployeesListPage';
import AIEmployeeAddPage from './pages/ai-team/AIEmployeeAddPage';
import AIEmployeePerformancePage from './pages/ai-team/AIEmployeePerformancePage';
import AgentManagementPage from './pages/ai-team/AgentManagementPage';
import AIProvidersPage from './pages/ai-team/AIProvidersPage';
import VoiceConsolePage from './pages/ai-team/VoiceConsolePage';
import FutureDesignPage from './pages/future/FutureDesignPage';
import FuturePlatformPage from './pages/future/FuturePlatformPage';
import TasksListPage from './pages/workflow/TasksListPage';
import TaskCreatePage from './pages/workflow/TaskCreatePage';
import TaskDetailPage from './pages/workflow/TaskDetailPage';
import TaskEditPage from './pages/workflow/TaskEditPage';
import WorkflowDesignPage from './pages/workflow/WorkflowDesignPage';
import WorkflowMonitoringPage from './pages/workflow/WorkflowMonitoringPage';
import TaskCalendarPage from './pages/workflow/TaskCalendarPage';
import SuppliersListPage from './pages/business/SuppliersListPage';
import SupplierDetailPage from './pages/business/SupplierDetailPage';
import BusinessOverviewPage from './pages/business/BusinessOverviewPage';
import SettingsPage from './pages/settings/SettingsPage';
import TenantManagementPage from './pages/tenant/TenantManagementPage';
import KnowledgeCenterPage from './pages/knowledge/KnowledgeCenterPage';
import HelpCenterPage from './pages/help/HelpCenterPage';
import PlaceholderPage from './pages/PlaceholderPage';

function App() {
  const [locale, setLocale] = useState<Locale>(DEFAULT_LOCALE);

  return (
    <Router>
      <div style={{ position: 'fixed', top: 16, right: 20, zIndex: 2000, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 12, color: '#64748b' }}>{getText('language', locale)}:</span>
        <select
          value={locale}
          onChange={(event) => setLocale(event.target.value as Locale)}
          style={{
            border: '1px solid #dbe2ea',
            borderRadius: 8,
            background: '#fff',
            color: '#0f172a',
            padding: '6px 10px',
            fontSize: 12,
          }}
        >
          {localeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <Routes>
        {/* 所有路由都使用 DashboardLayout 作为布局 - 无需登录 */}
        <Route path="/" element={<DashboardLayout />}>
          {/* 默认重定向到Dashboard */}
          <Route index element={<Navigate to="/overview/dashboard/realtime" replace />} />
          
          {/* 1. 系统总览 */}
          <Route path="overview/dashboard/realtime" element={<DashboardPage />} />
          <Route path="overview/dashboard/statistics" element={<DashboardPage />} />
          <Route path="overview/performance/api" element={<DashboardPage />} />
          <Route path="overview/performance/database" element={<DashboardPage />} />
          <Route path="overview/alerts" element={<AlertsPage mode="list" />} />
          <Route path="overview/alerts/list" element={<AlertsPage mode="list" />} />
          <Route path="overview/alerts/rules" element={<AlertsPage mode="rules" />} />

          {/* 2. AI团队 */}
          <Route path="ai-team/employees/list" element={<AIEmployeesListPage />} />
          <Route path="ai-team/employees/add" element={<AIEmployeeAddPage />} />
          <Route path="ai-team/employees/performance" element={<AIEmployeePerformancePage />} />
          <Route path="ai-team/agents/list" element={<AgentManagementPage mode="list" />} />
          <Route path="ai-team/agents/capabilities" element={<AgentManagementPage mode="capabilities" />} />
          <Route path="ai-team/providers/list" element={<AIProvidersPage mode="list" />} />
          <Route path="ai-team/providers/models" element={<AIProvidersPage mode="models" />} />
          <Route path="ai-team/voice/console" element={<VoiceConsolePage />} />

          {/* 未来平台 */}
          <Route path="future/platform" element={<FuturePlatformPage section="platform" />} />
          <Route path="future/desktop" element={<FuturePlatformPage section="desktop" />} />
          <Route path="future/mobile" element={<FuturePlatformPage section="mobile" />} />
          <Route path="future/console" element={<FuturePlatformPage section="console" />} />
          <Route path="future/design" element={<FutureDesignPage />} />

          {/* 3. 业务运营 */}
          <Route path="business/research/projects" element={<BusinessOverviewPage section="research" title="研发项目" />} />
          <Route path="business/research/innovation" element={<BusinessOverviewPage section="research" title="创新管理" />} />
          <Route path="business/suppliers/list" element={<SuppliersListPage />} />
          <Route path="business/suppliers/:supplierId" element={<SupplierDetailPage />} />
          <Route path="business/sales/leads" element={<BusinessOverviewPage section="sales" title="销售线索" />} />
          <Route path="business/sales/opportunities" element={<BusinessOverviewPage section="sales" title="商机管理" />} />
          <Route path="business/sales/customers" element={<BusinessOverviewPage section="sales" title="客户管理" />} />
          <Route path="business/operations/daily" element={<BusinessOverviewPage section="operations" title="日常运营" />} />
          <Route path="business/operations/reports" element={<BusinessOverviewPage section="operations" title="运营报表" />} />

          {/* 4. 知识中心 */}
          <Route path="knowledge/documents/list" element={<KnowledgeCenterPage section="documents-list" />} />
          <Route path="knowledge/documents/upload" element={<KnowledgeCenterPage section="documents-upload" />} />
          <Route path="knowledge/documents/categories" element={<KnowledgeCenterPage section="documents-categories" />} />
          <Route path="knowledge/memory/search" element={<KnowledgeCenterPage section="memory-search" />} />
          <Route path="knowledge/memory/manage" element={<KnowledgeCenterPage section="memory-manage" />} />
          <Route path="knowledge/brain/entities" element={<KnowledgeCenterPage section="brain-entities" />} />
          <Route path="knowledge/brain/graph" element={<KnowledgeCenterPage section="brain-graph" />} />

          {/* 5. 工作流管理 */}
          <Route path="workflow/design/list" element={<WorkflowDesignPage mode="list" />} />
          <Route path="workflow/design/create" element={<WorkflowDesignPage mode="create" />} />
          <Route path="workflow/tasks/list" element={<TasksListPage />} />
          <Route path="workflow/tasks/create" element={<TaskCreatePage />} />
          <Route path="workflow/tasks/:taskId/edit" element={<TaskEditPage />} />
          <Route path="workflow/tasks/:taskId" element={<TaskDetailPage />} />
          <Route path="workflow/tasks/calendar" element={<TaskCalendarPage />} />
          <Route path="workflow/monitoring/realtime" element={<WorkflowMonitoringPage />} />
          <Route path="workflow/monitoring/history" element={<WorkflowMonitoringPage />} />

          {/* 6. 多租户管理 */}
          <Route path="tenant/accounts/main" element={<TenantManagementPage section="accounts-main" />} />
          <Route path="tenant/accounts/sub" element={<TenantManagementPage section="accounts-sub" />} />
          <Route path="tenant/tokens/pool" element={<TenantManagementPage section="tokens-pool" />} />
          <Route path="tenant/tokens/usage" element={<TenantManagementPage section="tokens-usage" />} />
          <Route path="tenant/tokens/stealth" element={<TenantManagementPage section="tokens-stealth" />} />
          <Route path="tenant/permissions" element={<TenantManagementPage section="permissions" />} />

          {/* 7. 系统设置 */}
          <Route path="settings/system/general" element={<SettingsPage section="general" />} />
          <Route path="settings/system/security" element={<SettingsPage section="security" />} />
          <Route path="settings/users/list" element={<SettingsPage section="users" />} />
          <Route path="settings/users/roles" element={<SettingsPage section="roles" />} />
          <Route path="settings/users/permissions" element={<SettingsPage section="permissions" />} />
          <Route path="settings/audit" element={<SettingsPage section="audit" />} />

          {/* 8. 帮助中心 */}
          <Route path="help/docs" element={<HelpCenterPage section="docs" />} />
          <Route path="help/videos" element={<HelpCenterPage section="videos" />} />
          <Route path="help/support" element={<HelpCenterPage section="support" />} />

          {/* 404 */}
          <Route path="*" element={<PlaceholderPage title="页面未找到" />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
