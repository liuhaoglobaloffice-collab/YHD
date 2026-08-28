import { useMemo } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useI18n } from '../i18n';
import { clearAuthToken, getUser } from '../services/auth';
import { useNavigate } from 'react-router-dom';

/** 子账号只读菜单（专属简化控制台） */
const SUB_MENU = [
  { path: '/sub-portal', i18nKey: 'subPortal', icon: '◈' },
  { path: '/leads', i18nKey: 'leadPool', icon: '✉' },
  { path: '/weekly-report', i18nKey: 'weeklyReport', icon: '▤' },
  { path: '/weekly-meeting', i18nKey: 'weeklyMeeting', icon: '▤' },
  { path: '/platforms', i18nKey: 'platformCenter', icon: '✦' },
  { path: '/supplier-analysis', i18nKey: 'supplierAnalysis', icon: '⌖' },
  { path: '/site', i18nKey: 'siteBuilder', icon: '⬢' },
  { path: '/seo', i18nKey: 'seoToolbox', icon: '⌘' },
];

export function SubLayout({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useMemo(() => getUser(), []);

  const handleLogout = () => {
    clearAuthToken();
    navigate('/login', { replace: true });
  };

  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <div className="sub-shell">
      <aside className="sub-sidebar">
        <div className="brand">
          <div className="brand-mark">L</div>
          <span>{t('brand')}</span>
        </div>
        <div className="sub-role-chip">
          <span className="sub-role-dot" />
          {t('subRole')}
        </div>
        <nav className="nav-list">
          {SUB_MENU.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={`nav-link level-3 ${isActive(item.path) ? 'active' : ''}`}
            >
              <span className="nav-dot" />
              {t(item.i18nKey as never)}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="btn btn-sm btn-cancel" onClick={handleLogout}>
            {t('logout')}
          </button>
        </div>
      </aside>

      <div className="sub-main">
        <header className="sub-header">
          <div className="sub-header-title">
            <strong>{t('subPortal')}</strong>
            <span className="sub-readonly-badge">{t('readonlyMode')}</span>
          </div>
          <div className="sub-user">
            <span>{user?.full_name || user?.username}</span>
            <span className="sub-role-text">@{user?.username}</span>
          </div>
        </header>
        <main className="sub-content">{children}</main>
      </div>
    </div>
  );
}