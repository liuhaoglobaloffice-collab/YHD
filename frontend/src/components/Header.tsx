import { NavLink, useLocation } from 'react-router-dom';
import { useI18n } from '../i18n';

export function Header() {
  const { lang, setLang, t } = useI18n();
  const location = useLocation();

  // 根据当前路由显示标题
  const pageTitle = (() => {
    const path = location.pathname;
    if (path.startsWith('/dashboard')) return t('ceoDashboard');
    if (path.startsWith('/employees')) return t('aiEmployees');
    if (path.startsWith('/workflow')) return t('workflow');
    if (path.startsWith('/weekly-meeting')) return t('weeklyMeeting');
    if (path.startsWith('/security')) return t('security');
    if (path.startsWith('/models')) return t('models');
    if (path.startsWith('/metrics')) return t('metrics');
    if (path.startsWith('/onboarding')) return t('onboarding');
    return 'LiuHao AI OS';
  })();

  return (
    <header className="app-header">
      <div className="header-breadcrumb">
        <NavLink to="/" className="header-crumb-root">
          LiuHao AI OS
        </NavLink>
        <span className="header-crumb-sep">/</span>
        <span className="header-title">{pageTitle}</span>
      </div>
      <div className="header-actions">
        <span className="health-dot" />
        <span className="header-status">{t('systemOnline')}</span>
        <div className="lang-switch">
          <button
            className={`lang-btn ${lang === 'zh' ? 'active' : ''}`}
            onClick={() => setLang('zh')}
          >
            中文
          </button>
          <button
            className={`lang-btn ${lang === 'en' ? 'active' : ''}`}
            onClick={() => setLang('en')}
          >
            EN
          </button>
        </div>
      </div>
    </header>
  );
}