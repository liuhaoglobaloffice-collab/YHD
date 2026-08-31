import { useMemo, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { clearAuthToken } from '../services/auth';
import { useI18n } from '../i18n';
import { AIStatusDot, getAIStatusConfig } from './AIWorkStatus';
import type { AICoreState } from '../services/live';

interface MenuLeaf {
  path: string;
  i18nKey: string;
}

interface MenuGroup {
  labelKey: string;
  children: MenuLeaf[];
  subGroups?: { labelKey: string; children: MenuLeaf[] }[];
}

interface MenuSection {
  key: string;
  icon: string;
  labelKey: string;
  groups: MenuGroup[];
}

const menuSections: MenuSection[] = [
  {
    key: 'overview',
    icon: '◈',
    labelKey: 'overview',
    groups: [
      {
        labelKey: 'intelligence',
        children: [
          { path: '/dashboard', i18nKey: 'ceoDashboard' },
          { path: '/goals', i18nKey: 'goalCenter' },
        ],
      },
    ],
  },
  {
    key: 'ai',
    icon: '✦',
    labelKey: 'aiTeam',
    groups: [
      {
        labelKey: 'intelligence',
        children: [
          { path: '/employees', i18nKey: 'aiEmployees' },
          { path: '/workflow', i18nKey: 'workflow' },
          { path: '/weekly-meeting', i18nKey: 'aiMeeting' },
        ],
      },
    ],
  },
  {
    key: 'trade',
    icon: '⌖',
    labelKey: 'tradeOps',
    groups: [
      {
        labelKey: 'acquisitionCenter',
        children: [
          { path: '/leads', i18nKey: 'leadPool' },
          { path: '/quotes', i18nKey: 'quotationMgmt' },
          { path: '/company', i18nKey: 'companyMgmt' },
          { path: '/supplier-analysis', i18nKey: 'supplierAnalysis' },
          { path: '/weekly-report', i18nKey: 'weeklyReport' },
        ],
      },
    ],
  },
  {
    key: 'growth',
    icon: '⌖',
    labelKey: 'growthCenter',
    groups: [
      {
        labelKey: 'websiteCenter',
        children: [
          { path: '/site', i18nKey: 'siteBuilder' },
          { path: '/seo', i18nKey: 'seoToolbox' },
        ],
      },
    ],
  },
  {
    key: 'brain',
    icon: '⬢',
    labelKey: 'enterpriseBrain',
    groups: [
      {
        labelKey: 'knowledgeCenter',
        children: [
          { path: '/knowledge', i18nKey: 'knowledgeBase' },
          { path: '/onboarding', i18nKey: 'onboarding' },
        ],
      },
    ],
  },
  {
    key: 'governance',
    icon: '▤',
    labelKey: 'systemGovernance',
    groups: [
      {
        labelKey: 'modelCenter',
        children: [{ path: '/models', i18nKey: 'models' }],
      },
      {
        labelKey: 'securityCenter',
        children: [{ path: '/security', i18nKey: 'security' },
                   { path: '/permissions', i18nKey: 'permissionCenter' },
                   { path: '/approvals', i18nKey: 'approvalQueue' }],
      },
      {
        labelKey: 'systemHealth',
        children: [
          { path: '/metrics', i18nKey: 'metrics' },
          { path: '/platforms', i18nKey: 'platformCenter' },
          { path: '/platforms/inbox', i18nKey: 'unifiedInbox' },
          { path: '/platforms/templates', i18nKey: 'messageTemplates' },
        ],
      },
      {
        labelKey: 'accountCenter',
        children: [
          { path: '/staff', i18nKey: 'employeeMgmt' },
          { path: '/accounts', i18nKey: 'subAccounts' },
          { path: '/imports', i18nKey: 'dataImport' },
        ],
      },
    ],
  },
];

function LeafLink({ leaf, level }: { leaf: MenuLeaf; level: number }) {
  const { t } = useI18n();
  return (
    <NavLink
      to={leaf.path}
      className={({ isActive }) => `nav-link level-${level} ${isActive ? 'active' : ''}`}
    >
      <span className="nav-dot" />
      {t(leaf.i18nKey as never)}
    </NavLink>
  );
}

export function Sidebar({ aiCore }: { aiCore?: AICoreState }) {
  const { t } = useI18n();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const activeSectionKey = useMemo(() => {
    for (const section of menuSections) {
      for (const group of section.groups) {
        for (const leaf of group.children) {
          if (location.pathname.startsWith(leaf.path)) return section.key;
        }
        for (const sub of group.subGroups ?? []) {
          for (const leaf of sub.children) {
            if (location.pathname.startsWith(leaf.path)) return section.key;
          }
        }
      }
    }
    return null;
  }, [location.pathname]);

  const toggle = (key: string) => setCollapsed((c) => ({ ...c, [key]: !c[key] }));

  const handleLogout = () => {
    clearAuthToken();
    window.location.href = '/login';
  };

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">L</div>
        <span>{t('brand')}</span>
      </div>

      <nav className="nav-list">
        {menuSections.map((section) => {
          const isOpen = !collapsed[section.key];
          const isActive = activeSectionKey === section.key;
          return (
            <div className={`nav-section ${isActive ? 'section-active' : ''}`} key={section.key}>
              <button
                className={`nav-section-toggle ${isOpen ? 'open' : ''}`}
                onClick={() => toggle(section.key)}
                aria-expanded={isOpen}
              >
                <span className="nav-section-icon">{section.icon}</span>
                <span className="nav-section-label">{t(section.labelKey as never)}</span>
                <span className="nav-section-arrow" />
              </button>

              {isOpen && (
                <div className="nav-section-body">
                  {section.groups.map((group, gi) => {
                    if (!group.subGroups || group.subGroups.length === 0) {
                      return (
                        <div className="nav-group" key={gi}>
                          <div className="nav-group-label">
                            <span className="nav-group-text">{t(group.labelKey as never)}</span>
                          </div>
                          {group.children.map((leaf) => (
                            <LeafLink leaf={leaf} level={3} key={leaf.path} />
                          ))}
                        </div>
                      );
                    }
                    return (
                      <div className="nav-group" key={gi}>
                        <div className="nav-group-label">
                          <span className="nav-group-text">{t(group.labelKey as never)}</span>
                        </div>
                        {group.subGroups!.map((sub) => (
                          <div className="nav-subgroup" key={sub.labelKey}>
                            <div className="nav-subgroup-label">{t(sub.labelKey as never)}</div>
                            {sub.children.map((leaf) => (
                              <LeafLink leaf={leaf} level={3} key={leaf.path} />
                            ))}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div
          className="hologram-chip"
          title={aiCore?.detail || aiCore?.label || t('systemOnline')}
          role="status"
          aria-label={`AI Core 状态：${aiCore?.label ?? t('systemOnline')}`}
          style={
            aiCore
              ? (() => {
                  const cfg = getAIStatusConfig(aiCore.status);
                  return {
                    color: cfg.color,
                    borderColor: `${cfg.color}40`,
                    background: `${cfg.color}12`,
                  };
                })()
              : undefined
          }
        >
          {aiCore ? (
            <AIStatusDot status={aiCore.status} size={8} />
          ) : (
            <span className="hologram-pulse" />
          )}
          {aiCore ? aiCore.label : t('systemOnline')}
        </div>
        <button className="btn btn-sm btn-cancel sidebar-logout" onClick={handleLogout}>
          {t('logout')}
        </button>
      </div>
    </aside>
  );
}