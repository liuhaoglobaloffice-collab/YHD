import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { SubLayout } from '../components/SubLayout';
import { I18nProvider } from '../i18n';
import { DashboardPage } from '../pages/DashboardPage';
import { EmployeesPage } from '../pages/EmployeesPage';
import { WorkflowPage } from '../pages/WorkflowPage';
import { SecurityPage } from '../pages/SecurityPage';
import { ModelsPage } from '../pages/ModelsPage';
import { MetricsPage } from '../pages/MetricsPage';
import { OnboardingPage } from '../pages/OnboardingPage';
import { AccountsPage } from '../pages/AccountsPage';
import { SubAccountManagementPage } from '../pages/SubAccountManagementPage';
import { EmployeeManagementPage } from '../pages/EmployeeManagementPage';
import { ApprovalQueuePage } from '../pages/ApprovalQueuePage';
import { PermissionCenterPage } from '../pages/PermissionCenterPage';
import { ImportPage } from '../pages/ImportPage';
import { PlatformPage } from '../pages/PlatformPage';
import { InboxPage } from '../pages/InboxPage';
import { MessageTemplatesPage } from '../pages/MessageTemplatesPage';
import { LeadsPage } from '../pages/LeadsPage';
import { SupplierAnalysisPage } from '../pages/SupplierAnalysisPage';
import { ReportPage } from '../pages/ReportPage';
import { SitePage } from '../pages/SitePage';
import { SEOPage } from '../pages/SEOPage';
import { MarketPage } from '../pages/MarketPage';
import { WeeklyMeetingPage } from '../pages/WeeklyMeetingPage';
import { SubPortalPage } from '../pages/SubPortalPage';
import { CompanyPage } from '../pages/CompanyPage';
import { QuotesPage } from '../pages/QuotesPage';
import { GoalCenterPage } from '../pages/GoalCenterPage';
import { LoginPage } from '../pages/LoginPage';
import { clearAuthToken, getAuthToken, fetchMe } from '../services/auth';

/** 加载中页面，放在单独文件避免循环引用 */
function LoadingScreen() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#05070f', color: '#4cc9f0', fontFamily: 'monospace' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 14, marginBottom: 12 }}>LiuHao AI OS</div>
        <div style={{ fontSize: 12, opacity: 0.6 }}>验证身份...</div>
      </div>
    </div>
  );
}

export function AppRoutes() {
  const [checking, setChecking] = useState(true);
  const [valid, setValid] = useState(false);
  const [isSub, setIsSub] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setValid(false);
      setChecking(false);
      return;
    }

    // 验证 token 有效性：调用 /auth/me 检查是否返回正常
    // 使用超时防止网络异常导致无限加载
    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Token validation timeout')), 8000)
    );

    Promise.race([fetchMe(), timeout])
      .then((user) => {
        setValid(true);
        setIsSub((user as { account_type?: string }).account_type === 'sub');
        setChecking(false);
      })
      .catch(() => {
        // token 无效/过期/网络异常，清除并重定向到登录页
        clearAuthToken();
        setValid(false);
        setChecking(false);
      });
  }, []);

  // 正在校验 token
  if (checking) {
    return (
      <I18nProvider>
        <LoadingScreen />
      </I18nProvider>
    );
  }

  // 未登录或 token 无效
  if (!valid) {
    return (
      <I18nProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </I18nProvider>
    );
  }

  // 子账号：专属简化控制台（只读）
  if (isSub) {
    return (
      <I18nProvider>
        <SubLayout>
          <Routes>
            <Route path="/sub-portal" element={<SubPortalPage />} />
            <Route path="/leads" element={<LeadsPage />} />
            <Route path="/weekly-report" element={<ReportPage />} />
            <Route path="/weekly-meeting" element={<WeeklyMeetingPage />} />
            <Route path="/platforms" element={<PlatformPage />} />
            <Route path="/platforms/inbox" element={<InboxPage />} />
            <Route path="/platforms/templates" element={<MessageTemplatesPage />} />
            <Route path="/supplier-analysis" element={<SupplierAnalysisPage />} />
            <Route path="/site" element={<SitePage />} />
            <Route path="/seo" element={<SEOPage />} />
            <Route path="/" element={<Navigate to="/sub-portal" replace />} />
            <Route path="*" element={<Navigate to="/sub-portal" replace />} />
          </Routes>
        </SubLayout>
      </I18nProvider>
    );
  }

  // 主账号：完整控制台
  return (
    <I18nProvider>
      <Layout>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/employees" element={<EmployeeManagementPage />} />
          <Route path="/employees-old" element={<EmployeesPage />} />
          <Route path="/workflow" element={<WorkflowPage />} />
          <Route path="/weekly-meeting" element={<WeeklyMeetingPage />} />
          <Route path="/security" element={<SecurityPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/metrics" element={<MetricsPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/sub-accounts" element={<SubAccountManagementPage />} />
          <Route path="/imports" element={<ImportPage />} />
          <Route path="/approvals" element={<ApprovalQueuePage />} />
          <Route path="/permissions" element={<PermissionCenterPage />} />
          <Route path="/platforms" element={<PlatformPage />} />
          <Route path="/platforms/inbox" element={<InboxPage />} />
          <Route path="/platforms/templates" element={<MessageTemplatesPage />} />
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/weekly-report" element={<ReportPage />} />
          <Route path="/supplier-analysis" element={<SupplierAnalysisPage />} />
          <Route path="/site" element={<SitePage />} />
          <Route path="/seo" element={<SEOPage />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/company" element={<CompanyPage />} />
          <Route path="/quotes" element={<QuotesPage />} />
          <Route path="/goals" element={<GoalCenterPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Layout>
    </I18nProvider>
  );
}