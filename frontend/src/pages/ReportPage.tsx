import { useState } from 'react';
import { fetchWeeklyReport, type WeeklyReport } from '../services/crm';
import { useI18n } from '../i18n';

const SOURCE_LABELS: Record<string, string> = {
  social: '社媒',
  google: '谷歌',
  customs: '海关',
  manual: '手动',
  import: '导入',
};

export function ReportPage() {
  const { t } = useI18n();
  const [days, setDays] = useState(7);
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const load = async (d: number) => {
    setLoading(true);
    setError('');
    try {
      setReport(await fetchWeeklyReport(d));
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成周报失败');
    }
    setLoading(false);
  };

  const copySummary = async () => {
    if (!report) return;
    try {
      await navigator.clipboard.writeText(
        `【鎏灏外贸周报 ${report.period}】\n${report.summary}\n\n线索 ${report.leads.new_total} · 成交 ${report.funnel.won_count}单 $${report.funnel.won_amount.toLocaleString()} · 消息${report.messages.sent}/${report.messages.received}\n生成于 ${new Date().toLocaleString()}`
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>外贸周报</h1>
        <div className="cost-days-tabs">
          {[7, 30, 90].map((d) => (
            <button key={d} className={`cost-days-tab ${days === d ? 'active' : ''}`} onClick={() => { setDays(d); load(d); }}>
              {d}天
            </button>
          ))}
          <button className="btn btn-sm btn-submit" onClick={() => load(days)} disabled={loading}>
            {loading ? '生成中...' : '生成周报'}
          </button>
        </div>
      </div>
      <p className="card-desc">
        自动汇总线索、询盘漏斗、平台消息、供应商与 AI 成本，一键复盘本周业务。
      </p>

      {error && <p className="error-text">{error}</p>}
      {!report && !loading && (
        <div className="card">
          <p>点击「生成周报」查看最近 {days} 天的业务复盘。</p>
        </div>
      )}
      {loading && !report && <p>{t('loading')}</p>}

      {report && (
        <>
          {/* AI 摘要 */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="executions-header">
              <strong>AI 摘要</strong>
              <button className="btn btn-sm" onClick={copySummary}>
                {copied ? '已复制' : '复制摘要'}
              </button>
            </div>
            <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{report.summary}</p>
          </div>

          <div className="grid" style={{ marginBottom: 16 }}>
            <div className="card">
              <div className="cost-label">新增线索</div>
              <div className="cost-value">{report.leads.new_total}</div>
              <div className="cost-sub">
                {Object.entries(report.leads.by_source)
                  .map(([k, v]) => `${SOURCE_LABELS[k] ?? k} ${v}`)
                  .join(' · ')}
              </div>
            </div>
            <div className="card">
              <div className="cost-label">成交</div>
              <div className="cost-value">{report.funnel.won_count} 单</div>
              <div className="cost-sub">${Math.round(report.funnel.won_amount).toLocaleString()}</div>
            </div>
            <div className="card">
              <div className="cost-label">询盘/流失</div>
              <div className="cost-value">
                {report.funnel.quoted} / {report.funnel.lost_count}
              </div>
              <div className="cost-sub">报价客户 / 流失（待跟进 {report.leads.follow_up_due}）</div>
            </div>
            <div className="card">
              <div className="cost-label">消息收发</div>
              <div className="cost-value">{report.messages.sent}/{report.messages.received}</div>
              <div className="cost-sub">发送/接收（4 平台）</div>
            </div>
            <div className="card">
              <div className="cost-label">供应商</div>
              <div className="cost-value">{report.supplier_reports}</div>
              <div className="cost-sub">分析报告 · 询价 {report.inquiries} 条</div>
            </div>
            <div className="card">
              <div className="cost-label">AI 成本</div>
              <div className="cost-value">{report.ai.calls}</div>
              <div className="cost-sub">调用 · ${report.ai.cost_usd.toFixed(4)}</div>
            </div>
          </div>

          {/* 流失原因 */}
          {Object.keys(report.funnel.lost_reasons).length > 0 && (
            <div className="card">
              <div className="cost-label">流失原因 TOP</div>
              <div className="funnel-meta">
                {Object.entries(report.funnel.lost_reasons).map(([r, c]) => (
                  <span key={r} className="funnel-lost">
                    {r} ×{c}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}