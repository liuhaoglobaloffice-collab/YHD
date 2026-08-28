import { useEffect, useState } from 'react';
import {
  addLeadActivity, createLead, deleteLead, exportLeadsCsv,
  fetchCustoms, fetchLeadDetail, fetchLeads, fetchLeadStats,
  generateQuotation, runAcquisition, searchCustoms, updateLead,
  type CustomsRecord, type LeadActivity, type LeadDetail,
  type LeadItem, type LeadStats, type Quotation,
} from '../services/crm';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';
import { AIWorkStatus, type AIStatus } from '../components/AIWorkStatus';
import { AIEmptyState } from '../components/AIEmptyState';

const STATUS_ORDER = ['new', 'contacted', 'qualified', 'proposal', 'won', 'lost'];
const STATUS_LABELS: Record<string, string> = {
  new: '新线索',
  contacted: '已联系',
  qualified: '已确认意向',
  proposal: '方案/报价中',
  won: '成交',
  lost: '流失',
};
const ACTIVITY_LABELS: Record<string, string> = {
  call: '电话',
  email: '邮件',
  message: '消息',
  meeting: '会议',
  note: '备注',
};

export function LeadsPage() {
  const { t } = useI18n();
  const readonly = isReadonly();

  // 统计
  const [stats, setStats] = useState<LeadStats | null>(null);
  // 线索列表
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [onlyFollowUp, setOnlyFollowUp] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [error, setError] = useState('');

  // 获客引擎
  const [sources, setSources] = useState<string[]>(['social', 'google', 'customs']);
  const [keywords, setKeywords] = useState('');
  const [acquiring, setAcquiring] = useState(false);
  const [acquireResult, setAcquireResult] = useState<{
    leads: Array<Record<string, unknown> & { name: string }>;
    stats: Record<string, number>;
    saved: { created: number; skipped: number };
  } | null>(null);

  // 手动添加
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState(false);

  // 详情
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [activityForm, setActivityForm] = useState({ activity_type: 'note', content: '', result: '', next_follow_up_at: '' });
  // 报价单
  const [quoteQty, setQuoteQty] = useState('');
  const [quotation, setQuotation] = useState<Quotation | null>(null);
  const [quoteError, setQuoteError] = useState('');

  // 海关
  const [customs, setCustoms] = useState<CustomsRecord[]>([]);
  const [customsProduct, setCustomsProduct] = useState('');
  const [searchingCustoms, setSearchingCustoms] = useState(false);

  const loadAll = async () => {
    try {
      const [s, l] = await Promise.all([
        fetchLeadStats(),
        fetchLeads({ status: statusFilter || undefined, follow_up: onlyFollowUp, keyword: keyword || undefined, page_size: 50 }),
      ]);
      setStats(s);
      setLeads(l.items);
    } catch (e) {
      console.error(e);
      setError('加载线索失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadLeads = async (override?: { status?: string; follow_up?: boolean }) => {
    try {
      const st = override?.status ?? statusFilter;
      const fu = override?.follow_up ?? onlyFollowUp;
      const [s, l] = await Promise.all([
        fetchLeadStats(),
        fetchLeads({ status: st || undefined, follow_up: fu, keyword: keyword || undefined, page_size: 50 }),
      ]);
      setStats(s);
      setLeads(l.items);
    } catch (e) {
      console.error(e);
      setError('加载线索失败');
    }
  };

  const toggleSource = (s: string) => {
    setSources((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  };

  const handleAcquire = async () => {
    setAcquiring(true);
    setError('');
    try {
      const kw = keywords.split(/[,，\n]/).map((x) => x.trim()).filter(Boolean);
      const result = await runAcquisition({
        sources,
        keywords: kw.length ? kw : undefined,
        limit: 10,
        save_to_pool: true,
      });
      setAcquireResult(result);
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : '获客失败');
    }
    setAcquiring(false);
  };

  const handleAdd = async () => {
    setAdding(true);
    try {
      await createLead({ ...addForm, source: 'manual' });
      setShowAdd(false);
      setAddForm({});
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败');
    }
    setAdding(false);
  };

  const openDetail = async (leadId: number) => {
    try {
      const d = await fetchLeadDetail(leadId);
      setDetail(d);
      setQuotation(null);
      setQuoteQty('');
      setQuoteError('');
      setActivityForm({ activity_type: 'note', content: '', result: '', next_follow_up_at: '' });
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载详情失败');
    }
  };

  const genQuote = async () => {
    if (!detail) return;
    try {
      const q = await generateQuotation(detail.id, {
        quantity: quoteQty ? Number(quoteQty) : undefined,
      });
      setQuotation(q);
      setQuoteError('');
    } catch (e) {
      setQuoteError(e instanceof Error ? e.message : '生成报价单失败');
    }
  };

  const copyQuote = async (q: Quotation) => {
    const lines = [
      `QUOTATION 报价单 · ${q.valid_until || ''}`,
      `客户：${q.company || ''}（${q.country || ''}）`,
      `联系人：${q.contact || ''}${q.email ? ` / ${q.email}` : ''}${q.whatsapp ? ` / ${q.whatsapp}` : ''}`,
      `产品：${q.product || '产品待确认'}`,
      `数量：${q.quantity}  ${q.moq ? `MOQ：${q.moq}` : ''}`,
      `单价：${q.currency} ${q.unit_price ?? '待确认'}${q.freight ? `  运费：${q.currency} ${q.freight}` : ''}`,
      `总额：${q.currency} ${q.total.toLocaleString()}`,
      `交期：${q.lead_time}   付款：${q.payment}`,
      `有效期：${q.valid_until}`,
    ].join('\n');
    try {
      await navigator.clipboard.writeText(lines);
      setQuoteError('已复制到剪贴板');
    } catch {
      setQuoteError('');
    }
  };

  const handleStatusChange = async (leadId: number, status: string) => {
    try {
      await updateLead(leadId, { status });
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败');
    }
  };

  const handleAddActivity = async () => {
    if (!detail || !activityForm.content.trim()) return;
    try {
      await addLeadActivity(detail.id, {
        activity_type: activityForm.activity_type,
        content: activityForm.content.trim(),
        result: activityForm.result.trim() || undefined,
        next_follow_up_at: activityForm.next_follow_up_at || undefined,
      });
      setDetail(await fetchLeadDetail(detail.id));
      setActivityForm({ activity_type: 'note', content: '', result: '', next_follow_up_at: '' });
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : '添加跟进失败');
    }
  };

  const handleDelete = async (leadId: number) => {
    if (!confirm('确认删除该线索？')) return;
    try {
      await deleteLead(leadId);
      setDetail(null);
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败');
    }
  };

  const saveDealInfo = async (d: LeadDetail) => {
    try {
      await updateLead(d.id, {
        quote_amount: d.quote_amount ?? undefined,
        won_amount: d.won_amount ?? undefined,
        expected_close_at: d.expected_close_at || undefined,
        lost_reason: d.lost_reason?.trim() || undefined,
      });
      setDetail(await fetchLeadDetail(d.id));
      loadLeads();
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    }
  };

  const handleCustomsSearch = async () => {
    setSearchingCustoms(true);
    try {
      const r = await searchCustoms({ product: customsProduct || undefined, save: true });
      setCustoms(r.records);
    } catch (e) {
      setError(e instanceof Error ? e.message : '海关查询失败');
    }
    setSearchingCustoms(false);
  };

  if (loading) {
    return (
      <section className="page">
        <h1>AI 销售团队</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  if (error && leads.length === 0) {
    return (
      <section className="page">
        <h1>AI 销售团队</h1>
        <AIEmptyState isError errorMessage={error} onRetry={loadAll} />
      </section>
    );
  }

  return (
    <section className="page">
      <h1>AI 销售团队</h1>

      {/* AI 团队状态 */}
      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card" style={{ borderLeft: '3px solid #4cc9f0' }}>
          <div className="cost-label">AI 客户发现</div>
          <div className="cost-value" style={{ color: '#4cc9f0' }}>{stats?.total ?? 0}</div>
          <div className="cost-sub">线索总数</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #4ade80' }}>
          <div className="cost-label">AI 评分状态</div>
          <div className="cost-value" style={{ color: '#4ade80' }}>{stats?.ai_scored ?? 0}</div>
          <div className="cost-sub">AI 已评分</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #facc15' }}>
          <div className="cost-label">待跟进客户</div>
          <div className="cost-value" style={{ color: '#facc15' }}>{stats?.follow_up ?? 0}</div>
          <div className="cost-sub">需联系</div>
        </div>
        <div className="card" style={{ borderLeft: '3px solid #ff6b6b' }}>
          <div className="cost-label">流失客户</div>
          <div className="cost-value" style={{ color: '#ff6b6b' }}>{stats?.lost ?? 0}</div>
          <div className="cost-sub">已流失</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button className="btn btn-sm" onClick={exportLeadsCsv}>
          导出 CSV
        </button>
        {!readonly && (
          <button className="btn btn-submit" onClick={() => setShowAdd(true)}>
            + {t('addLead')}
          </button>
        )}
      </div>
      <p className="card-desc">{t('leadPoolDesc')}</p>

      {error && <p className="error-text">{error}</p>}

      {/* 统计卡片 */}
      {stats && (
        <div className="grid">
          <div className="card">
            <strong>{t('totalLeads')}</strong>
            <div className="card-value">{stats.total}</div>
          </div>
          <div className="card">
            <strong>{t('followUpDue')}</strong>
            <div className="card-value">{stats.follow_up_due}</div>
            <div className="card-meta">{t('needsFollowUp')}</div>
          </div>
          <div className="card">
            <strong>{t('winnedLeads')}</strong>
            <div className="card-value">{stats.by_status.won ?? 0}</div>
            <div className="card-meta">{stats.win_rate}% 成交率</div>
          </div>
          <div className="card">
            <strong>{t('estimatedValue')}</strong>
            <div className="card-value">{Math.round(stats.total_estimated_value).toLocaleString()}</div>
            <div className="card-meta">USD</div>
          </div>
        </div>
      )}

      {/* 销售漏斗（询盘转化，点击阶段筛选） */}
      {stats && stats.stages && stats.stages.length > 0 && (
        <div className="card funnel-panel" style={{ marginTop: 16 }}>
          <div className="cost-label" style={{ marginBottom: 10 }}>
            销售漏斗（点击阶段筛选列表）
          </div>
          <div className="funnel-row">
            {stats.stages.map((s) => (
              <button
                key={s.status}
                className={`funnel-stage st-${s.status} ${statusFilter === s.status ? 'active' : ''}`}
                onClick={() => {
                  const next = statusFilter === s.status ? '' : s.status;
                  setStatusFilter(next);
                  loadLeads({ status: next });
                }}
                title={`${STATUS_LABELS[s.status]}：${s.count} 个（${s.rate}%）`}
              >
                <span className="funnel-stage-label">{STATUS_LABELS[s.status]}</span>
                <span className="funnel-stage-count">{s.count}</span>
                <span className="funnel-stage-rate">{s.rate}%</span>
              </button>
            ))}
          </div>
          <div className="funnel-meta">
            <span>预估值 ${Math.round(stats.total_estimated_value).toLocaleString()}</span>
            <span>报价总额 ${Math.round(stats.quote_total).toLocaleString()}</span>
            <span>成交总额 ${Math.round(stats.won_total).toLocaleString()}</span>
            {Object.keys(stats.lost_by_reason).length > 0 && (
              <span className="funnel-lost">
                流失原因：
                {Object.entries(stats.lost_by_reason)
                  .map(([r, c]) => `${r}×${c}`)
                  .join('、')}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 获客引擎（子账号只读隐藏） */}
      {!readonly && (
        <div className="import-panel">
        <div className="executions-header">
          <strong>{t('acquisitionEngine')}</strong>
          <span className="executions-count">{t('acquisitionEngineDesc')}</span>
        </div>
        <div className="acquire-controls">
          <div className="source-checkboxes">
            {[
              { v: 'social', label: '社媒' },
              { v: 'google', label: '谷歌搜索' },
              { v: 'customs', label: '海关数据' },
            ].map((s) => (
              <label key={s.v} className={`source-check ${sources.includes(s.v) ? 'on' : ''}`}>
                <input
                  type="checkbox"
                  checked={sources.includes(s.v)}
                  onChange={() => toggleSource(s.v)}
                />
                {s.label}
              </label>
            ))}
          </div>
          <input
            className="acquire-keywords"
            placeholder="关键词（逗号分隔，可选）"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
          <button className="btn btn-submit" onClick={handleAcquire} disabled={acquiring || sources.length === 0}>
            {acquiring ? '挖掘中...' : t('runAcquisition')}
          </button>
        </div>

        {acquireResult && (
          <div className="acquire-result">
            <div className="execution-item-sub">
              <span className="ok">获客成功</span>
              <span>
                社媒 {acquireResult.stats.social ?? 0} · 谷歌 {acquireResult.stats.google ?? 0} · 海关 {acquireResult.stats.customs ?? 0}
              </span>
              <span>已入库 {acquireResult.saved.created} · 跳过重复 {acquireResult.saved.skipped}</span>
            </div>
            <div className="acquire-lead-list">
              {acquireResult.leads.map((l, i) => (
                <div key={i} className="acquire-lead-item">
                  <span className="contact-name">{l.name}</span>
                  <span className="contact-phone">
                    {l.company} · {l.country}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      )}

      {/* 线索池 */}
      <div className="executions-panel">
        <div className="executions-header">
          <strong>{t('leadPool')}</strong>
          <div className="workbench-actions">
            <select value={statusFilter} onChange={(e) => { const v = e.target.value; setStatusFilter(v); loadLeads({ status: v }); }}>
              <option value="">全部状态</option>
              {STATUS_ORDER.map((s) => (
                <option key={s} value={s}>{STATUS_LABELS[s]}</option>
              ))}
            </select>
            <input
              className="lead-search"
              placeholder="搜索名称/公司/邮箱"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadLeads()}
            />
            <button className="btn btn-sm" onClick={() => { const next = !onlyFollowUp; setOnlyFollowUp(next); loadLeads({ follow_up: next }); }}>
              {onlyFollowUp ? '全部线索' : '仅待跟进'}
            </button>
            <button className="btn btn-sm" onClick={loadLeads}>刷新</button>
          </div>
        </div>

        {leads.length === 0 ? (
          <AIEmptyState
            title="AI 销售团队已就绪"
            description="等待启动客户开发任务。可通过 AI 自动获客或手动添加线索。"
            aiStatus="waiting"
            availableTasks={['启动 AI 自动获客', '手动添加客户线索', '查询海关数据']}
            nextStep="建议先输入关键词启动 AI 获客引擎"
            actionLabel="开始客户开发"
            onAction={() => document.querySelector<HTMLInputElement>('[class*="composer"]')?.focus()}
          />
        ) : (
          <div className="leads-list">
            {leads.map((lead) => (
              <div key={lead.id} className={`lead-item st-${lead.status}`}>
                <div className="execution-item-main">
                  <span className="execution-employee" onClick={() => openDetail(lead.id)}>
                    {lead.name}
                  </span>
                  <span className="lead-company">{lead.company}</span>
                  <span className={`lead-badge src-${lead.source}`}>{lead.source_label}</span>
                  <span className={`execution-status st-${lead.status}`}>{lead.status_label}</span>
                  <span className="lead-score">{lead.score}</span>
                </div>
                <div className="execution-item-sub">
                  <span>
                    {lead.country || ''} {lead.product_interest ? `· ${lead.product_interest}` : ''}
                  </span>
                  <span className="lead-actions">
                    <select
                      value={lead.status}
                      onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {STATUS_ORDER.map((s) => (
                        <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                      ))}
                    </select>
                    {lead.next_follow_up_at && (
                      <span className="lead-followup">
                        跟进 {new Date(lead.next_follow_up_at).toLocaleDateString()}
                      </span>
                    )}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 海关数据（子账号只读隐藏） */}
      {!readonly && (
        <div className="import-panel">
        <div className="executions-header">
          <strong>{t('customsData')}</strong>
        </div>
        <div className="composer-row">
          <input
            placeholder="商品关键词（如 LED）"
            value={customsProduct}
            onChange={(e) => setCustomsProduct(e.target.value)}
          />
          <button className="btn btn-submit" onClick={handleCustomsSearch} disabled={searchingCustoms}>
            {searchingCustoms ? '查询中...' : t('searchCustoms')}
          </button>
        </div>
        {customs.length > 0 && (
          <div className="customs-list">
            {customs.map((c, i) => (
              <div key={c.id ?? i} className="customs-item">
                <div className="execution-item-main">
                  <span className="execution-employee">{c.product}</span>
                  <span className="lead-badge">{c.hs_code}</span>
                </div>
                <div className="execution-item-sub">
                  <span>进口商：{c.importer_name}（{c.importer_country}）</span>
                  <span>出口商：{c.exporter_name}（{c.exporter_country}）</span>
                  <span>{c.quantity} {c.unit} · ${c.value?.toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {/* 手动添加 */}
      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{t('addLead')}</h2>
            <div className="form-group">
              <label>名称 *</label>
              <input value={addForm.name ?? ''} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} />
            </div>
            <div className="form-group">
              <label>公司</label>
              <input value={addForm.company ?? ''} onChange={(e) => setAddForm({ ...addForm, company: e.target.value })} />
            </div>
            <div className="form-group">
              <label>国家</label>
              <input value={addForm.country ?? ''} onChange={(e) => setAddForm({ ...addForm, country: e.target.value })} />
            </div>
            <div className="form-group">
              <label>邮箱</label>
              <input value={addForm.email ?? ''} onChange={(e) => setAddForm({ ...addForm, email: e.target.value })} />
            </div>
            <div className="form-group">
              <label>WhatsApp</label>
              <input value={addForm.whatsapp ?? ''} onChange={(e) => setAddForm({ ...addForm, whatsapp: e.target.value })} />
            </div>
            <div className="form-group">
              <label>感兴趣产品</label>
              <input value={addForm.product_interest ?? ''} onChange={(e) => setAddForm({ ...addForm, product_interest: e.target.value })} />
            </div>
            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setShowAdd(false)}>{t('cancel')}</button>
              <button className="btn btn-submit" onClick={handleAdd} disabled={adding || !addForm.name?.trim()}>
                {adding ? '创建中...' : t('create')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 线索详情 */}
      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-actions-start">
              <h2>
                {detail.name}
                <span className={`lead-badge src-${detail.source}`}>{detail.source_label}</span>
              </h2>
              {!readonly && (
                <button className="btn btn-sm btn-cancel" onClick={() => handleDelete(detail.id)}>删除</button>
              )}
              </div>
            <p className="modal-meta">
              {detail.company} · {detail.country} {detail.city ? `· ${detail.city}` : ''} · {detail.industry || ''}
            </p>
            <div className="modal-meta">
              邮箱：{detail.email || '-'} · WhatsApp：{detail.whatsapp || '-'} · 电话：{detail.phone || '-'}
            </div>
            <div className="modal-meta">感兴趣：{detail.product_interest || '-'} · 评分 {detail.score}</div>

            {!readonly && (
              <div className="form-group">
                <label>状态</label>
                <select
                  value={detail.status}
                  onChange={async (e) => {
                    await handleStatusChange(detail.id, e.target.value);
                    setDetail(await fetchLeadDetail(detail.id));
                  }}
                >
                {STATUS_ORDER.map((s) => (
                  <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                ))}
              </select>
              </div>
            )}

            {!readonly && (
              <div className="form-group">
                <label>报价 / 成交信息（询盘漏斗）</label>
                <div className="composer-row">
                  <input
                    type="number"
                    min="0"
                    placeholder="报价金额（USD）"
                    value={detail.quote_amount ?? ''}
                    onChange={(e) =>
                      setDetail({ ...detail, quote_amount: e.target.value ? Number(e.target.value) : null })
                    }
                  />
                  <input
                    type="number"
                    min="0"
                    placeholder="成交金额（USD）"
                    value={detail.won_amount ?? ''}
                    onChange={(e) =>
                      setDetail({ ...detail, won_amount: e.target.value ? Number(e.target.value) : null })
                    }
                  />
                </div>
                <div className="composer-row" style={{ marginTop: 6 }}>
                  <input
                    type="date"
                    placeholder="预计成交日"
                    value={detail.expected_close_at?.slice(0, 10) ?? ''}
                    onChange={(e) =>
                      setDetail({ ...detail, expected_close_at: e.target.value || null })
                    }
                  />
                  <input
                    placeholder="流失原因（如：价格过高）"
                    value={detail.lost_reason ?? ''}
                    onChange={(e) => setDetail({ ...detail, lost_reason: e.target.value })}
                  />
                </div>
                <button
                  className="btn btn-sm btn-submit"
                  style={{ marginTop: 8 }}
                  onClick={() => saveDealInfo(detail)}
                >
                  保存报价信息
                </button>
              </div>
            )}

            {!readonly && (
              <div className="form-group">
                <label>报价单（一键生成，可复制发给客户）</label>
                <div className="composer-row">
                  <input
                    type="number"
                    min="1"
                    placeholder="数量（默认 1）"
                    value={quoteQty}
                    onChange={(e) => setQuoteQty(e.target.value)}
                  />
                  <button className="btn btn-sm btn-submit" onClick={genQuote} disabled={!detail.product_interest && !detail.quote_amount}>
                    生成报价单
                  </button>
                </div>
                {quoteError && <div className="activity-result">{quoteError}</div>}
                {quotation && (
                  <div className="quotation-card">
                    <div className="quotation-row">
                      <span>客户</span>
                      <strong>
                        {quotation.company || quotation.contact || '-'}（{quotation.country || '-'}）
                      </strong>
                    </div>
                    <div className="quotation-row">
                      <span>产品</span>
                      <strong>{quotation.product || '产品待确认'}</strong>
                    </div>
                    <div className="quotation-row">
                      <span>数量 / MOQ</span>
                      <strong>
                        {quotation.quantity} {quotation.moq ? `· MOQ ${quotation.moq}` : ''}
                      </strong>
                    </div>
                    <div className="quotation-row">
                      <span>单价 / 总额</span>
                      <strong>
                        {quotation.currency} {quotation.unit_price ?? '待确认'}
                        {quotation.freight ? ` + 运费 ${quotation.currency} ${quotation.freight}` : ''} · 总额{' '}
                        {quotation.currency} {Math.round(quotation.total).toLocaleString()}
                      </strong>
                    </div>
                    <div className="quotation-row">
                      <span>交期 / 付款</span>
                      <strong>
                        {quotation.lead_time} · {quotation.payment}
                      </strong>
                    </div>
                    <div className="quotation-row">
                      <span>有效期</span>
                      <strong>至 {quotation.valid_until}</strong>
                    </div>
                    {quotation.missing_fields.length > 0 && (
                      <div className="activity-result" style={{ marginTop: 8 }}>
                        提示：缺少 {quotation.missing_fields.join('、')}，请补充后再发给客户
                      </div>
                    )}
                    <button className="btn btn-sm" style={{ marginTop: 10 }} onClick={() => copyQuote(quotation)}>
                      复制报价单
                    </button>
                  </div>
                )}
              </div>
            )}

            <div className="executions-header">
              <strong>跟进记录</strong>
              <span className="executions-count">{detail.activities.length} 条</span>
            </div>
            <div className="activity-list">
              {detail.activities.length === 0 ? (
                <p className="executions-empty">暂无跟进记录</p>
              ) : (
                detail.activities.map((a: LeadActivity) => (
                  <div key={a.id} className="activity-item">
                    <div className="execution-item-main">
                      <span className="execution-employee">{ACTIVITY_LABELS[a.activity_type] ?? a.activity_type}</span>
                      <span className="execution-time">{new Date(a.created_at).toLocaleString()}</span>
                    </div>
                    <div className="execution-item-sub">{a.content}</div>
                    {a.result && <div className="activity-result">结果：{a.result}</div>}
                  </div>
                ))
              )}
            </div>

            {!readonly && (
              <>
                <div className="executions-header">
                  <strong>添加跟进</strong>
                </div>
                <div className="composer-row">
                  <select
                    value={activityForm.activity_type}
                    onChange={(e) => setActivityForm({ ...activityForm, activity_type: e.target.value })}
                  >
                    {Object.entries(ACTIVITY_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                  <input
                    placeholder="下次跟进日期（可选，YYYY-MM-DD）"
                    type="date"
                    value={activityForm.next_follow_up_at}
                    onChange={(e) => setActivityForm({ ...activityForm, next_follow_up_at: e.target.value })}
                  />
                </div>
                <div className="composer-row" style={{ marginTop: 8 }}>
                  <textarea
                    rows={2}
                    placeholder="跟进内容..."
                    value={activityForm.content}
                    onChange={(e) => setActivityForm({ ...activityForm, content: e.target.value })}
                  />
                  <input
                    placeholder="结果（可选）"
                    value={activityForm.result}
                    onChange={(e) => setActivityForm({ ...activityForm, result: e.target.value })}
                  />
                </div>
                <div className="modal-actions">
                  <button className="btn btn-cancel" onClick={() => setDetail(null)}>{t('cancel')}</button>
                  <button className="btn btn-submit" onClick={handleAddActivity} disabled={!activityForm.content.trim()}>
                    添加跟进
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
