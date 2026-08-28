import { useEffect, useState } from 'react';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';
import {
  fetchQuotes,
  fetchQuote,
  createQuote,
  updateQuoteStatus,
  sendQuote,
  STATUS_LABELS,
  STATUS_COLORS,
  type Quote,
  type QuoteItem,
} from '../services/quotes';
import { fetchLeads, type Lead } from '../services/crm';

const STATUS_FLOW: Record<string, string[]> = {
  draft: ['pending_approval'],
  pending_approval: ['approved', 'draft'],
  approved: ['sent'],
  sent: ['following_up', 'accepted', 'rejected'],
  following_up: ['accepted', 'rejected'],
};

export function QuotesPage() {
  const { t } = useI18n();
  const readonly = isReadonly();
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // 筛选
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // 选中详情
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null);

  // 创建表单
  const [showCreate, setShowCreate] = useState(false);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [createForm, setCreateForm] = useState({
    lead_id: '',
    lead_name: '',
    lead_company: '',
    lead_email: '',
    lead_phone: '',
    subject: '',
    currency: 'USD',
    discount: '0',
    tax_rate: '0',
    valid_days: '30',
    payment_terms: '',
    delivery_terms: '',
    notes: '',
  });
  const [items, setItems] = useState<QuoteItem[]>([
    { product_name: '', unit: '件', quantity: 1, unit_price: 0 },
  ]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  const loadQuotes = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchQuotes({
        status: statusFilter || undefined,
        q: searchQuery || undefined,
      });
      setQuotes(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    }
    setLoading(false);
  };

  const loadLeads = async () => {
    try {
      const data = await fetchLeads({ page_size: 100 });
      setLeads(data.items ?? []);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadQuotes();
    loadLeads();
  }, []);

  const handleSelect = async (id: number) => {
    setSelectedId(id);
    setError('');
    try {
      const data = await fetchQuote(id);
      setSelectedQuote(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载详情失败');
    }
  };

  const handleStatusUpdate = async (status: string) => {
    if (!selectedQuote) return;
    try {
      await updateQuoteStatus(selectedQuote.id, status);
      setSuccessMsg(`状态已更新为 ${STATUS_LABELS[status] ?? status}`);
      handleSelect(selectedQuote.id);
      loadQuotes();
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败');
    }
  };

  const handleSend = async (sendVia?: string) => {
    if (!selectedQuote) return;
    try {
      const result = await sendQuote(selectedQuote.id, sendVia);
      setSuccessMsg(`报价单 ${result.quote_number} 已通过 ${result.sent_via.join(', ') || '手动'} 发送`);
      handleSelect(selectedQuote.id);
      loadQuotes();
    } catch (e) {
      setError(e instanceof Error ? e.message : '发送失败');
    }
  };

  const handleLeadSelect = (leadId: string) => {
    const lead = leads.find((l) => l.id === Number(leadId));
    if (lead) {
      setCreateForm({
        ...createForm,
        lead_id: leadId,
        lead_name: lead.name,
        lead_company: lead.company ?? '',
        lead_email: lead.email ?? '',
        lead_phone: lead.phone ?? lead.whatsapp ?? '',
      });
    }
  };

  const handleCreate = async () => {
    if (!createForm.lead_name || !createForm.subject || items.length === 0) return;
    setCreating(true);
    setCreateError('');
    try {
      await createQuote({
        lead_id: createForm.lead_id ? Number(createForm.lead_id) : undefined,
        lead_name: createForm.lead_name,
        lead_company: createForm.lead_company || undefined,
        lead_email: createForm.lead_email || undefined,
        lead_phone: createForm.lead_phone || undefined,
        subject: createForm.subject,
        currency: createForm.currency,
        discount: Number(createForm.discount),
        tax_rate: Number(createForm.tax_rate),
        valid_days: Number(createForm.valid_days),
        payment_terms: createForm.payment_terms || undefined,
        delivery_terms: createForm.delivery_terms || undefined,
        notes: createForm.notes || undefined,
        items: items.filter((i) => i.product_name && i.unit_price > 0),
      });
      setShowCreate(false);
      setSuccessMsg('报价单创建成功');
      loadQuotes();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : '创建失败');
    }
    setCreating(false);
  };

  const addItem = () => {
    setItems([...items, { product_name: '', unit: '件', quantity: 1, unit_price: 0 }]);
  };

  const updateItem = (idx: number, field: keyof QuoteItem, value: string | number) => {
    const newItems = [...items];
    (newItems[idx] as Record<string, unknown>)[field] = value;
    setItems(newItems);
  };

  const removeItem = (idx: number) => {
    if (items.length > 1) setItems(items.filter((_, i) => i !== idx));
  };

  const calcTotal = (items: QuoteItem[]) => {
    const subtotal = items.reduce((s, i) => s + i.quantity * i.unit_price, 0);
    const discount = Number(createForm.discount);
    const taxRate = Number(createForm.tax_rate);
    const taxable = subtotal - discount;
    const tax = taxable * taxRate / 100;
    return { subtotal, tax, total: taxable + tax };
  };

  const formatAmount = (val: number, currency = 'USD') => {
    return `${currency} ${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>报价单管理</h1>
        {!readonly && (
          <button className="btn btn-submit" onClick={() => { setShowCreate(true); setCreateError(''); }}>
            + 新建报价单
          </button>
        )}
      </div>
      <p className="card-desc">管理外贸报价单，支持创建、审批、发送、跟进全流程。</p>

      {error && <p className="error-text">{error}</p>}
      {successMsg && <p className="ok-text">{successMsg}</p>}

      {/* 筛选 */}
      <div className="composer-row" style={{ marginBottom: 16, gap: 8 }}>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ flex: 1 }}>
          <option value="">全部状态</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <input
          placeholder="搜索报价单号/客户/主题..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && loadQuotes()}
          style={{ flex: 2 }}
        />
        <button className="btn btn-sm" onClick={loadQuotes} disabled={loading}>
          {loading ? '加载中...' : '筛选'}
        </button>
      </div>

      {/* 报价单列表 + 详情 */}
      <div className="inbox-layout" style={{ display: 'flex', gap: 16, minHeight: 500 }}>
        <div className="inbox-list" style={{ flex: 1, maxWidth: 380, overflowY: 'auto' }}>
          {loading ? (
            <div className="card"><p>加载中...</p></div>
          ) : quotes.length === 0 ? (
            <div className="card"><p>暂无报价单。点击"新建报价单"开始。</p></div>
          ) : (
            quotes.map((q) => (
              <div
                key={q.id}
                className={`card platform-card ${selectedId === q.id ? 'selected' : ''}`}
                style={{ cursor: 'pointer', marginBottom: 8, padding: 12 }}
                onClick={() => handleSelect(q.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <strong style={{ fontSize: 13, color: '#4cc9f0' }}>{q.quote_number}</strong>
                  <span className="ai-status-badge" style={{
                    color: STATUS_COLORS[q.status] ?? '#888',
                    background: `${STATUS_COLORS[q.status] ?? '#888'}15`,
                    fontSize: 10,
                  }}>
                    {STATUS_LABELS[q.status] ?? q.status}
                  </span>
                </div>
                <div style={{ fontSize: 13 }}>{q.subject}</div>
                <div className="card-meta" style={{ marginTop: 4 }}>
                  <span>{q.lead_name}</span>
                  <span>{formatAmount(q.total_amount, q.currency)}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* 详情 */}
        <div className="inbox-detail" style={{ flex: 2 }}>
          {!selectedQuote ? (
            <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
              <p style={{ color: '#888' }}>选择报价单查看详情</p>
            </div>
          ) : (
            <div className="card">
              <div className="executions-header">
                <strong style={{ color: '#4cc9f0' }}>{selectedQuote.quote_number}</strong>
                <span className="lead-badge" style={{
                  color: STATUS_COLORS[selectedQuote.status] ?? '#888',
                  background: `${STATUS_COLORS[selectedQuote.status] ?? '#888'}15`,
                }}>
                  {STATUS_LABELS[selectedQuote.status] ?? selectedQuote.status}
                </span>
              </div>

              <div style={{ marginTop: 12 }}>
                <div className="cost-label">客户信息</div>
                <div style={{ fontSize: 13, marginTop: 4 }}>
                  <div>名称: {selectedQuote.lead_name}</div>
                  {selectedQuote.lead_company && <div>公司: {selectedQuote.lead_company}</div>}
                  {selectedQuote.lead_email && <div>邮箱: {selectedQuote.lead_email}</div>}
                  {selectedQuote.lead_phone && <div>电话: {selectedQuote.lead_phone}</div>}
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <div className="cost-label">报价明细</div>
                <div style={{ fontSize: 13, marginTop: 4 }}>
                  <div>主题: {selectedQuote.subject}</div>
                  {selectedQuote.payment_terms && <div>付款条件: {selectedQuote.payment_terms}</div>}
                  {selectedQuote.delivery_terms && <div>交货条款: {selectedQuote.delivery_terms}</div>}
                  <div>有效期: {selectedQuote.valid_days} 天 (至 {selectedQuote.expires_at ? new Date(selectedQuote.expires_at).toLocaleDateString() : 'N/A'})</div>
                </div>
              </div>

              {/* 产品明细 */}
              {selectedQuote.items.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div className="cost-label">产品明细</div>
                  <table style={{ width: '100%', marginTop: 8, fontSize: 12, borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                        <th style={{ textAlign: 'left', padding: 4 }}>产品</th>
                        <th style={{ textAlign: 'right', padding: 4 }}>数量</th>
                        <th style={{ textAlign: 'right', padding: 4 }}>单价</th>
                        <th style={{ textAlign: 'right', padding: 4 }}>小计</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedQuote.items.map((item, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          <td style={{ padding: 4 }}>
                            {item.product_name}
                            {item.specification && <div style={{ color: '#888', fontSize: 11 }}>{item.specification}</div>}
                          </td>
                          <td style={{ textAlign: 'right', padding: 4 }}>{item.quantity} {item.unit}</td>
                          <td style={{ textAlign: 'right', padding: 4 }}>{formatAmount(item.unit_price, selectedQuote.currency)}</td>
                          <td style={{ textAlign: 'right', padding: 4 }}>{formatAmount(item.total_price, selectedQuote.currency)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr><td colSpan={3} style={{ textAlign: 'right', padding: 4, fontWeight: 600 }}>小计</td><td style={{ textAlign: 'right', padding: 4 }}>{formatAmount(selectedQuote.subtotal, selectedQuote.currency)}</td></tr>
                      {selectedQuote.discount > 0 && <tr><td colSpan={3} style={{ textAlign: 'right', padding: 4 }}>折扣</td><td style={{ textAlign: 'right', padding: 4 }}>-{formatAmount(selectedQuote.discount, selectedQuote.currency)}</td></tr>}
                      {selectedQuote.tax_rate > 0 && <tr><td colSpan={3} style={{ textAlign: 'right', padding: 4 }}>税率 {selectedQuote.tax_rate}%</td><td style={{ textAlign: 'right', padding: 4 }}>{formatAmount(selectedQuote.tax_amount, selectedQuote.currency)}</td></tr>}
                      <tr style={{ fontWeight: 700, borderTop: '2px solid rgba(255,255,255,0.2)' }}>
                        <td colSpan={3} style={{ textAlign: 'right', padding: 4 }}>总计</td>
                        <td style={{ textAlign: 'right', padding: 4, color: '#4cc9f0' }}>{formatAmount(selectedQuote.total_amount, selectedQuote.currency)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}

              {selectedQuote.notes && (
                <div style={{ marginTop: 12 }}>
                  <div className="cost-label">备注</div>
                  <div style={{ fontSize: 13, marginTop: 4, whiteSpace: 'pre-wrap' }}>{selectedQuote.notes}</div>
                </div>
              )}

              <div className="card-meta" style={{ marginTop: 12 }}>
                <span>创建: {selectedQuote.created_at ? new Date(selectedQuote.created_at).toLocaleString() : 'N/A'}</span>
                {selectedQuote.sent_at && <span>发送: {new Date(selectedQuote.sent_at).toLocaleString()}</span>}
              </div>

              {/* 操作按钮 */}
              {!readonly && (
                <div className="sub-actions" style={{ marginTop: 16, gap: 8, flexWrap: 'wrap' }}>
                  {/* 状态流转 */}
                  {(STATUS_FLOW[selectedQuote.status] ?? []).map((nextStatus) => (
                    <button
                      key={nextStatus}
                      className="btn btn-sm"
                      style={{ borderColor: STATUS_COLORS[nextStatus] ?? '#888' }}
                      onClick={() => handleStatusUpdate(nextStatus)}
                    >
                      → {STATUS_LABELS[nextStatus] ?? nextStatus}
                    </button>
                  ))}

                  {/* 发送操作 */}
                  {selectedQuote.status === 'approved' && (
                    <>
                      <button className="btn btn-sm btn-submit" onClick={() => handleSend('whatsapp')}>
                        📤 WhatsApp 发送
                      </button>
                      <button className="btn btn-sm" onClick={() => handleSend()}>
                        📤 标记已发送
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 新建报价单弹窗 */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => { if (!creating) setShowCreate(false); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 700 }}>
            <h2>新建报价单</h2>
            {createError && <p className="error-text">{createError}</p>}

            <div className="form-group">
              <label>选择已有客户</label>
              <select onChange={(e) => handleLeadSelect(e.target.value)} value={createForm.lead_id}>
                <option value="">手动输入客户信息</option>
                {leads.map((l) => (
                  <option key={l.id} value={l.id}>{l.name} {l.company ? `(${l.company})` : ''}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div className="form-group">
                <label>客户名称 *</label>
                <input value={createForm.lead_name} onChange={(e) => setCreateForm({ ...createForm, lead_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>公司</label>
                <input value={createForm.lead_company} onChange={(e) => setCreateForm({ ...createForm, lead_company: e.target.value })} />
              </div>
              <div className="form-group">
                <label>邮箱</label>
                <input value={createForm.lead_email} onChange={(e) => setCreateForm({ ...createForm, lead_email: e.target.value })} />
              </div>
              <div className="form-group">
                <label>电话</label>
                <input value={createForm.lead_phone} onChange={(e) => setCreateForm({ ...createForm, lead_phone: e.target.value })} />
              </div>
            </div>

            <div className="form-group">
              <label>报价主题 *</label>
              <input value={createForm.subject} onChange={(e) => setCreateForm({ ...createForm, subject: e.target.value })} placeholder="如: 5000件环保包装盒报价" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
              <div className="form-group">
                <label>币种</label>
                <select value={createForm.currency} onChange={(e) => setCreateForm({ ...createForm, currency: e.target.value })}>
                  <option value="USD">USD</option>
                  <option value="CNY">CNY</option>
                  <option value="EUR">EUR</option>
                </select>
              </div>
              <div className="form-group">
                <label>折扣</label>
                <input type="number" value={createForm.discount} onChange={(e) => setCreateForm({ ...createForm, discount: e.target.value })} />
              </div>
              <div className="form-group">
                <label>税率(%)</label>
                <input type="number" value={createForm.tax_rate} onChange={(e) => setCreateForm({ ...createForm, tax_rate: e.target.value })} />
              </div>
              <div className="form-group">
                <label>有效期(天)</label>
                <input type="number" value={createForm.valid_days} onChange={(e) => setCreateForm({ ...createForm, valid_days: e.target.value })} />
              </div>
            </div>

            <div className="form-group">
              <label>产品明细</label>
              {items.map((item, idx) => (
                <div key={idx} className="composer-row" style={{ gap: 4, marginTop: 4 }}>
                  <input
                    placeholder="产品名称"
                    value={item.product_name}
                    onChange={(e) => updateItem(idx, 'product_name', e.target.value)}
                    style={{ flex: 2 }}
                  />
                  <input
                    placeholder="数量"
                    type="number"
                    value={item.quantity}
                    onChange={(e) => updateItem(idx, 'quantity', Number(e.target.value))}
                    style={{ flex: 1, width: 60 }}
                  />
                  <input
                    placeholder="单价"
                    type="number"
                    value={item.unit_price}
                    onChange={(e) => updateItem(idx, 'unit_price', Number(e.target.value))}
                    style={{ flex: 1, width: 80 }}
                  />
                  <span style={{ fontSize: 12, color: '#888', width: 60, textAlign: 'right' }}>
                    {(item.quantity * item.unit_price).toFixed(2)}
                  </span>
                  <button className="btn btn-sm btn-cancel" onClick={() => removeItem(idx)} disabled={items.length === 1}>
                    ✕
                  </button>
                </div>
              ))}
              <button className="btn btn-sm" onClick={addItem} style={{ marginTop: 4 }}>+ 添加产品</button>

              <div style={{ marginTop: 8, fontSize: 13, textAlign: 'right' }}>
                {(() => { const t = calcTotal(items); return (
                  <>合计: {formatAmount(t.total, createForm.currency)} (税前: {formatAmount(t.subtotal, createForm.currency)}, 税: {formatAmount(t.tax, createForm.currency)})</>
                ); })()}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div className="form-group">
                <label>付款条件</label>
                <input value={createForm.payment_terms} onChange={(e) => setCreateForm({ ...createForm, payment_terms: e.target.value })} placeholder="如: T/T 30% deposit, 70% before shipment" />
              </div>
              <div className="form-group">
                <label>交货条款</label>
                <input value={createForm.delivery_terms} onChange={(e) => setCreateForm({ ...createForm, delivery_terms: e.target.value })} placeholder="如: FOB Shanghai, 30 days after order" />
              </div>
            </div>

            <div className="form-group">
              <label>备注</label>
              <textarea rows={2} value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />
            </div>

            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setShowCreate(false)} disabled={creating}>取消</button>
              <button className="btn btn-submit" onClick={handleCreate} disabled={creating || !createForm.lead_name || !createForm.subject || items.filter(i => i.product_name && i.unit_price > 0).length === 0}>
                {creating ? '创建中...' : '创建报价单'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}