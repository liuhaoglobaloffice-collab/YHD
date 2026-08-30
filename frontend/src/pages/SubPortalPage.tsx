import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../i18n';
import { getUser } from '../services/auth';
import { fetchMyBudget, type SubBudget } from '../services/accounts';
import { fetchCEOSummaryReport, type CEOSummaryReport } from '../services/ceo';

interface Overview {
  version?: string;
  status?: string;
  total_records?: number;
  modules?: Record<string, number>;
}

const MODULE_LABELS: Record<string, string> = {
  ai_employees: 'AI 员工',
  leads: '客户线索',
  suppliers: '供应商',
  supplier_reports: '供应商报告',
  platform_accounts: '平台账号',
  platform_messages: '平台消息',
  site_pages: '独立站页面',
  keyword_ranks: '关键词排名',
};

/** 子账号专属简化控制台首页（只读聚合视图） */
export function SubPortalPage() {
  const { t } = useI18n();
  const user = getUser();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [budget, setBudget] = useState<SubBudget | null>(null);
  const [ceoSummary, setCeoSummary] = useState<CEOSummaryReport | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(
      `${import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000'}/api/v1/system/overview`,
      { headers: { Authorization: `Bearer ${localStorage.getItem('liuhao_auth_token') ?? ''}` } }
    )
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setOverview)
      .catch((e) => setError(`overview: ${String(e)}`));
    fetchMyBudget()
      .then(setBudget)
      .catch(() => undefined);
    fetchCEOSummaryReport(7)
      .then(setCeoSummary)
      .catch(() => undefined);
  }, []);

  const shortcuts = [
    { path: '/leads', key: 'leadPool', desc: 'subShortcutLeads' },
    { path: '/platforms', key: 'platformCenter', desc: 'subShortcutPlatforms' },
    { path: '/supplier-analysis', key: 'supplierAnalysis', desc: 'subShortcutSupplier' },
    { path: '/weekly-meeting', key: 'weeklyMeeting', desc: 'subShortcutMeeting' },
  ];

  return (
    <div className="sub-portal-page">
      <div className="sub-welcome-card">
        <div className="sub-welcome-icon">👋</div>
        <div>
          <h2>
            {t('subWelcome')}，{user?.full_name || user?.username}
          </h2>
          <p>{t('subWelcomeDesc')}</p>
        </div>
        <span className="sub-readonly-badge">{t('readonlyMode')}</span>
      </div>

      {error && <p className="error-text">{error}</p>}

      {ceoSummary && (
        <div className="card sub-ceo-summary">
          <div className="sub-budget-head">
            <span className="cost-label">CEO 经营摘要（近 {ceoSummary.period_days} 天）</span>
            <span className={`sub-budget-badge ${ceoSummary.status === 'partially_degraded' ? 'over' : ''}`}>
              {ceoSummary.status === 'generated' ? '已生成' : '部分降级'}
            </span>
          </div>
          <div className="sub-stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 8 }}>
            <div className="sub-stat-card">
              <div className="sub-stat-value">{(ceoSummary.report.kpis as any)?.ai_employees ?? 0}</div>
              <div className="sub-stat-label">在线 AI 员工</div>
            </div>
            <div className="sub-stat-card">
              <div className="sub-stat-value">{(ceoSummary.report.kpis as any)?.running_tasks ?? 0}</div>
              <div className="sub-stat-label">执行中任务</div>
            </div>
            <div className="sub-stat-card">
              <div className="sub-stat-value">{(ceoSummary.report.kpis as any)?.suppliers ?? 0}</div>
              <div className="sub-stat-label">供应商</div>
            </div>
            <div className="sub-stat-card">
              <div className="sub-stat-value">{(ceoSummary.report.goals as any)?.count ?? 0}</div>
              <div className="sub-stat-label">经营目标</div>
            </div>
          </div>
          <div className="cost-sub" style={{ lineHeight: 1.7 }}>
            • KPI: {ceoSummary.report.kpis.message ?? '暂无'}<br />
            • 告警: {ceoSummary.report.alerts.message ?? '暂无'}
            {ceoSummary.report.alerts.items && ceoSummary.report.alerts.items.length > 0 ? `（${ceoSummary.report.alerts.items.length} 条）` : null}
            <br />
            • 成本: {ceoSummary.report.cost.message ?? '暂无'}
            {typeof (ceoSummary.report.cost as any)?.total_usd === 'number'
              ? ` · $${(ceoSummary.report.cost as any).total_usd.toFixed(4)}`
              : null}
          </div>
        </div>
      )}

      {/* 只读模块概览 */}
      {overview?.modules && (
        <div className="sub-stats-grid">
          {Object.entries(overview.modules)
            .filter(([k]) => MODULE_LABELS[k])
            .map(([k, v]) => (
              <div key={k} className="sub-stat-card">
                <div className="sub-stat-value">{v}</div>
                <div className="sub-stat-label">{MODULE_LABELS[k]}</div>
              </div>
            ))}
        </div>
      )}

      {budget && (
        <div className="card sub-budget-card">
          <div className="sub-budget-head">
            <span className="cost-label">本月 AI 预算（{budget.month}）</span>
            <span className={`sub-budget-badge ${budget.over_budget ? 'over' : ''}`}>
              {budget.over_budget ? '已超预算' : budget.monthly_budget != null ? '预算内' : '未设预算'}
            </span>
          </div>
          <div className="sub-budget-body">
            <strong className="cost-value">
              ${budget.used_usd.toFixed(4)}
              {budget.monthly_budget != null && (
                <span className="sub-budget-total"> / ${budget.monthly_budget}</span>
              )}
            </strong>
            <span className="cost-sub">
              {budget.calls} 次调用 · 剩余{' '}
              {budget.remaining_usd != null ? `$${budget.remaining_usd.toFixed(4)}` : '不限'}
            </span>
          </div>
        </div>
      )}

      <div className="sub-shortcuts">
        {shortcuts.map((s) => (
          <Link key={s.path} to={s.path} className="sub-shortcut-card">
            <strong>{t(s.key as never)}</strong>
            <span>{t(s.desc as never)}</span>
          </Link>
        ))}
      </div>

      <div className="sub-permission-note">
        <strong>🛡 {t('subPermissionNote')}</strong>
        <p>{t('subPermissionNoteDesc')}</p>
      </div>
    </div>
  );
}
