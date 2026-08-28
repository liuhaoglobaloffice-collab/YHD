import { useEffect, useState } from 'react';
import {
  analyzeSupplier,
  compareInquiries,
  createInquiry,
  discoverSuppliers,
  fetchInquiries,
  fetchSupplierReports,
  type InquiryCompare,
  type SupplierInquiry,
  type SupplierReport,
} from '../services/crm';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';

const LEVEL_COLOR: Record<string, string> = {
  A: '#4ade80',
  B: '#4cc9f0',
  C: '#ffd54f',
  D: '#ff6b6b',
  低: '#4ade80',
  中: '#ffd54f',
  高: '#ff6b6b',
};

export function SupplierAnalysisPage() {
  const { t } = useI18n();
  const readonly = isReadonly();
  const [product, setProduct] = useState('');
  const [suppliers, setSuppliers] = useState<Array<Record<string, unknown> & { name: string }>>([]);
  const [discovering, setDiscovering] = useState(false);
  const [reports, setReports] = useState<SupplierReport[]>([]);
  const [current, setCurrent] = useState<SupplierReport | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [customSupplier, setCustomSupplier] = useState('');
  const [error, setError] = useState('');

  // 询价 / 比价（V3）
  const [inquiries, setInquiries] = useState<SupplierInquiry[]>([]);
  const [compare, setCompare] = useState<InquiryCompare | null>(null);
  const [compareProduct, setCompareProduct] = useState('');
  const [savingInquiry, setSavingInquiry] = useState(false);
  const [inquiryForm, setInquiryForm] = useState({
    supplier_name: '',
    product: '',
    quantity: '',
    unit_price: '',
    currency: 'USD',
    lead_time: '',
    payment: '',
    quality_note: '',
    note: '',
  });

  const loadInquiries = async () => {
    try {
      setInquiries(await fetchInquiries());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadReports();
    loadInquiries();
  }, []);

  const saveInquiry = async () => {
    if (!inquiryForm.supplier_name.trim() || !inquiryForm.product.trim()) return;
    setSavingInquiry(true);
    setError('');
    try {
      await createInquiry({
        supplier_name: inquiryForm.supplier_name.trim(),
        product: inquiryForm.product.trim(),
        quantity: inquiryForm.quantity ? Number(inquiryForm.quantity) : undefined,
        unit_price: inquiryForm.unit_price ? Number(inquiryForm.unit_price) : undefined,
        currency: inquiryForm.currency || 'USD',
        lead_time: inquiryForm.lead_time.trim() || undefined,
        payment: inquiryForm.payment.trim() || undefined,
        quality_note: inquiryForm.quality_note.trim() || undefined,
        note: inquiryForm.note.trim() || undefined,
      });
      setInquiryForm({ supplier_name: '', product: '', quantity: '', unit_price: '', currency: 'USD', lead_time: '', payment: '', quality_note: '', note: '' });
      setCompare(null);
      setCompareProduct('');
      loadInquiries();
    } catch (e) {
      setError(e instanceof Error ? e.message : '录入询价失败');
    }
    setSavingInquiry(false);
  };

  const doCompare = async () => {
    if (!compareProduct.trim()) return;
    try {
      setCompare(await compareInquiries(compareProduct.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : '比价失败');
    }
  };

  const loadReports = async () => {
    try {
      setReports(await fetchSupplierReports());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleDiscover = async () => {
    setDiscovering(true);
    setError('');
    try {
      const r = await discoverSuppliers({ product: product || undefined });
      setSuppliers(r.suppliers);
    } catch (e) {
      setError(e instanceof Error ? e.message : '发现失败');
    }
    setDiscovering(false);
  };

  const handleAnalyze = async (
    name: string,
    productCategory?: string,
    supplierData?: Record<string, unknown>,
    supplierId?: number
  ) => {
    setAnalyzing(true);
    setError('');
    try {
      const report = await analyzeSupplier({ supplier_name: name, product_category: productCategory, supplier_data: supplierData, supplier_id: supplierId });
      setCurrent(report);
      loadReports();
    } catch (e) {
      setError(e instanceof Error ? e.message : '分析失败');
    }
    setAnalyzing(false);
  };

  const handleCustomAnalyze = async () => {
    if (!customSupplier.trim()) return;
    await handleAnalyze(customSupplier.trim());
  };

  return (
    <section className="page">
      <h1>AI 采购助手</h1>
      <p className="card-desc">AI 驱动的供应商分析、风险评估与询价对比</p>

      {error && <p className="error-text">{error}</p>}

      {/* 询价 / 比价（V3） */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>供应商询价 / 比价</strong>
          <span className="executions-count">已录入 {inquiries.length} 条询价</span>
        </div>

        {!readonly && (
          <>
            <div className="composer-row" style={{ flexWrap: 'wrap' }}>
              <input style={{ flex: 1, minWidth: 140 }} placeholder="供应商名称 *"
                value={inquiryForm.supplier_name}
                onChange={(e) => setInquiryForm({ ...inquiryForm, supplier_name: e.target.value })} />
              <input style={{ flex: 1, minWidth: 140 }} placeholder="产品 *"
                value={inquiryForm.product}
                onChange={(e) => setInquiryForm({ ...inquiryForm, product: e.target.value })} />
              <input style={{ width: 90 }} type="number" placeholder="数量"
                value={inquiryForm.quantity}
                onChange={(e) => setInquiryForm({ ...inquiryForm, quantity: e.target.value })} />
              <input style={{ width: 110 }} type="number" placeholder="单价 USD"
                value={inquiryForm.unit_price}
                onChange={(e) => setInquiryForm({ ...inquiryForm, unit_price: e.target.value })} />
              <input style={{ width: 100 }} placeholder="交期（如 15天）"
                value={inquiryForm.lead_time}
                onChange={(e) => setInquiryForm({ ...inquiryForm, lead_time: e.target.value })} />
              <input style={{ width: 130 }} placeholder="付款方式"
                value={inquiryForm.payment}
                onChange={(e) => setInquiryForm({ ...inquiryForm, payment: e.target.value })} />
            </div>
            <div className="composer-row" style={{ marginTop: 6 }}>
              <input style={{ flex: 1 }} placeholder="质量 / 证书说明（ISO/CE/FDA）"
                value={inquiryForm.quality_note}
                onChange={(e) => setInquiryForm({ ...inquiryForm, quality_note: e.target.value })} />
              <input style={{ flex: 1 }} placeholder="备注"
                value={inquiryForm.note}
                onChange={(e) => setInquiryForm({ ...inquiryForm, note: e.target.value })} />
              <button className="btn btn-submit" onClick={saveInquiry}
                disabled={savingInquiry || !inquiryForm.supplier_name.trim() || !inquiryForm.product.trim()}>
                {savingInquiry ? '保存中...' : '录入询价'}
              </button>
            </div>
          </>
        )}

        <div className="composer-row" style={{ marginTop: 8 }}>
          <input style={{ flex: 1 }} placeholder="按产品比价（如：LED 灯）"
            value={compareProduct}
            onChange={(e) => setCompareProduct(e.target.value)} />
          <button className="btn" onClick={doCompare} disabled={!compareProduct.trim()}>
            比价
          </button>
        </div>

        {compare && (
          <div style={{ marginTop: 10 }}>
            <div className="inquiry-best">
              ⭐ 最优报价：
              {compare.cheapest
                ? `${compare.cheapest.supplier_name}（${compare.cheapest.currency} ${compare.cheapest.unit_price}/件${compare.cheapest.lead_time ? '，交期 ' + compare.cheapest.lead_time : ''}）`
                : '暂无带价格的询价记录'}
            </div>
            <div className="inquiry-table">
              <div className="inquiry-row head">
                <span>供应商</span><span>产品</span><span>数量</span><span>单价</span><span>交期/付款</span><span>资质</span>
              </div>
              {compare.items.map((iq) => (
                <div className="inquiry-row" key={iq.id}>
                  <span>{iq.supplier_name}</span>
                  <span>{iq.product}</span>
                  <span>{iq.quantity ?? '-'}</span>
                  <span className={compare.cheapest && iq.id === compare.cheapest.id ? 'inquiry-cheapest' : ''}>
                    {iq.currency} {iq.unit_price ?? '-'}
                  </span>
                  <span>{[iq.lead_time, iq.payment].filter(Boolean).join(' / ') || '-'}</span>
                  <span>{iq.quality_note || ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 供应商发现 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>{t('supplierDiscovery')}</strong>
          <span className="executions-count">{t('supplierDiscoveryDesc')}</span>
        </div>
        <div className="composer-row">
          <input
            placeholder="产品关键词（如 LED）"
            value={product}
            onChange={(e) => setProduct(e.target.value)}
          />
          {!readonly && (
            <button className="btn btn-submit" onClick={handleDiscover} disabled={discovering}>
              {discovering ? '搜索中...' : t('discoverSuppliers')}
            </button>
          )}
        </div>
        {suppliers.length > 0 && (
          <div className="customs-list">
            {suppliers.map((s, i) => (
              <div key={i} className="customs-item">
                <div className="execution-item-main">
                  <span className="execution-employee">{s.name}</span>
                  <span className="lead-badge">{s.product_category as string}</span>
                </div>
                <div className="execution-item-sub">
                  <span>{s.province} {s.city} · {s.phone}</span>
                  <button
                    className="btn btn-sm btn-submit"
                    onClick={() =>
                      handleAnalyze(
                        s.name as string,
                        s.product_category as string | undefined,
                        {
                          province: s.province,
                          city: s.city,
                          phone: s.phone,
                          website: s.website,
                          country: '中国',
                        }
                      )
                    }
                    disabled={analyzing}
                  >
                    分析
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 手动分析 */}
      <div className="import-panel">
        <div className="executions-header">
          <strong>{t('manualAnalyze')}</strong>
        </div>
        <div className="composer-row">
          <input
            placeholder="输入供应商名称（或从下方已有供应商分析）"
            value={customSupplier}
            onChange={(e) => setCustomSupplier(e.target.value)}
          />
          {!readonly && (
            <button className="btn btn-submit" onClick={handleCustomAnalyze} disabled={analyzing || !customSupplier.trim()}>
              {analyzing ? '分析中...' : t('analyze')}
            </button>
          )}
        </div>
      </div>

      {/* 分析报告 */}
      {current && (
        <div className="analysis-report">
          <div className="executions-header">
            <strong>分析报告 · {current.supplier_name}</strong>
            <span className="analysis-method">
              {current.analysis_method === 'ai' ? 'AI 分析' : '规则分析'}
            </span>
          </div>
          <div className="analysis-scores">
            <div className="score-item">
              <span className="score-value" style={{ color: LEVEL_COLOR[current.overall_level ?? 'C'] }}>
                {current.overall_level}
              </span>
              <span className="score-label">综合评级</span>
              <span className="score-num">{current.overall_score} 分</span>
            </div>
            <div className="score-item">
              <span className="score-value" style={{ color: LEVEL_COLOR[current.risk_level ?? '中'] }}>
                {current.risk_level}
              </span>
              <span className="score-label">风险</span>
              <span className="score-num">{current.risk_score} 分</span>
            </div>
            <div className="score-item">
              <span className="score-value" style={{ color: LEVEL_COLOR[current.price_level ?? '中'] }}>
                {current.price_level}
              </span>
              <span className="score-label">价格竞争力</span>
              <span className="score-num">{current.price_score} 分</span>
            </div>
            <div className="score-item">
              <span className="score-value" style={{ color: LEVEL_COLOR[current.capacity_level ?? '中'] }}>
                {current.capacity_level}
              </span>
              <span className="score-label">产能</span>
              <span className="score-num">{current.capacity_score} 分</span>
            </div>
          </div>

          <div className="analysis-dimensions">
            <div className="dimension">
              <strong>风险分析</strong>
              <p>{current.risk_summary}</p>
            </div>
            <div className="dimension">
              <strong>价格分析</strong>
              <p>{current.price_summary}</p>
            </div>
            <div className="dimension">
              <strong>产能分析</strong>
              <p>{current.capacity_summary}</p>
            </div>
          </div>

          {current.recommendations.length > 0 && (
            <div className="analysis-recommendations">
              <strong>建议</strong>
              <ul>
                {current.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {current.report && (
            <div className="analysis-report-body">
              <strong>完整报告</strong>
              <pre>{current.report}</pre>
            </div>
          )}
        </div>
      )}

      {/* 历史报告 */}
      <div className="executions-panel">
        <div className="executions-header">
          <strong>{t('analysisHistory')}</strong>
          <span className="executions-count">{reports.length} 份</span>
        </div>
        {reports.length === 0 ? (
          <p className="executions-empty">{t('noAnalysisHistory')}</p>
        ) : (
          <div className="leads-list">
            {reports.map((r) => (
              <div key={r.id} className="lead-item">
                <div className="execution-item-main">
                  <span className="execution-employee" onClick={() => setCurrent(r)}>
                    {r.supplier_name}
                  </span>
                  <span className="lead-badge">{r.product_category}</span>
                  <span className={`execution-status st-${r.overall_level === 'A' ? 'completed' : r.overall_level === 'B' ? 'running' : 'queued'}`}>
                    {r.overall_level} 级 · {r.overall_score} 分
                  </span>
                </div>
                <div className="execution-item-sub">
                  <span>
                    风险{r.risk_level} · 价格{r.price_level} · 产能{r.capacity_level}
                  </span>
                  <span className="execution-time">{new Date(r.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
