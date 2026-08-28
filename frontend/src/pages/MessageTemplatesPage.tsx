import { useEffect, useState } from 'react';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';
import { fetchAccounts, type PlatformAccount } from '../services/platforms';
import {
  fetchTemplates,
  renderTemplate,
  sendTemplate,
  type Template,
} from '../services/templates';

export function MessageTemplatesPage() {
  const { t } = useI18n();
  const readonly = isReadonly();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // 选中模板
  const [selectedTpl, setSelectedTpl] = useState<Template | null>(null);

  // 发送表单
  const [sendAccountId, setSendAccountId] = useState<number>(0);
  const [sendToId, setSendToId] = useState('');
  const [sendToName, setSendToName] = useState('');
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState('');

  // 预览
  const [previewText, setPreviewText] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [tplData, accData] = await Promise.all([
        fetchTemplates(),
        fetchAccounts(),
      ]);
      setTemplates(tplData.templates);
      setAccounts(accData.accounts);
      if (accData.accounts.length > 0) {
        setSendAccountId(accData.accounts[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelect = (tpl: Template) => {
    setSelectedTpl(tpl);
    setSendError('');
    setSuccessMsg('');
    setPreviewText('');

    // 初始化变量
    const vars: Record<string, string> = {};
    if (tpl.example) {
      if (tpl.example.header_text) {
        tpl.example.header_text.forEach((v, i) => { vars[String(i + 1)] = v; });
      }
      if (tpl.example.body_text) {
        tpl.example.body_text.forEach((row) => {
          row.forEach((v, i) => {
            if (!vars[String(i + 1)]) vars[String(i + 1)] = v;
          });
        });
      }
    }
    setVariables(vars);
  };

  const handlePreview = async () => {
    if (!selectedTpl) return;
    try {
      const result = await renderTemplate(selectedTpl.id, variables);
      setPreviewText(result.rendered);
    } catch (e) {
      setPreviewText(e instanceof Error ? e.message : '预览失败');
    }
  };

  const handleSend = async () => {
    if (!selectedTpl || !sendAccountId || !sendToId.trim()) return;
    setSending(true);
    setSendError('');
    setSuccessMsg('');
    try {
      const result = await sendTemplate(
        selectedTpl.id,
        sendAccountId,
        sendToId.trim(),
        variables,
        sendToName.trim() || undefined
      );
      setSuccessMsg(`模板消息已发送！消息ID: ${result.message_id}`);
      setPreviewText('');
    } catch (e) {
      setSendError(e instanceof Error ? e.message : '发送失败');
    }
    setSending(false);
  };

  const CATEGORY_LABELS: Record<string, string> = {
    MARKETING: '营销',
    UTILITY: '实用',
    AUTHENTICATION: '认证',
  };

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>消息模板</h1>
      </div>
      <p className="card-desc">预置消息模板，支持 WhatsApp 模板消息的预览和发送。</p>

      {error && <p className="error-text">{error}</p>}
      {successMsg && <p className="ok-text">{successMsg}</p>}

      {loading ? (
        <div className="card"><p>加载中...</p></div>
      ) : templates.length === 0 ? (
        <div className="card"><p>暂无可用模板。</p></div>
      ) : (
        <div className="inbox-layout" style={{ display: 'flex', gap: 16, minHeight: 400 }}>
          {/* 模板列表 */}
          <div className="inbox-list" style={{ flex: 1, maxWidth: 360, overflowY: 'auto' }}>
            {templates.map((tpl) => (
              <div
                key={tpl.id}
                className={`card platform-card ${selectedTpl?.id === tpl.id ? 'selected' : ''}`}
                style={{ cursor: 'pointer', marginBottom: 8, padding: 12 }}
                onClick={() => handleSelect(tpl)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <strong style={{ fontSize: 13 }}>{tpl.name}</strong>
                  <span style={{ fontSize: 11, color: '#888' }}>
                    {CATEGORY_LABELS[tpl.category] ?? tpl.category}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#888' }}>
                  {tpl.language} · {tpl.variables} 个变量 · {tpl.platform}
                </div>
                <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
                  {tpl.components.filter((c) => c.type === 'BODY').map((c) => c.text).join(' ')}
                </div>
              </div>
            ))}
          </div>

          {/* 模板详情 + 发送 */}
          <div className="inbox-detail" style={{ flex: 2 }}>
            {!selectedTpl ? (
              <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }}>
                <p style={{ color: '#888' }}>选择一个模板查看详情</p>
              </div>
            ) : (
              <div className="card">
                <div className="executions-header">
                  <strong>{selectedTpl.name}</strong>
                  <span style={{ fontSize: 12, color: '#888' }}>
                    {CATEGORY_LABELS[selectedTpl.category] ?? selectedTpl.category} · {selectedTpl.language}
                  </span>
                </div>

                {/* 组件预览 */}
                <div style={{ marginTop: 12, marginBottom: 16 }}>
                  {selectedTpl.components.map((comp, i) => (
                    <div key={i} style={{ marginBottom: 8, padding: 8, background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
                      <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>{comp.type}</div>
                      <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{comp.text || '(无文本)'}</div>
                    </div>
                  ))}
                </div>

                {/* 变量填写 */}
                {selectedTpl.variables > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <strong style={{ fontSize: 13 }}>变量</strong>
                    {Array.from({ length: selectedTpl.variables }, (_, i) => i + 1).map((idx) => (
                      <div className="form-group" key={idx} style={{ marginTop: 8 }}>
                        <label style={{ fontSize: 12 }}>变量 {idx}</label>
                        <input
                          value={variables[String(idx)] ?? ''}
                          onChange={(e) => setVariables({ ...variables, [String(idx)]: e.target.value })}
                          placeholder={`变量 ${idx} 的值`}
                        />
                      </div>
                    ))}
                    <button className="btn btn-sm" onClick={handlePreview} style={{ marginTop: 8 }}>
                      预览
                    </button>
                    {previewText && (
                      <div style={{ marginTop: 8, padding: 8, background: 'rgba(0,217,255,0.1)', borderRadius: 6, fontSize: 13 }}>
                        <strong>预览：</strong>
                        <div style={{ whiteSpace: 'pre-wrap', marginTop: 4 }}>{previewText}</div>
                      </div>
                    )}
                  </div>
                )}

                <hr style={{ borderColor: 'rgba(255,255,255,0.1)', margin: '12px 0' }} />

                {/* 发送表单 */}
                {!readonly && (
                  <>
                    <strong style={{ fontSize: 13 }}>发送模板消息</strong>
                    {sendError && <p className="error-text">{sendError}</p>}
                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>平台账号</label>
                      <select
                        value={sendAccountId}
                        onChange={(e) => setSendAccountId(Number(e.target.value))}
                      >
                        {accounts.map((acc) => (
                          <option key={acc.id} value={acc.id}>
                            {acc.name} ({acc.platform})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group">
                      <label>对方 ID</label>
                      <input
                        value={sendToId}
                        onChange={(e) => setSendToId(e.target.value)}
                        placeholder="接收方 ID / 手机号"
                      />
                    </div>
                    <div className="form-group">
                      <label>对方名称（可选）</label>
                      <input
                        value={sendToName}
                        onChange={(e) => setSendToName(e.target.value)}
                        placeholder="接收方名称"
                      />
                    </div>
                    <button
                      className="btn btn-submit"
                      onClick={handleSend}
                      disabled={sending || !sendToId.trim() || !sendAccountId}
                      style={{ marginTop: 8 }}
                    >
                      {sending ? '发送中...' : '发送模板消息'}
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}