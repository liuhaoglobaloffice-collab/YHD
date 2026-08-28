import { useEffect, useState } from 'react';
import {
  fetchSubAccounts,
  fetchPendingApprovals,
  approveSubAccount,
  approveSubAccountWithRole,
  rejectSubAccount,
  fetchBusinessRoles,
  fetchSubPermissions,
  updateSubPermissions,
  updateSubDataScope,
  createSubAccount,
  type SubAccount,
  type BusinessRoleInfo,
} from '../services/accounts';
import { useI18n } from '../i18n';

const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000';
const API_PREFIX = '/api/v1';

function token(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

const BUSINESS_ROLE_LABELS: Record<string, string> = {
  sales: '销售',
  purchasing: '采购',
  operations: '运营',
  ai_admin: 'AI管理员',
  general: '通用',
};

const BUSINESS_ROLE_COLORS: Record<string, string> = {
  sales: '#4cc9f0',
  purchasing: '#f72585',
  operations: '#7209b7',
  ai_admin: '#facc15',
  general: '#06d6a0',
};

// 权限分组（用于前端展示）
const PERMISSION_GROUPS: Record<string, { label: string; items: string[] }> = {
  customer: {
    label: '客户管理',
    items: ['lead:create', 'lead:read', 'lead:update', 'lead:delete'],
  },
  crm: {
    label: 'CRM',
    items: ['business:create', 'business:read', 'business:update', 'business:execute'],
  },
  platform: {
    label: '社媒平台',
    items: ['platform:read', 'platform:message_send'],
  },
  supplier: {
    label: '供应商管理',
    items: ['supplier:create', 'supplier:read', 'supplier:update', 'supplier:delete'],
  },
  site: {
    label: '独立站与SEO',
    items: ['site:create', 'site:read', 'site:update', 'site:delete', 'seo:read'],
  },
  quote: {
    label: '报价单',
    items: ['quote:create', 'quote:read', 'quote:update', 'quote:send'],
  },
  ai: {
    label: 'AI与任务',
    items: ['task:create', 'task:read', 'task:update', 'task:execute', 'agent:read', 'agent:execute'],
  },
  workforce: {
    label: 'AI员工',
    items: ['employee:create', 'employee:read', 'employee:update', 'employee:delete'],
  },
  data: {
    label: '数据导入',
    items: ['import:create', 'import:read'],
  },
  system: {
    label: '系统管理',
    items: ['user:read', 'audit:read', 'role:read'],
  },
};

export function EmployeeManagementPage() {
  const { t } = useI18n();
  const [accounts, setAccounts] = useState<SubAccount[]>([]);
  const [pending, setPending] = useState<SubAccount[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [error, setError] = useState('');
  const [banner, setBanner] = useState('');

  // 权限控制中心状态
  const [selectedAccount, setSelectedAccount] = useState<SubAccount | null>(null);
  const [permissions, setPermissions] = useState<Record<string, boolean>>({});
  const [dataScope, setDataScope] = useState('self');
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<'permissions' | 'budget' | 'info'>('permissions');

  // 业务角色列表
  const [businessRoles, setBusinessRoles] = useState<BusinessRoleInfo[]>([]);

  // 创建子账号
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    username: '', email: '', password: '', full_name: '',
  });
  const [creating, setCreating] = useState(false);

  // 审批弹窗
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [approveRole, setApproveRole] = useState('general');
  const [approveDataScope, setApproveDataScope] = useState('self');
  const [approveFullName, setApproveFullName] = useState('');

  const loadAccounts = async () => {
    try {
      const data = await fetchSubAccounts();
      setAccounts(data.sub_accounts);
    } catch (e) {
      setError('加载员工列表失败');
      console.error(e);
    }
    setLoading(false);
  };

  const loadPending = async () => {
    setPendingLoading(true);
    try {
      setPending(await fetchPendingApprovals().then(r => r.sub_accounts));
    } catch { /* ignore */ }
    setPendingLoading(false);
  };

  const loadRoles = async () => {
    try {
      setBusinessRoles(await fetchBusinessRoles());
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadAccounts();
    loadPending();
    loadRoles();
  }, []);

  const selectAccount = async (acc: SubAccount) => {
    setSelectedId(acc.id);
    setSelectedAccount(acc);
    setTab('permissions');
    try {
      const permData = await fetchSubPermissions(acc.id);
      setPermissions(permData.permissions_config || {});
      setDataScope(permData.data_scope || 'self');
    } catch {
      setPermissions({});
      setDataScope('self');
    }
  };

  const handlePermissionToggle = (permCode: string) => {
    setPermissions(prev => ({ ...prev, [permCode]: !prev[permCode] }));
  };

  const handleRoleQuickAssign = async (acc: SubAccount, role: string) => {
    try {
      const rolePerms = businessRoles.find(r => r.role === role)?.permissions || [];
      const newPerms: Record<string, boolean> = {};
      rolePerms.forEach(p => { newPerms[p] = true; });
      setPermissions(newPerms);
      // Also update the business_role on the user
      const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${acc.id}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_role: role }),
      });
      if (res.ok) {
        setBanner(`已为「${acc.full_name || acc.username}」分配 ${BUSINESS_ROLE_LABELS[role] || role} 角色`);
        loadAccounts();
      }
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '分配角色失败');
    }
  };

  const handleSavePermissions = async () => {
    if (!selectedId) return;
    setSaving(true);
    setBanner('');
    try {
      await updateSubPermissions(selectedId, permissions);
      await updateSubDataScope(selectedId, dataScope);
      setBanner('权限保存成功');
      loadAccounts();
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '保存失败');
    }
    setSaving(false);
  };

  const handleCreateSubAccount = async () => {
    if (!createForm.username.trim() || !createForm.password.trim()) {
      setBanner('用户名和密码必填');
      return;
    }
    setCreating(true);
    setBanner('');
    try {
      await createSubAccount({
        username: createForm.username.trim(),
        email: createForm.email || `${createForm.username.trim()}@example.com`,
        password: createForm.password,
        full_name: createForm.full_name || undefined,
      });
      setShowCreate(false);
      setCreateForm({ username: '', email: '', password: '', full_name: '' });
      setBanner('子账号创建成功');
      loadAccounts();
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '创建失败');
    }
    setCreating(false);
  };

  const handleApprove = async (subId: number) => {
    setApprovingId(subId);
    setBanner('');
    try {
      await approveSubAccountWithRole(subId, {
        business_role: approveRole,
        data_scope: approveDataScope,
        full_name: approveFullName || undefined,
      });
      setBanner('审批通过，子账号已激活');
      setApprovingId(null);
      setApproveRole('general');
      setApproveDataScope('self');
      setApproveFullName('');
      loadPending();
      loadAccounts();
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '审批失败');
      setApprovingId(null);
    }
  };

  const handleReject = async (subId: number) => {
    try {
      await rejectSubAccount(subId);
      setBanner('已拒绝该申请');
      loadPending();
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '操作失败');
    }
  };

  const handleToggleActive = async (acc: SubAccount) => {
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${acc.id}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !acc.is_active }),
      });
      if (res.ok) {
        setBanner(acc.is_active ? '已停用账号' : '已启用账号');
        loadAccounts();
        if (selectedId === acc.id) selectAccount({ ...acc, is_active: !acc.is_active });
      }
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '操作失败');
    }
  };

  // 获取当前选中账号的角色权限
  const currentRolePerms = selectedAccount?.business_role
    ? businessRoles.find(r => r.role === selectedAccount.business_role)?.permissions || []
    : [];

  if (loading) return <div className="page-loading">{t('loading')}...</div>;

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>员工与权限</h1>
        <button className="btn btn-submit" onClick={() => setShowCreate(true)}>
          + 添加员工
        </button>
      </div>
      <p className="card-desc">管理企业员工账号、角色分配和权限配置</p>

      {error && <p className="error-text">{error}</p>}
      {banner && <div className="sub-mgmt-banner">{banner}</div>}

      {/* 待审核员工 */}
      {pending.length > 0 && (
        <div className="pending-section" style={{ marginBottom: 16 }}>
          <h3 className="section-title">
            <span className="pending-icon">⏳</span>
            待审核员工
            <span className="pending-count">（{pending.length}）</span>
          </h3>
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}>
            {pending.map((p) => (
              <div className="card card-pending" key={p.id}>
                <div className="card-pending-badge">待审核</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <strong>{p.full_name || p.username}</strong>
                  <span className="card-meta">@{p.username}</span>
                </div>
                <div className="card-meta" style={{ marginBottom: 8 }}>
                  申请于 {p.created_at ? new Date(p.created_at).toLocaleString('zh-CN') : 'N/A'}
                </div>

                {/* 审批表单 */}
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 8, marginTop: 8 }}>
                  <div className="form-group" style={{ marginBottom: 8 }}>
                    <label style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>分配角色</label>
                    <select
                      value={approveRole}
                      onChange={(e) => setApproveRole(e.target.value)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: '#fff', fontSize: 13 }}
                    >
                      {businessRoles.map(r => (
                        <option key={r.role} value={r.role}>{r.label} - {r.description}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ marginBottom: 8 }}>
                    <label style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>备注姓名（可选）</label>
                    <input
                      value={approveFullName}
                      onChange={(e) => setApproveFullName(e.target.value)}
                      placeholder="张三"
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)', color: '#fff', fontSize: 13 }}
                    />
                  </div>
                  <div className="sub-actions" style={{ marginTop: 8 }}>
                    <button
                      className="btn btn-sm btn-submit"
                      disabled={approvingId === p.id}
                      onClick={() => handleApprove(p.id)}
                    >
                      {approvingId === p.id ? '审批中...' : '批准'}
                    </button>
                    <button className="btn btn-sm btn-cancel" onClick={() => handleReject(p.id)}>
                      拒绝
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 员工列表与权限控制中心 */}
      <div className="sub-mgmt-layout">
        {/* 左：员工列表 */}
        <aside className="sub-mgmt-side">
          <div className="sub-mgmt-side-title">
            员工列表
            <span className="card-meta" style={{ marginLeft: 8 }}>{accounts.length} 人</span>
          </div>
          {/* 主账号 */}
          <div className="sub-mgmt-acc owner" style={{ pointerEvents: 'none', opacity: 0.8 }}>
            <div className="sub-mgmt-acc-head">
              <span style={{ fontSize: 16 }}>👑</span>
              <strong>主账号（你）</strong>
              <span className="sub-mgmt-badge" style={{ background: 'rgba(76,201,240,0.2)', color: '#4cc9f0' }}>最高权限</span>
            </div>
            <div className="sub-mgmt-acc-sub">系统最高权限，可管理所有员工和配置</div>
          </div>
          {accounts.length === 0 && <p className="sub-mgmt-empty">暂无子账号</p>}
          {accounts.map((acc) => {
            const active = selectedId === acc.id;
            return (
              <button
                key={acc.id}
                className={`sub-mgmt-acc ${active ? 'active' : ''}`}
                onClick={() => selectAccount(acc)}
              >
                <div className="sub-mgmt-acc-head">
                  <strong>{acc.full_name || acc.username}</strong>
                  {acc.business_role && (
                    <span
                      className="sub-mgmt-badge"
                      style={{
                        background: `${BUSINESS_ROLE_COLORS[acc.business_role] || '#666'}22`,
                        color: BUSINESS_ROLE_COLORS[acc.business_role] || '#666',
                        border: `1px solid ${BUSINESS_ROLE_COLORS[acc.business_role] || '#666'}44`,
                      }}
                    >
                      {BUSINESS_ROLE_LABELS[acc.business_role] || acc.business_role}
                    </span>
                  )}
                  <span className={`sub-mgmt-badge ${!acc.is_active ? 'over' : ''}`}>
                    {acc.is_active ? '● 已启用' : '○ 已停用'}
                  </span>
                </div>
                <div className="sub-mgmt-acc-sub">
                  {acc.email} · 数据范围: {acc.data_scope === 'all' ? '全公司' : acc.data_scope === 'department' ? '本部门' : '仅本人'}
                </div>
              </button>
            );
          })}
        </aside>

        {/* 右：权限控制中心 */}
        <main className="sub-mgmt-main">
          {selectedId == null && (
            <div className="sub-mgmt-placeholder">← 选择左侧员工查看和配置权限</div>
          )}

          {selectedId != null && selectedAccount && (
            <>
              {/* 员工信息头部 */}
              <div className="card sub-mgmt-card" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: 0 }}>
                      {selectedAccount.full_name || selectedAccount.username}
                      {selectedAccount.business_role && (
                        <span
                          style={{
                            display: 'inline-block',
                            marginLeft: 8,
                            padding: '2px 8px',
                            borderRadius: 4,
                            fontSize: 12,
                            background: `${BUSINESS_ROLE_COLORS[selectedAccount.business_role] || '#666'}22`,
                            color: BUSINESS_ROLE_COLORS[selectedAccount.business_role] || '#666',
                          }}
                        >
                          {BUSINESS_ROLE_LABELS[selectedAccount.business_role] || selectedAccount.business_role}
                        </span>
                      )}
                    </h3>
                    <p className="card-meta" style={{ margin: '4px 0 0' }}>
                      @{selectedAccount.username} · {selectedAccount.email}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span style={{
                      display: 'inline-block',
                      width: 8, height: 8, borderRadius: '50%',
                      background: selectedAccount.is_active ? '#06d6a0' : '#ff6b6b',
                    }} />
                    <span style={{ fontSize: 12, color: selectedAccount.is_active ? '#06d6a0' : '#ff6b6b' }}>
                      {selectedAccount.is_active ? '已启用' : '已停用'}
                    </span>
                    <button
                      className="btn btn-sm"
                      onClick={() => handleToggleActive(selectedAccount)}
                      style={{ marginLeft: 8 }}
                    >
                      {selectedAccount.is_active ? '停用' : '启用'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Tab 切换 */}
              <div className="sub-mgmt-mode-tabs" style={{ marginBottom: 12 }}>
                <button
                  className={`sub-mgmt-tab ${tab === 'permissions' ? 'active' : ''}`}
                  onClick={() => setTab('permissions')}
                >
                  权限配置
                </button>
                <button
                  className={`sub-mgmt-tab ${tab === 'info' ? 'active' : ''}`}
                  onClick={() => setTab('info')}
                >
                  基本信息
                </button>
              </div>

              {tab === 'permissions' && (
                <>
                  {/* 快速分配角色 */}
                  <div className="card sub-mgmt-card" style={{ marginBottom: 12 }}>
                    <div className="sub-mgmt-card-title">快速分配角色</div>
                    <p className="card-meta" style={{ marginBottom: 8 }}>
                      选择预设角色将自动配置对应的权限组，之后可单独调整。
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {businessRoles.map(r => (
                        <button
                          key={r.role}
                          className="btn btn-sm"
                          style={{
                            background: selectedAccount.business_role === r.role
                              ? `${BUSINESS_ROLE_COLORS[r.role] || '#4cc9f0'}33`
                              : 'rgba(255,255,255,0.05)',
                            border: selectedAccount.business_role === r.role
                              ? `1px solid ${BUSINESS_ROLE_COLORS[r.role] || '#4cc9f0'}`
                              : '1px solid rgba(255,255,255,0.1)',
                            color: selectedAccount.business_role === r.role
                              ? BUSINESS_ROLE_COLORS[r.role] || '#4cc9f0'
                              : 'rgba(255,255,255,0.7)',
                          }}
                          onClick={() => handleRoleQuickAssign(selectedAccount, r.role)}
                          title={r.description}
                        >
                          {r.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 数据范围 */}
                  <div className="card sub-mgmt-card" style={{ marginBottom: 12 }}>
                    <div className="sub-mgmt-card-title">数据权限范围</div>
                    <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                      {[
                        { value: 'self', label: '仅本人数据' },
                        { value: 'department', label: '本部门数据' },
                        { value: 'all', label: '全公司数据' },
                      ].map(opt => (
                        <label
                          key={opt.value}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            padding: '6px 12px', borderRadius: 6,
                            background: dataScope === opt.value ? 'rgba(76,201,240,0.1)' : 'rgba(0,0,0,0.2)',
                            border: dataScope === opt.value ? '1px solid rgba(76,201,240,0.3)' : '1px solid rgba(255,255,255,0.08)',
                            cursor: 'pointer', fontSize: 13,
                          }}
                        >
                          <input
                            type="radio"
                            name="data_scope"
                            value={opt.value}
                            checked={dataScope === opt.value}
                            onChange={() => setDataScope(opt.value)}
                            style={{ accentColor: '#4cc9f0' }}
                          />
                          {opt.label}
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* 细粒度权限 */}
                  <div className="card sub-mgmt-card" style={{ marginBottom: 12 }}>
                    <div className="sub-mgmt-card-title">细粒度权限</div>
                    <p className="card-meta" style={{ marginBottom: 8 }}>
                      当前角色预设权限数：{currentRolePerms.length}，已自定义：{Object.keys(permissions).length}
                    </p>
                    {Object.entries(PERMISSION_GROUPS).map(([groupKey, group]) => {
                      const groupPerms = group.items.filter(p => p in permissions || currentRolePerms.includes(p));
                      if (groupPerms.length === 0) return null;
                      return (
                        <div key={groupKey} style={{ marginBottom: 12, borderBottom: '1px solid rgba(255,255,255,0.04)', paddingBottom: 8 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.5)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                            {group.label}
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {group.items.map(permCode => {
                              const isEnabled = permissions[permCode] ?? currentRolePerms.includes(permCode) ?? false;
                              const isByRole = currentRolePerms.includes(permCode) && !(permCode in permissions);
                              return (
                                <label
                                  key={permCode}
                                  style={{
                                    display: 'flex', alignItems: 'center', gap: 4,
                                    padding: '4px 10px', borderRadius: 6,
                                    background: isEnabled ? 'rgba(6,214,160,0.08)' : 'rgba(0,0,0,0.2)',
                                    border: isEnabled ? '1px solid rgba(6,214,160,0.2)' : '1px solid rgba(255,255,255,0.06)',
                                    cursor: 'pointer', fontSize: 12,
                                    opacity: isByRole ? 0.8 : 1,
                                  }}
                                >
                                  <input
                                    type="checkbox"
                                    checked={isEnabled}
                                    onChange={() => handlePermissionToggle(permCode)}
                                    style={{ accentColor: '#06d6a0' }}
                                  />
                                  <span>{permCode.split(':')[1] || permCode}</span>
                                  {isByRole && <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginLeft: 2 }}>(角色)</span>}
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* 保存按钮 */}
                  <button
                    className="btn btn-submit"
                    onClick={handleSavePermissions}
                    disabled={saving}
                    style={{ width: '100%' }}
                  >
                    {saving ? '保存中...' : '保存权限配置'}
                  </button>
                </>
              )}

              {tab === 'info' && (
                <div className="card sub-mgmt-card">
                  <div className="sub-mgmt-card-title">基本信息</div>
                  <div style={{ marginTop: 8 }}>
                    <div className="form-group">
                      <label>用户名</label>
                      <p style={{ color: 'rgba(255,255,255,0.8)' }}>{selectedAccount.username}</p>
                    </div>
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>邮箱</label>
                      <p style={{ color: 'rgba(255,255,255,0.8)' }}>{selectedAccount.email}</p>
                    </div>
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>姓名</label>
                      <p style={{ color: 'rgba(255,255,255,0.8)' }}>{selectedAccount.full_name || '-'}</p>
                    </div>
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>业务角色</label>
                      <p style={{ color: 'rgba(255,255,255,0.8)' }}>
                        {selectedAccount.business_role
                          ? BUSINESS_ROLE_LABELS[selectedAccount.business_role] || selectedAccount.business_role
                          : '-'
                        }
                      </p>
                    </div>
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>数据范围</label>
                      <p style={{ color: 'rgba(255,255,255,0.8)' }}>
                        {selectedAccount.data_scope === 'all' ? '全公司数据'
                          : selectedAccount.data_scope === 'department' ? '本部门数据'
                          : '仅本人数据'}
                      </p>
                    </div>
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>账号状态</label>
                      <p style={{ color: selectedAccount.is_active ? '#06d6a0' : '#ff6b6b' }}>
                        {selectedAccount.is_active ? '已启用' : '已停用'}
                      </p>
                    </div>
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>注册时间</label>
                      <p style={{ color: 'rgba(255,255,255,0.6)' }}>
                        {selectedAccount.created_at ? new Date(selectedAccount.created_at).toLocaleString('zh-CN') : '-'}
                      </p>
                    </div>
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>AI月度预算</label>
                      <p style={{ color: 'rgba(255,255,255,0.8)' }}>
                        {selectedAccount.ai_budget_monthly != null
                          ? `$${selectedAccount.ai_budget_monthly.toFixed(2)}`
                          : '不限'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {/* 创建子账号弹窗 */}
      {showCreate && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: 440 }}>
            <h3>添加员工</h3>
            <p className="card-desc">创建子账号后，员工可使用此账号登录系统。</p>
            <div className="form-group" style={{ marginTop: 12 }}>
              <label>用户名 *</label>
              <input
                value={createForm.username}
                onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                placeholder="zhangsan"
              />
            </div>
            <div className="form-group" style={{ marginTop: 8 }}>
              <label>邮箱</label>
              <input
                type="email"
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                placeholder="zhangsan@company.com"
              />
            </div>
            <div className="form-group" style={{ marginTop: 8 }}>
              <label>姓名</label>
              <input
                value={createForm.full_name}
                onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                placeholder="张三"
              />
            </div>
            <div className="form-group" style={{ marginTop: 8 }}>
              <label>密码 *</label>
              <input
                type="password"
                value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                placeholder="至少8位"
              />
            </div>
            <div className="sub-actions" style={{ marginTop: 16 }}>
              <button className="btn btn-submit" onClick={handleCreateSubAccount} disabled={creating}>
                {creating ? '创建中...' : '创建'}
              </button>
              <button className="btn btn-cancel" onClick={() => setShowCreate(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}