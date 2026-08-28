import { useEffect, useState } from 'react';
import {
  approveSubAccount,
  createSubAccount,
  fetchPendingApprovals,
  fetchSubAccounts,
  rejectSubAccount,
  updateSubAccount,
  type SubAccount,
} from '../services/accounts';
import { useI18n } from '../i18n';

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  user: '用户',
  viewer: '只读',
};

export function AccountsPage() {
  const { t } = useI18n();
  const [accounts, setAccounts] = useState<SubAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // 待审核申请
  const [pending, setPending] = useState<SubAccount[]>([]);
  const [reviewError, setReviewError] = useState('');

  // 创建表单
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role: 'viewer',
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  const load = async () => {
    try {
      const data = await fetchSubAccounts();
      setAccounts(data.sub_accounts);
    } catch (e) {
      console.error('Failed to load sub accounts', e);
      setError('加载子账号列表失败');
    }
    setLoading(false);
  };

  const loadPending = async () => {
    try {
      const data = await fetchPendingApprovals();
      setPending(data.sub_accounts);
    } catch (e) {
      console.error('Failed to load pending approvals', e);
      setError('加载待审核申请失败');
    }
  };

  useEffect(() => {
    load();
    loadPending();
  }, []);

  const handleApprove = async (sub: SubAccount) => {
    try {
      await approveSubAccount(sub.id);
      await Promise.all([load(), loadPending()]);
    } catch (e) {
      setReviewError(e instanceof Error ? e.message : '操作失败');
    }
  };

  const handleReject = async (sub: SubAccount) => {
    try {
      await rejectSubAccount(sub.id);
      await loadPending();
    } catch (e) {
      setReviewError(e instanceof Error ? e.message : '操作失败');
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setCreateError('');
    try {
      await createSubAccount({
        username: form.username,
        email: form.email,
        password: form.password,
        full_name: form.full_name || undefined,
        role: form.role,
      });
      setShowCreate(false);
      setForm({ username: '', email: '', password: '', full_name: '', role: 'viewer' });
      load();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : '创建失败');
    }
    setCreating(false);
  };

  const handleToggleRole = async (acc: SubAccount) => {
    try {
      const nextRole = acc.role === 'viewer' ? 'user' : 'viewer';
      await updateSubAccount(acc.id, { role: nextRole });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败');
    }
  };

  const handleToggleActive = async (acc: SubAccount) => {
    try {
      await updateSubAccount(acc.id, { is_active: !acc.is_active });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败');
    }
  };

  if (loading) {
    return (
      <section className="page">
        <h1>{t('subAccounts')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  // 分离待审核与已审核/已创建的子账号
  const pendingIds = new Set(pending.map((p) => p.id));
  const approvedAccounts = accounts.filter((a) => !pendingIds.has(a.id));

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>
          {t('subAccounts')}
          {pending.length > 0 && (
            <span className="pending-count-badge">{pending.length} 个待审核</span>
          )}
        </h1>
        <button className="btn btn-submit" onClick={() => setShowCreate(true)}>
          + {t('createSubAccount')}
        </button>
      </div>
      <p className="card-desc">{t('subAccountsDesc')}</p>

      {error && <p className="error-text">{error}</p>}
      {reviewError && <p className="error-text">{reviewError}</p>}

      {/* ===== 待审核申请区 ===== */}
      {pending.length > 0 && (
        <div className="section-block pending-section">
          <h3 className="section-title">
            <span className="pending-icon">⏳</span>
            待审核的子账号申请
            <span className="pending-count">（{pending.length}）</span>
          </h3>
          <div className="grid">
            {pending.map((sub) => (
              <div className="card card-pending" key={sub.id}>
                <div className="card-pending-badge">待审核</div>
                <strong>{sub.full_name || sub.username}</strong>
                <div className="card-meta">
                  <span>@{sub.username}</span> · <span>{sub.email}</span>
                </div>
                <div className="card-meta">
                  申请于{' '}
                  {sub.created_at ? new Date(sub.created_at).toLocaleString('zh-CN') : 'N/A'}
                </div>
                <div className="sub-actions">
                  <button
                    className="btn btn-sm btn-submit"
                    onClick={() => handleApprove(sub)}
                  >
                    同意
                  </button>
                  <button
                    className="btn btn-sm btn-cancel"
                    onClick={() => handleReject(sub)}
                  >
                    拒绝
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===== 已创建/已同意的子账号列表 ===== */}
      <h3 className="section-title">
        子账号列表
        <span className="sub-count">（{approvedAccounts.length}）</span>
      </h3>

      {approvedAccounts.length === 0 ? (
        <div className="card">
          <p>{t('noSubAccounts')}</p>
        </div>
      ) : (
        <div className="grid">
          {approvedAccounts.map((acc) => {
            const isPending = acc.approval_status === 'pending' || pendingIds.has(acc.id);
            return (
              <div className={`card ${isPending ? 'card-pending' : ''}`} key={acc.id}>
                <strong>{acc.full_name || acc.username}</strong>
                <div className="card-meta">
                  <span>@{acc.username}</span> · <span>{acc.email}</span>
                </div>
                <div className="card-status">
                  {ROLE_LABELS[acc.role] ?? acc.role}
                  {isPending ? (
                    <span className="sub-active pending">待审核</span>
                  ) : (
                    <span className={`sub-active ${acc.is_active ? 'ok' : 'off'}`}>
                      {acc.is_active ? '启用' : '停用'}
                    </span>
                  )}
                </div>
                <div className="card-meta">
                  {isPending
                    ? `申请于 ${acc.created_at ? new Date(acc.created_at).toLocaleString('zh-CN') : 'N/A'}`
                    : `创建于 ${acc.created_at ? new Date(acc.created_at).toLocaleString('zh-CN') : 'N/A'}`}
                </div>
                <div className="sub-actions">
                  {isPending ? (
                    <>
                      <button
                        className="btn btn-sm btn-submit"
                        onClick={() => handleApprove(acc)}
                      >
                        同意
                      </button>
                      <button
                        className="btn btn-sm btn-cancel"
                        onClick={() => handleReject(acc)}
                      >
                        拒绝
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="btn btn-sm"
                        onClick={() => handleToggleRole(acc)}
                        title={acc.role === 'viewer' ? '提升为可协作用户' : '降为只读'}
                      >
                        {acc.role === 'viewer' ? '设为协作' : '设为只读'}
                      </button>
                      <button
                        className={`btn btn-sm ${acc.is_active ? 'btn-cancel' : 'btn-submit'}`}
                        onClick={() => handleToggleActive(acc)}
                      >
                        {acc.is_active ? '停用' : '启用'}
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 创建子账号 */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{t('createSubAccount')}</h2>
            <div className="form-group">
              <label>{t('username')}</label>
              <input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="子账号用户名"
              />
            </div>
            <div className="form-group">
              <label>{t('email')}</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="user@example.com"
              />
            </div>
            <div className="form-group">
              <label>{t('password')}</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="至少 8 位"
              />
            </div>
            <div className="form-group">
              <label>{t('fullName')}</label>
              <input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="姓名（可选）"
              />
            </div>
            <div className="form-group">
              <label>{t('role')}</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                <option value="viewer">{t('roleViewer')}</option>
                <option value="user">{t('roleUser')}</option>
              </select>
              <p className="role-hint">子账号不支持管理员角色（仅协作/只读）</p>
            </div>
            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setShowCreate(false)}>
                {t('cancel')}
              </button>
              <button
                className="btn btn-submit"
                onClick={handleCreate}
                disabled={creating || !form.username || !form.email || form.password.length < 8}
              >
                {creating ? '创建中...' : t('create')}
              </button>
            </div>
            {createError && (
              <div className="modal-error">
                <strong>错误：</strong> {createError}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}