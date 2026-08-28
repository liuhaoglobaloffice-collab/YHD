import { useEffect, useState } from 'react';
import {
  bindAccount,
  fetchAccounts,
  fetchContacts,
  fetchLanguages,
  fetchMessages,
  receiveMessages,
  sendPlatformMessage,
  syncContacts,
  testAccount,
  translateText,
  unbindAccount,
  updateAccount,
  toggleAccount,
  searchMessages,
  type Language,
  type PlatformAccount,
  type PlatformContact,
  type PlatformMessage,
  type PlatformOption,
} from '../services/platforms';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';

const PLATFORM_LABELS: Record<string, string> = {
  whatsapp: 'WhatsApp',
  facebook: 'Facebook / Messenger',
  linkedin: 'LinkedIn',
  wechat: '企业微信',
};

const STATUS_LABELS: Record<string, { text: string; cls: string }> = {
  connected: { text: '已连接', cls: 'ok' },
  mock: { text: '开发模式', cls: 'mock' },
  disconnected: { text: '未连接', cls: 'off' },
  error: { text: '异常', cls: 'off' },
};

export function PlatformPage() {
  const { t } = useI18n();
  const readonly = isReadonly();
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [platforms, setPlatforms] = useState<PlatformOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 绑定表单
  const [showBind, setShowBind] = useState(false);
  const [bindForm, setBindForm] = useState({
    platform: 'whatsapp',
    name: '',
    account_id: '',
    credentials: '',
  });
  const [binding, setBinding] = useState(false);
  const [bindError, setBindError] = useState('');

  // 工作台
  const [selected, setSelected] = useState<PlatformAccount | null>(null);
  const [contacts, setContacts] = useState<PlatformContact[]>([]);
  const [messages, setMessages] = useState<PlatformMessage[]>([]);
  const [toId, setToId] = useState('');
  const [toName, setToName] = useState('');
  const [content, setContent] = useState('');
  const [targetLang, setTargetLang] = useState('');
  const [languages, setLanguages] = useState<Language[]>([]);
  const [sending, setSending] = useState(false);
  const [workError, setWorkError] = useState('');

  // 翻译
  const [trText, setTrText] = useState('');
  const [trLang, setTrLang] = useState('en');
  const [trResult, setTrResult] = useState('');
  const [translating, setTranslating] = useState(false);

  // 编辑
  const [editAccount, setEditAccount] = useState<PlatformAccount | null>(null);
  const [editName, setEditName] = useState('');
  const [editCredentials, setEditCredentials] = useState('');
  const [saving, setSaving] = useState(false);

  // 搜索
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<PlatformMessage[] | null>(null);
  const [searching, setSearching] = useState(false);

  const loadAccounts = async () => {
    try {
      const data = await fetchAccounts();
      setAccounts(data.accounts);
      setPlatforms(data.platforms);
    } catch (e) {
      console.error('Failed to load accounts', e);
      setError('加载平台账号失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAccounts();
    fetchLanguages()
      .then(setLanguages)
      .catch(() => {});
  }, []);

  const loadWorkbench = async (acc: PlatformAccount) => {
    setSelected(acc);
    setWorkError('');
    try {
      const [cs, ms] = await Promise.all([fetchContacts(acc.id), fetchMessages(acc.id)]);
      setContacts(cs);
      setMessages(ms);
      if (cs.length > 0) {
        setToId(cs[0].remote_id);
        setToName(cs[0].name ?? '');
      }
    } catch (e) {
      console.error(e);
      setWorkError('加载工作台数据失败');
    }
  };

  const handleBind = async () => {
    setBinding(true);
    setBindError('');
    try {
      let credentials: Record<string, unknown> | null = null;
      if (bindForm.credentials.trim()) {
        try {
          credentials = JSON.parse(bindForm.credentials);
        } catch {
          setBindError('凭据 JSON 格式错误');
          setBinding(false);
          return;
        }
      }
      await bindAccount({
        platform: bindForm.platform,
        name: bindForm.name,
        account_id: bindForm.account_id,
        credentials,
      });
      setShowBind(false);
      setBindForm({ platform: 'whatsapp', name: '', account_id: '', credentials: '' });
      loadAccounts();
    } catch (e) {
      setBindError(e instanceof Error ? e.message : '绑定失败');
    }
    setBinding(false);
  };

  const handleTest = async (acc: PlatformAccount) => {
    try {
      const r = await testAccount(acc.id);
      alert(`${PLATFORM_LABELS[acc.platform]} 连接测试：${r.ok ? '成功' : '失败'} - ${r.message}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : '测试失败');
    }
  };

  const handleUnbind = async (acc: PlatformAccount) => {
    if (!confirm(`确认解绑 ${acc.name} ？`)) return;
    try {
      await unbindAccount(acc.id);
      if (selected?.id === acc.id) setSelected(null);
      loadAccounts();
    } catch (e) {
      setError(e instanceof Error ? e.message : '解绑失败');
    }
  };

  const handleSend = async () => {
    if (!selected || !toId.trim() || !content.trim()) return;
    setSending(true);
    setWorkError('');
    try {
      await sendPlatformMessage(selected.id, {
        to_id: toId.trim(),
        to_name: toName.trim() || undefined,
        content: content.trim(),
        target_lang: targetLang || undefined,
      });
      setContent('');
      const ms = await fetchMessages(selected.id);
      setMessages(ms);
    } catch (e) {
      setWorkError(e instanceof Error ? e.message : '发送失败');
    }
    setSending(false);
  };

  const handleReceive = async () => {
    if (!selected) return;
    setWorkError('');
    try {
      const ms = await receiveMessages(selected.id);
      setMessages(ms);
    } catch (e) {
      setWorkError(e instanceof Error ? e.message : '拉取失败');
    }
  };

  const handleSyncContacts = async () => {
    if (!selected) return;
    try {
      await syncContacts(selected.id);
      setContacts(await fetchContacts(selected.id));
    } catch (e) {
      setWorkError(e instanceof Error ? e.message : '同步失败');
    }
  };

  const handleTranslate = async () => {
    if (!trText.trim()) return;
    setTranslating(true);
    setTrResult('');
    try {
      const r = await translateText(trText.trim(), trLang);
      setTrResult(r.translated);
    } catch (e) {
      setTrResult(e instanceof Error ? e.message : '翻译失败');
    }
    setTranslating(false);
  };

  const handleOpenEdit = (acc: PlatformAccount) => {
    setEditAccount(acc);
    setEditName(acc.name);
    setEditCredentials(acc.credentials ? JSON.stringify(acc.credentials, null, 2) : '');
  };

  const handleSaveEdit = async () => {
    if (!editAccount) return;
    setSaving(true);
    setError('');
    try {
      let credentials: Record<string, unknown> | undefined;
      if (editCredentials.trim()) {
        try { credentials = JSON.parse(editCredentials); }
        catch { setError('凭据 JSON 格式错误'); setSaving(false); return; }
      }
      await updateAccount(editAccount.id, { name: editName, credentials });
      setEditAccount(null);
      loadAccounts();
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败');
    }
    setSaving(false);
  };

  const handleToggle = async (acc: PlatformAccount) => {
    try {
      await toggleAccount(acc.id);
      loadAccounts();
    } catch (e) {
      setError(e instanceof Error ? e.message : '切换失败');
    }
  };

  const handleSearch = async () => {
    if (!selected || !searchQuery.trim()) return;
    setSearching(true);
    try {
      const results = await searchMessages(selected.id, searchQuery.trim());
      setSearchResults(results);
    } catch (e) {
      setWorkError(e instanceof Error ? e.message : '搜索失败');
    }
    setSearching(false);
  };

  if (loading) {
    return (
      <section className="page">
        <h1>{t('platformCenter')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>{t('platformCenter')}</h1>
        {!readonly && (
          <button className="btn btn-submit" onClick={() => setShowBind(true)}>
            + {t('bindPlatform')}
          </button>
        )}
      </div>
      <p className="card-desc">{t('platformCenterDesc')}</p>

      {error && <p className="error-text">{error}</p>}

      {/* 平台账号卡片 */}
      {accounts.length === 0 ? (
        <div className="card">
          <p>{t('noPlatformAccount')}</p>
        </div>
      ) : (
        <div className="grid">
          {accounts.map((acc) => {
            const st = STATUS_LABELS[acc.status] ?? STATUS_LABELS.disconnected;
            return (
              <div className={`card platform-card ${selected?.id === acc.id ? 'selected' : ''}`} key={acc.id}>
                <div className="platform-card-head">
                  <span className="platform-badge">{PLATFORM_LABELS[acc.platform] ?? acc.platform}</span>
                  <span className={`platform-status ${st.cls}`}>{st.text}</span>
                </div>
                <strong>{acc.name}</strong>
                <div className="card-meta">
                  <span>{acc.account_id}</span>
                  {!acc.is_active && <span className="sub-active off">停用</span>}
                </div>
                <div className="sub-actions">
                  <button className="btn btn-sm" onClick={() => loadWorkbench(acc)}>
                    打开工作台
                  </button>
                  <button className="btn btn-sm" onClick={() => handleTest(acc)}>
                    测试连接
                  </button>
                  {!readonly && (
                    <>
                      <button className="btn btn-sm" onClick={() => handleToggle(acc)}>
                        {acc.is_active ? '停用' : '启用'}
                      </button>
                      <button className="btn btn-sm" onClick={() => handleOpenEdit(acc)}>
                        编辑
                      </button>
                      <button className="btn btn-sm btn-cancel" onClick={() => handleUnbind(acc)}>
                        解绑
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 平台工作台 */}
      {selected && (
        <div className="platform-workbench">
          <div className="executions-header">
            <strong>
              {PLATFORM_LABELS[selected.platform] ?? selected.platform} · {selected.name}
            </strong>
            <div className="workbench-actions">
              {!readonly && (
                <>
                  <button className="btn btn-sm" onClick={handleSyncContacts}>
                    同步联系人
                  </button>
                  <button className="btn btn-sm" onClick={handleReceive}>
                    拉取消息
                  </button>
                </>
              )}
            </div>
          </div>

          {workError && <p className="error-text">{workError}</p>}

          <div className="workbench-body">
            {/* 联系人列表 */}
            <div className="workbench-contacts">
              <div className="executions-header">
                <strong>联系人</strong>
                <span className="executions-count">{contacts.length}</span>
              </div>
              {contacts.length === 0 ? (
                <p className="executions-empty">{t('noContacts')}</p>
              ) : (
                <div className="contact-list">
                  {contacts.map((c) => (
                    <button
                      key={c.id}
                      className={`contact-item ${toId === c.remote_id ? 'active' : ''}`}
                      onClick={() => {
                        setToId(c.remote_id);
                        setToName(c.name ?? '');
                      }}
                    >
                      <span className="contact-name">{c.name || c.remote_id}</span>
                      {c.phone && <span className="contact-phone">{c.phone}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 聊天区 */}
            <div className="workbench-chat">
              {/* 搜索栏 */}
              <div className="composer-row" style={{ marginBottom: 8 }}>
                <input
                  placeholder="搜索消息内容..."
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setSearchResults(null); }}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button className="btn btn-sm" onClick={handleSearch} disabled={searching || !searchQuery.trim()}>
                  {searching ? '搜索中...' : '搜索'}
                </button>
                {searchResults !== null && (
                  <button className="btn btn-sm btn-cancel" onClick={() => setSearchResults(null)}>
                    清除
                  </button>
                )}
              </div>
              <div className="chat-list">
                {(searchResults ?? messages).length === 0 ? (
                  <p className="executions-empty">{t('noMessages')}</p>
                ) : (
                  (searchResults ?? messages).map((m) => (
                    <div
                      key={m.id}
                      className={`chat-bubble ${m.direction === 'outbound' ? 'out' : 'in'}`}
                    >
                      <div className="chat-meta">
                        <span>{m.direction === 'outbound' ? '我' : m.from_name || '对方'}</span>
                        <span className="execution-time">
                          {m.created_at ? new Date(m.created_at).toLocaleString() : ''}
                        </span>
                      </div>
                      <div className="chat-content">
                        {searchResults ? <mark style={{ background: 'rgba(0,217,255,0.2)', color: '#00d9ff' }}>{m.content}</mark> : m.content}
                      </div>
                      {m.translated_content && m.translated_content !== m.content && (
                        <div className="chat-translated">🌐 {m.translated_content}</div>
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* 发送区（子账号只读隐藏） */}
              {!readonly && (
                <div className="chat-composer">
                <div className="composer-row">
                  <input
                    placeholder="对方 ID"
                    value={toId}
                    onChange={(e) => setToId(e.target.value)}
                  />
                  <input
                    placeholder="对方名称（可选）"
                    value={toName}
                    onChange={(e) => setToName(e.target.value)}
                  />
                </div>
                <div className="composer-row">
                  <textarea
                    placeholder="输入消息内容..."
                    rows={2}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                  />
                </div>
                <div className="composer-row">
                  <select
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    title="自动翻译为"
                  >
                    <option value="">不翻译</option>
                    {languages.map((l) => (
                      <option key={l.code} value={l.code}>
                        {l.name}
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn btn-submit"
                    onClick={handleSend}
                    disabled={sending || !toId.trim() || !content.trim()}
                  >
                    {sending ? '发送中...' : '发送'}
                  </button>
                </div>
              </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 翻译工具 */}
      <div className="import-panel translate-panel">
        <div className="executions-header">
          <strong>{t('translateTool')}</strong>
        </div>
        <div className="composer-row">
          <textarea
            placeholder="输入要翻译的内容..."
            rows={2}
            value={trText}
            onChange={(e) => setTrText(e.target.value)}
          />
          <select value={trLang} onChange={(e) => setTrLang(e.target.value)}>
            {languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
          <button
            className="btn btn-submit"
            onClick={handleTranslate}
            disabled={translating || !trText.trim()}
          >
            {translating ? '翻译中...' : t('translate')}
          </button>
        </div>
        {trResult && (
          <div className="translate-result">
            <strong>翻译结果：</strong>
            <div>{trResult}</div>
          </div>
        )}
      </div>

      {/* 绑定弹窗 */}
      {showBind && (
        <div className="modal-overlay" onClick={() => setShowBind(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{t('bindPlatform')}</h2>
            <div className="form-group">
              <label>{t('platformType')}</label>
              <select
                value={bindForm.platform}
                onChange={(e) => setBindForm({ ...bindForm, platform: e.target.value })}
              >
                {platforms.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>{t('accountName')}</label>
              <input
                value={bindForm.name}
                onChange={(e) => setBindForm({ ...bindForm, name: e.target.value })}
                placeholder="例如：主号 WhatsApp"
              />
            </div>
            <div className="form-group">
              <label>{t('accountId')}</label>
              <input
                value={bindForm.account_id}
                onChange={(e) => setBindForm({ ...bindForm, account_id: e.target.value })}
                placeholder="平台侧账号ID / 手机号"
              />
            </div>
            <div className="form-group">
              <label>{t('credentials')}（可选，JSON）</label>
              <textarea
                rows={3}
                value={bindForm.credentials}
                onChange={(e) => setBindForm({ ...bindForm, credentials: e.target.value })}
                placeholder='{"access_token": "..."}'
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setShowBind(false)}>
                {t('cancel')}
              </button>
              <button
                className="btn btn-submit"
                onClick={handleBind}
                disabled={binding || !bindForm.name || !bindForm.account_id}
              >
                {binding ? '绑定中...' : t('bind')}
              </button>
            </div>
            {bindError && (
              <div className="modal-error">
                <strong>错误：</strong> {bindError}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 编辑弹窗 */}
      {editAccount && (
        <div className="modal-overlay" onClick={() => setEditAccount(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>编辑平台账号</h2>
            <div className="form-group">
              <label>账号名称</label>
              <input value={editName} onChange={(e) => setEditName(e.target.value)} />
            </div>
            <div className="form-group">
              <label>凭据（JSON，可选）</label>
              <textarea
                rows={3}
                value={editCredentials}
                onChange={(e) => setEditCredentials(e.target.value)}
                placeholder='{"access_token": "..."}'
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setEditAccount(null)}>
                {t('cancel')}
              </button>
              <button className="btn btn-submit" onClick={handleSaveEdit} disabled={saving || !editName}>
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
