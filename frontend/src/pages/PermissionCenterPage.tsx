import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../i18n';
import { fetchBusinessRoles, fetchAllPermissions, type BusinessRoleInfo } from '../services/accounts';

const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000';
const API_PREFIX = '/api/v1';

function token(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

const ROLE_COLORS: Record<string, string> = {
  sales: '#4cc9f0',
  purchasing: '#f72585',
  operations: '#7209b7',
  ai_admin: '#facc15',
  general: '#06d6a0',
};

const ROLE_LABELS: Record<string, string> = {
  sales: '销售',
  purchasing: '采购',
  operations: '运营',
  ai_admin: 'AI管理员',
  general: '通用',
};

const PERMISSION_GROUP_LABELS: Record<string, string> = {
  lead: '线索',
  business: '业务',
  platform: '社媒',
  supplier: '供应商',
  site: '独立站',
  seo: 'SEO',
  quote: '报价单',
  task: '任务',
  agent: 'Agent',
  employee: 'AI员工',
  import: '数据导入',
  user: '用户管理',
  audit: '审计',
  role: '角色管理',
  system: '系统',
  ai_brain: 'AI指令',
  workflow: '工作流',
  workforce: 'Workforce',
  approval: '审批',
  policy: '策略',
  knowledge: '知识库',
  business_task: '业务任务',
  business_metrics: '业务指标',
  cost: '成本',
  report: '报告',
  sub_account: '子账号',
  department: '部门',
  api_key: 'API密钥',
};

export function PermissionCenterPage() {
  const { t } = useI18n();
  const [roles, setRoles] = useState<BusinessRoleInfo[]>([]);
  const [allPerms, setAllPerms] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<{
    total_users: number;
    active_subs: number;
    pending_approvals: number;
    roles: Record<string, number>;
  } | null>(null);

  useEffect(() => {
    Promise.all([
      fetchBusinessRoles(),
      fetchAllPermissions(),
      fetch(`${API_BASE}${API_PREFIX}/accounts/permissions/stats`, {
        headers: { Authorization: `Bearer ${token()}` },
      }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([rolesData, permsData, statsData]) => {
      setRoles(rolesData);
      setAllPerms(permsData.permissions || []);
      setStats(statsData);
    }).catch(e => {
      setError('加载权限数据失败');
      console.error(e);
    }).finally(() => setLoading(false));
  }, []);

  // 按模块分组权限
  const groupedPerms = allPerms.reduce<Record<string, string[]>>((acc, p) => {
    const module = p.split(':')[0];
    if (!acc[module]) acc[module] = [];
    acc[module].push(p);
    return acc;
  }, {});

  if (loading) return <div className="page-loading">{t('loading')}...</div>;

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>权限中心</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to="/staff" className="btn btn-submit">员工权限管理</Link>
          <Link to="/approvals" className="btn">审批队列</Link>
        </div>
      </div>
      <p className="card-desc">权限系统架构总览：RBAC + ABAC 混合模型，支持主/子账号、业务角色、数据范围、权限覆盖</p>

      {error && <p className="error-text">{error}</p>}

      {/* ===== 统计概览 ===== */}
      {stats && (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', marginBottom: 20 }}>
          <div className="card" style={{ textAlign: 'center', padding: '16px 12px' }}>
            <div className="cost-value" style={{ fontSize: 28 }}>{stats.total_users}</div>
            <div className="cost-label">总账号数</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: '16px 12px' }}>
            <div className="cost-value" style={{ fontSize: 28, color: '#4cc9f0' }}>{stats.active_subs}</div>
            <div className="cost-label">活跃子账号</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: '16px 12px' }}>
            <div className="cost-value" style={{ fontSize: 28, color: stats.pending_approvals > 0 ? '#facc15' : '#06d6a0' }}>{stats.pending_approvals}</div>
            <div className="cost-label">待审批</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: '16px 12px' }}>
            <div className="cost-value" style={{ fontSize: 28 }}>{roles.length}</div>
            <div className="cost-label">业务角色数</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: '16px 12px' }}>
            <div className="cost-value" style={{ fontSize: 28 }}>{allPerms.length}</div>
            <div className="cost-label">权限总量</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: '16px 12px' }}>
            <div className="cost-value" style={{ fontSize: 28 }}>{Object.keys(groupedPerms).length}</div>
            <div className="cost-label">权限模块</div>
          </div>
        </div>
      )}

      {/* ===== 权限检查优先级 ===== */}
      <div className="card" style={{ marginBottom: 20, padding: '16px 20px' }}>
        <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#4cc9f0' }}>
          权限检查优先级
        </h3>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
          {[
            { label: '① 账号停用', color: '#ef233c', desc: '直接拒绝' },
            { label: '② 主账号', color: '#4cc9f0', desc: '直接放行' },
            { label: '③ 自定义配置', color: '#facc15', desc: '最高优先级覆盖' },
            { label: '④ 业务角色预设', color: '#06d6a0', desc: '岗位默认权限' },
            { label: '⑤ 系统角色兜底', color: '#7209b7', desc: '仅当无业务角色时' },
          ].map((step, i) => (
            <>
              <div
                key={step.label}
                style={{
                  padding: '6px 14px',
                  borderRadius: 8,
                  background: `${step.color}18`,
                  border: `1px solid ${step.color}44`,
                  color: step.color,
                  fontSize: 13,
                  textAlign: 'center',
                }}
              >
                <div style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{step.label}</div>
                <div style={{ fontSize: 11, opacity: 0.7, whiteSpace: 'nowrap' }}>{step.desc}</div>
              </div>
              {i < 4 && <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 18 }}>→</span>}
            </>
          ))}
        </div>
      </div>

      {/* ===== 业务角色 × 权限矩阵 ===== */}
      <div className="card" style={{ marginBottom: 20, padding: '16px 20px', overflowX: 'auto' }}>
        <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#4cc9f0' }}>
          业务角色权限矩阵
        </h3>
        <p className="card-meta" style={{ marginBottom: 12 }}>
          勾选 = 该角色预设拥有此权限 · 主账号始终拥有全部权限 · 可通过自定义配置覆盖
        </p>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <th style={{ padding: '8px 10px', textAlign: 'left', color: 'rgba(255,255,255,0.5)', fontWeight: 500, whiteSpace: 'nowrap' }}>权限模块</th>
              <th style={{ padding: '8px 10px', textAlign: 'left', color: 'rgba(255,255,255,0.5)', fontWeight: 500, whiteSpace: 'nowrap' }}>权限</th>
              {roles.map(r => (
                <th key={r.role} style={{
                  padding: '8px 10px', textAlign: 'center', fontWeight: 600, whiteSpace: 'nowrap',
                  color: ROLE_COLORS[r.role] || '#fff',
                }}>
                  {r.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(groupedPerms).map(([module, perms]) => (
              <tr key={module} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '6px 10px', color: 'rgba(255,255,255,0.5)', fontWeight: 500, whiteSpace: 'nowrap', verticalAlign: 'top' }}>
                  {PERMISSION_GROUP_LABELS[module] || module}
                </td>
                <td style={{ padding: '6px 10px', verticalAlign: 'top' }}>
                  {perms.map(p => (
                    <div key={p} style={{ padding: '1px 0', color: 'rgba(255,255,255,0.6)', whiteSpace: 'nowrap' }}>
                      {p}
                    </div>
                  ))}
                </td>
                {roles.map(r => (
                  <td key={r.role} style={{ padding: '6px 10px', verticalAlign: 'top', textAlign: 'center' }}>
                    {perms.map(p => {
                      const has = r.permissions.includes(p);
                      return (
                        <div key={p} style={{ padding: '1px 0', fontSize: 14 }}>
                          {has ? (
                            <span style={{ color: '#06d6a0' }}>✓</span>
                          ) : (
                            <span style={{ color: 'rgba(255,255,255,0.1)' }}>—</span>
                          )}
                        </div>
                      );
                    })}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ===== 数据范围说明 ===== */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginBottom: 20 }}>
        {[
          {
            scope: 'self',
            label: '仅本人数据',
            icon: '👤',
            desc: '子账号只能看到自己创建的数据',
            rule: 'owner_user_id = 当前用户',
            example: '普通销售人员只能看到自己跟进的线索',
            color: '#4cc9f0',
          },
          {
            scope: 'department',
            label: '本部门数据',
            icon: '👥',
            desc: '子账号只能看到本部门的数据',
            rule: 'department_id = 当前用户部门',
            example: '部门主管可看到整个部门的客户数据',
            color: '#facc15',
          },
          {
            scope: 'all',
            label: '全公司数据',
            icon: '🏢',
            desc: '子账号可看到租户内所有数据',
            rule: '仅 tenant_id 过滤，无用户级限制',
            example: '运营总监可查看全部运营数据',
            color: '#06d6a0',
          },
        ].map(ds => (
          <div key={ds.scope} className="card" style={{ padding: '16px', borderLeft: `3px solid ${ds.color}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 20 }}>{ds.icon}</span>
              <strong style={{ fontSize: 15 }}>{ds.label}</strong>
            </div>
            <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', margin: '0 0 6px' }}>{ds.desc}</p>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 4 }}>
              <code style={{ background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: 4 }}>{ds.rule}</code>
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
              💡 {ds.example}
            </div>
          </div>
        ))}
      </div>

      {/* ===== 角色详情 ===== */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
        {roles.map(r => (
          <div key={r.role} className="card" style={{
            padding: '16px',
            borderTop: `3px solid ${ROLE_COLORS[r.role] || '#4cc9f0'}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h4 style={{ margin: 0, color: ROLE_COLORS[r.role] || '#4cc9f0' }}>
                {r.label}
              </h4>
              <span style={{
                fontSize: 11,
                padding: '2px 8px',
                borderRadius: 10,
                background: `${ROLE_COLORS[r.role] || '#4cc9f0'}22`,
                color: ROLE_COLORS[r.role] || '#4cc9f0',
              }}>
                {r.permissions.length} 项权限
              </span>
            </div>
            <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', margin: '0 0 8px' }}>{r.description}</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {r.permissions.map(p => (
                <span key={p} style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: 'rgba(255,255,255,0.04)',
                  color: 'rgba(255,255,255,0.6)',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}>
                  {p}
                </span>
              ))}
            </div>
            {stats?.roles && stats.roles[r.role] != null && (
              <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
                当前 {stats.roles[r.role]} 人分配此角色
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}