import { useEffect, useState } from 'react';
import {
  fetchSubAccounts,
  fetchSubBudgets,
  fetchSubDataSummary,
  fetchPendingApprovals,
  approveSubAccount,
  rejectSubAccount,
  type SubAccount,
  type SubBudget,
  type SubDataSummary,
} from '../services/accounts';
import { createLead } from '../services/crm';
import { useI18n } from '../i18n';

const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000';
const API_PREFIX = '/api/v1';

function token(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

const DOMAIN_LABELS: Record<string, string> = {
  marketing: '营销',
  sales: '销售',
  operations: '运营',
  research: '调研',
  general: '通用',
};

/** 主账号：子账号数据管理台（只读数据摘要 + 代建线索/任务） */
export function SubAccountManagementPage() {
  const { t } = useI18n();
  const [accounts, setAccounts] = useState<SubAccount[]>([]);
  const [budgets, setBudgets] = useState<SubBudget[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [summary, setSummary] = useState<SubDataSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');
  const [detailError, setDetailError] = useState('');

  // 代建模式：lead | task
  const [mode, setMode] = useState<'lead' | 'task'>('lead');
  // 代建线索表单
  const [leadForm, setLeadForm] = useState({ name: '', company: '', country: '', phone: '', email: '', whatsapp: '', notes: '' });
  // 代建任务表单
  const [taskForm, setTaskForm] = useState({ domain: 'marketing', title: '', description: '', priority: 'medium' });
  // 代建预算（编辑子账号预算）
  const [budgetEdits, setBudgetEdits] = useState<Record<number, string>>({});
  const [savingBudget, setSavingBudget] = useState<number | null>(null);
  const [banner, setBanner] = useState('');
  // 待审核
  const [pending, setPending] = useState<SubAccount[]>([]);
  const [pendingLoading, setPendingLoading] = useState(false);

  const loadAccounts = async () => {
    try {
      const data = await fetchSubAccounts();
      setAccounts(data.sub_accounts);
      const b = await fetchSubBudgets().catch(() => null);
      if (b) setBudgets(b.items);
    } catch (e) {
      setError('加载子账号列表失败');
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAccounts();
    loadPending();
  }, []);

  const loadPending = async () => {
    setPendingLoading(true);
    try {
      setPending(await fetchPendingApprovals().then(r => r.sub_accounts));
    } catch { /* ignore */ }
    setPendingLoading(false);
  };

  const loadSummary = async (subId: number) => {
    setSelectedId(subId);
    setDetailLoading(true);
    setDetailError('');
    try {
      setSummary(await fetchSubDataSummary(subId));
    } catch (e) {
      setDetailError('加载子账号数据失败');
      console.error(e);
    }
    setDetailLoading(false);
  };

  const budgetOf = (subId: number): SubBudget | undefined => budgets.find((b) => b.user_id === subId);

  const handleSaveBudget = async (subId: number) => {
    const raw = budgetEdits[subId];
    const value = Number.parseFloat(raw ?? '');
    if (Number.isNaN(value) || value < 0) {
      setBanner('预算必须是 >= 0 的数字');
      return;
    }
    setSavingBudget(subId);
    setBanner('');
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/accounts/sub-accounts/${subId}/budget`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ monthly_budget: value }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `设置失败: ${res.status}`);
      }
      const updated = await res.json();
      setBudgets((prev) =>
        prev.map((b) => (b.user_id === subId ? { ...b, ...updated } : b))
      );
      setBanner(`已保存子账号「${accounts.find((a) => a.id === subId)?.username}」月度预算`);
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '保存失败');
    }
    setSavingBudget(null);
  };

  const handleCreateLead = async () => {
    if (!leadForm.name.trim()) {
      setBanner('线索名称必填');
      return;
    }
    if (selectedId == null) {
      setBanner('请先选择子账号');
      return;
    }
    setBanner('');
    try {
      await createLead({
        name: leadForm.name.trim(),
        company: leadForm.company || undefined,
        country: leadForm.country || undefined,
        phone: leadForm.phone || undefined,
        email: leadForm.email || undefined,
        whatsapp: leadForm.whatsapp || undefined,
        notes: leadForm.notes || undefined,
        owner_user_id: selectedId,
      });
      setLeadForm({ name: '', company: '', country: '', phone: '', email: '', whatsapp: '', notes: '' });
      setBanner('代建线索成功，已出现在子账号工作台');
      loadSummary(selectedId);
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '代建线索失败');
    }
  };

  const handleCreateTask = async () => {
    if (!taskForm.title.trim() || !taskForm.description.trim()) {
      setBanner('任务标题和描述必填');
      return;
    }
    if (selectedId == null) {
      setBanner('请先选择子账号');
      return;
    }
    setBanner('');
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/business/tasks`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: taskForm.domain,
          title: taskForm.title.trim(),
          description: taskForm.description.trim(),
          priority: taskForm.priority,
          owner_user_id: selectedId,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `创建失败: ${res.status}`);
      }
      setTaskForm({ domain: 'marketing', title: '', description: '', priority: 'medium' });
      setBanner('代建业务任务成功，已出现在子账号工作台');
    } catch (e) {
      setBanner(e instanceof Error ? e.message : '代建任务失败');
    }
  };

  if (loading) return <div className="page-loading">{t('loading')}...</div>;

  return (
    <div className="sub-mgmt-page">
      <div className="page-header">
        <h1>
          {t('subAccountMgmt' as never)}
          {pending.length > 0 && (
            <span className="pending-count-badge">{pending.length} 个待审核</span>
          )}
        </h1>
        <p>主账号视角：只读查看子账号数据，并可为其代建线索 / 业务任务、调整 AI 预算。</p>
      </div>

      {error && <p className="error-text">{error}</p>}
      {banner && <div className="sub-mgmt-banner">{banner}</div>}

      {/* 待审核子账号申请 */}
      {pending.length > 0 && (
        <div className="pending-section" style={{ marginBottom: 16 }}>
          <h3 className="section-title">
            <span className="pending-icon">⏳</span>
            待审核的子账号申请
            <span className="pending-count">（{pending.length}）</span>
          </h3>
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
            {pending.map((p) => (
              <div className="card card-pending" key={p.id}>
                <div className="card-pending-badge">待审核</div>
                <strong>{p.full_name || p.username}</strong>
                <div className="card-meta">
                  <span>@{p.username}</span> · <span>{p.email}</span>
                </div>
                <div className="card-meta">
                  申请于 {p.created_at ? new Date(p.created_at).toLocaleString('zh-CN') : 'N/A'}
                </div>
                <div className="sub-actions" style={{ marginTop: 8 }}>
                  <button className="btn btn-sm btn-submit" onClick={async () => { await approveSubAccount(p.id); loadPending(); loadAccounts(); }}>
                    同意
                  </button>
                  <button className="btn btn-sm btn-cancel" onClick={async () => { await rejectSubAccount(p.id); loadPending(); }}>
                    拒绝
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="sub-mgmt-layout">
        {/* 左：子账号列表 */}
        <aside className="sub-mgmt-side">
          <div className="sub-mgmt-side-title">子账号</div>
          {accounts.length === 0 && <p className="sub-mgmt-empty">暂无子账号</p>}
          {accounts.map((acc) => {
            const b = budgetOf(acc.id);
            const active = selectedId === acc.id;
            const isPending = acc.approval_status === 'pending';
            return (
              <button
                key={acc.id}
                className={`sub-mgmt-acc ${active ? 'active' : ''} ${isPending ? 'pending' : ''}`}
                onClick={() => !isPending && loadSummary(acc.id)}
                style={isPending ? { opacity: 0.7 } : {}}
              >
                <div className="sub-mgmt-acc-head">
                  <strong>{acc.full_name || acc.username}</strong>
                  <span className={`sub-mgmt-badge ${b?.over_budget ? 'over' : ''}`}>
                    {isPending ? '待审核' : b?.over_budget ? '超预算' : acc.is_active ? '正常' : '停用'}
                  </span>
                </div>
                <div className="sub-mgmt-acc-sub">
                  {isPending
                    ? `申请于 ${acc.created_at ? new Date(acc.created_at).toLocaleString('zh-CN') : 'N/A'}`
                    : b
                      ? `本月 $${b.used_usd.toFixed(4)} / ${b.monthly_budget != null ? `$${b.monthly_budget}` : '不限'}`
                      : acc.email}
                </div>
              </button>
            );
          })}
        </aside>

        {/* 右：选中子账号详情 */}
        <main className="sub-mgmt-main">
          {selectedId == null && (
            <div className="sub-mgmt-placeholder">← 选择左侧子账号查看数据摘要</div>
          )}

          {selectedId != null && detailLoading && <div className="page-loading">加载中...</div>}

          {selectedId != null && !detailLoading && summary && (
            <>
              {/* 预算调整 */}
              <div className="card sub-mgmt-card">
                <div className="sub-mgmt-card-title">AI 预算（{summary.budget.month}）</div>
                <div className="sub-mgmt-budget-row">
                  <div>
                    已用 <strong>${summary.budget.used_usd.toFixed(4)}</strong>（{summary.budget.calls} 次调用）
                    {summary.budget.monthly_budget != null && (
                      <span> · 剩余 <strong>${summary.budget.remaining_usd?.toFixed(4)}</strong></span>
                    )}
                  </div>
                  <div className="sub-mgmt-budget-edit">
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      placeholder={summary.budget.monthly_budget != null ? String(summary.budget.monthly_budget) : '不限'}
                      value={budgetEdits[summary.user_id] ?? ''}
                      onChange={(e) => setBudgetEdits((s) => ({ ...s, [summary.user_id]: e.target.value }))}
                    />
                    <button
                      className="btn btn-sm btn-submit"
                      disabled={savingBudget === summary.user_id}
                      onClick={() => handleSaveBudget(summary.user_id)}
                    >
                      {savingBudget === summary.user_id ? '保存中...' : '保存预算'}
                    </button>
                  </div>
                </div>
              </div>

              {/* 数据摘要 */}
              <div className="sub-mgmt-stats">
                <div className="card sub-mgmt-stat">
                  <div className="cost-value">{summary.leads.total}</div>
                  <div className="cost-label">线索总数</div>
                  <div className="cost-sub">预估金额 ${summary.leads.total_estimated_value.toFixed(2)}</div>
                  <div className="sub-mgmt-status-map">
                    {Object.entries(summary.leads.by_status).map(([k, v]) => (
                      <span key={k}>{k}: {v}</span>
                    ))}
                  </div>
                </div>
                <div className="card sub-mgmt-stat">
                  <div className="cost-value">{summary.messages}</div>
                  <div className="cost-label">平台消息</div>
                </div>
                <div className="card sub-mgmt-stat">
                  <div className="cost-value">{summary.inquiries}</div>
                  <div className="cost-label">询价记录</div>
                </div>
                <div className="card sub-mgmt-stat">
                  <div className="cost-value">${summary.ai_cost.cost_usd.toFixed(4)}</div>
                  <div className="cost-label">本月 AI 成本</div>
                  <div className="cost-sub">{summary.ai_cost.calls} 次调用</div>
                </div>
              </div>

              {/* 代建入口 */}
              <div className="card sub-mgmt-card">
                <div className="sub-mgmt-card-title">为「{summary.username}」代建</div>
                <div className="sub-mgmt-mode-tabs">
                  <button className={`sub-mgmt-tab ${mode === 'lead' ? 'active' : ''}`} onClick={() => setMode('lead')}>
                    代建线索
                  </button>
                  <button className={`sub-mgmt-tab ${mode === 'task' ? 'active' : ''}`} onClick={() => setMode('task')}>
                    代建业务任务
                  </button>
                </div>

                {mode === 'lead' && (
                  <div className="sub-mgmt-form">
                    <div className="sub-mgmt-form-row">
                      <input placeholder="线索名称 *" value={leadForm.name} onChange={(e) => setLeadForm({ ...leadForm, name: e.target.value })} />
                      <input placeholder="公司" value={leadForm.company} onChange={(e) => setLeadForm({ ...leadForm, company: e.target.value })} />
                    </div>
                    <div className="sub-mgmt-form-row">
                      <input placeholder="国家/地区" value={leadForm.country} onChange={(e) => setLeadForm({ ...leadForm, country: e.target.value })} />
                      <input placeholder="电话" value={leadForm.phone} onChange={(e) => setLeadForm({ ...leadForm, phone: e.target.value })} />
                    </div>
                    <div className="sub-mgmt-form-row">
                      <input placeholder="邮箱" value={leadForm.email} onChange={(e) => setLeadForm({ ...leadForm, email: e.target.value })} />
                      <input placeholder="WhatsApp" value={leadForm.whatsapp} onChange={(e) => setLeadForm({ ...leadForm, whatsapp: e.target.value })} />
                    </div>
                    <input placeholder="备注" value={leadForm.notes} onChange={(e) => setLeadForm({ ...leadForm, notes: e.target.value })} />
                    <button className="btn btn-submit" onClick={handleCreateLead}>代建线索到子账号</button>
                  </div>
                )}

                {mode === 'task' && (
                  <div className="sub-mgmt-form">
                    <div className="sub-mgmt-form-row">
                      <select
                        value={taskForm.domain}
                        onChange={(e) => setTaskForm({ ...taskForm, domain: e.target.value })}
                      >
                        {Object.entries(DOMAIN_LABELS).map(([k, label]) => (
                          <option key={k} value={k}>{label}</option>
                        ))}
                      </select>
                      <select
                        value={taskForm.priority}
                        onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })}
                      >
                        <option value="low">低</option>
                        <option value="medium">中</option>
                        <option value="high">高</option>
                        <option value="urgent">紧急</option>
                      </select>
                    </div>
                    <input placeholder="任务标题 *" value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} />
                    <textarea placeholder="任务描述 *" rows={3} value={taskForm.description} onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })} />
                    <button className="btn btn-submit" onClick={handleCreateTask}>代建任务到子账号</button>
                  </div>
                )}
              </div>
            </>
          )}

          {selectedId != null && !detailLoading && detailError && (
            <div className="error-text">{detailError}</div>
          )}
        </main>
      </div>
    </div>
  );
}