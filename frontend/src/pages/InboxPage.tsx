import { useEffect, useState } from 'react';
import { useI18n } from '../i18n';
import { isReadonly } from '../services/auth';
import { fetchAccounts, type PlatformAccount } from '../services/platforms';
import {
  fetchInbox,
  fetchInboxStats,
  replyInboxMessage,
  type InboxMessage,
  type InboxStats,
} from '../services/inbox';

const PLATFORM_LABELS: Record<string, string> = {
  whatsapp: 'WhatsApp',
  facebook: 'Facebook',
  linkedin: 'LinkedIn',
  wechat: '企业微信',
};

const PLATFORM_COLORS: Record<string, string> = {
  whatsapp: '#25D366',
  facebook: '#1877F2',
  linkedin: '#0A66C2',
  wechat: '#07C160',
};

export function InboxPage() {
  const { t } = useI18n();
  const readonly = isReadonly();
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 筛选
  const [platformFilter, setPlatformFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // 选中消息 + 回复
  const [selectedMsg, setSelectedMsg] = useState<InboxMessage | null>(null);
  const [replyContent, setReplyContent] = useState('');
  const [replyLang, setReplyLang] = useState('');
  const [sending, setSending] = useState(false);
  const [replyError, setReplyError] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [inboxData, statsData, accData] = await Promise.all([
        fetchInbox({
          platform: platformFilter || undefined,
          status: statusFilter || undefined,
          q: searchQuery || undefined,
        }),
        fetchInboxStats(),
        fetchAccounts(),
      ]);
      setMessages(inboxData.messages);
      setStats(statsData);
      setAccounts(accData.accounts);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleFilter = () => {
    loadData();
  };

  const handleSelectMessage = (msg: InboxMessage) => {
    setSelectedMsg(msg);
    setReplyContent('');
    setReplyError('');
  };

  const handleReply = async () => {
    if (!selectedMsg || !replyContent.trim()) return;
    setSending(true);
    setReplyError('');
    try {
      await replyInboxMessage(selectedMsg.id, replyContent.trim(), replyLang || undefined);
      setReplyContent('');
      loadData();
    } catch (e) {
      setReplyError(e instanceof Error ? e.message : '回复失败');
    }
    setSending(false);
  };

  const getAccountName = (accountId: number): string => {
    const acc = accounts.find((a) => a.id === accountId);
    return acc ? acc.name : `#${accountId}`;
  };

  const formatTime = (iso: string): string => {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin} 分钟前`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour} 小时前`;
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>统一收件箱</h1>
        {stats && (
          <div className="stats-row" style={{ display: 'flex', gap: 16, fontSize: 13, alignItems: 'center' }}>
            <span>📊 今日 {stats.today}</span>
            <span>⏳ 待回复 {stats.pending}</span>
            <span>📈 回复率 {stats.reply_rate}%</span>
            <span>📬 总计 {stats.total}</span>
          </div>
        )}
      </div>
      <p className="card-desc">跨平台消息聚合，统一管理 WhatsApp / 企业微信 / Facebook / LinkedIn 消息。</p>

      {error && <p className="error-text">{error}</p>}

      {/* 筛选栏 */}
      <div className="composer-row" style={{ marginBottom: 16, gap: 8 }}>
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value)}
          style={{ flex: 1 }}
        >
          <option value="">全部平台</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="wechat">企业微信</option>
          <option value="facebook">Facebook</option>
          <option value="linkedin">LinkedIn</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ flex: 1 }}
        >
          <option value="">全部状态</option>
          <option value="inbound">收到的</option>
          <option value="outbound">发出的</option>
          <option value="unread">未读</option>
        </select>
        <input
          placeholder="搜索消息内容..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleFilter()}
          style={{ flex: 2 }}
        />
        <button className="btn btn-sm" onClick={handleFilter} disabled={loading}>
          {loading ? '加载中...' : '筛选'}
        </button>
      </div>

      {loading && messages.length === 0 ? (
        <div className="card"><p>加载中...</p></div>
      ) : messages.length === 0 ? (
        <div className="card"><p>暂无消息。绑定平台账号并发送消息后，消息将出现在这里。</p></div>
      ) : (
        <div className="inbox-layout" style={{ display: 'flex', gap: 16, minHeight: 500 }}>
          {/* 消息列表 */}
          <div className="inbox-list" style={{ flex: 1, maxWidth: 420, overflowY: 'auto' }}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`card platform-card ${selectedMsg?.id === msg.id ? 'selected' : ''}`}
                style={{ cursor: 'pointer', marginBottom: 8, padding: 12 }}
                onClick={() => handleSelectMessage(msg)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ color: PLATFORM_COLORS[msg.platform] ?? '#888', fontWeight: 600, fontSize: 12 }}>
                    {PLATFORM_LABELS[msg.platform] ?? msg.platform}
                  </span>
                  <span style={{ color: '#888', fontSize: 11 }}>
                    {formatTime(msg.created_at)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <strong style={{ fontSize: 13 }}>
                    {msg.direction === 'outbound' ? '→ ' : '← '}
                    {msg.from_name || msg.from_id || msg.to_name || '未知'}
                  </strong>
                  <span style={{ fontSize: 11, color: '#888' }}>
                    {getAccountName(msg.account_id)}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: '#ccc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {msg.content}
                </div>
                {msg.status === 'received' && (
                  <span style={{ display: 'inline-block', background: '#ff4444', color: '#fff', fontSize: 10, padding: '1px 6px', borderRadius: 8, marginTop: 4 }}>
                    待回复
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* 消息详情 + 回复 */}
          <div className="inbox-detail" style={{ flex: 2, display: 'flex', flexDirection: 'column' }}>
            {!selectedMsg ? (
              <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <p style={{ color: '#888' }}>选择一条消息查看详情</p>
              </div>
            ) : (
              <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                {/* 消息详情 */}
                <div className="chat-list" style={{ flex: 1, overflowY: 'auto', marginBottom: 12 }}>
                  <div className={`chat-bubble ${selectedMsg.direction === 'outbound' ? 'out' : 'in'}`}>
                    <div className="chat-meta">
                      <span>
                        {selectedMsg.direction === 'outbound' ? '我' : selectedMsg.from_name || '对方'}
                        <span style={{ marginLeft: 8, color: PLATFORM_COLORS[selectedMsg.platform] ?? '#888', fontSize: 11 }}>
                          {PLATFORM_LABELS[selectedMsg.platform] ?? selectedMsg.platform}
                        </span>
                      </span>
                      <span className="execution-time">
                        {new Date(selectedMsg.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="chat-content">{selectedMsg.content}</div>
                    {selectedMsg.translated_content && selectedMsg.translated_content !== selectedMsg.content && (
                      <div className="chat-translated">🌐 {selectedMsg.translated_content}</div>
                    )}
                  </div>
                </div>

                {/* 回复区 */}
                {!readonly && (
                  <>
                    {replyError && <p className="error-text">{replyError}</p>}
                    <div className="composer-row" style={{ gap: 8 }}>
                      <textarea
                        placeholder="输入回复内容..."
                        rows={2}
                        value={replyContent}
                        onChange={(e) => setReplyContent(e.target.value)}
                        style={{ flex: 1 }}
                      />
                      <select
                        value={replyLang}
                        onChange={(e) => setReplyLang(e.target.value)}
                        title="自动翻译为"
                        style={{ width: 120 }}
                      >
                        <option value="">不翻译</option>
                        <option value="en">English</option>
                        <option value="zh">中文</option>
                        <option value="yue">粤语</option>
                        <option value="es">Español</option>
                        <option value="ar">العربية</option>
                        <option value="ja">日本語</option>
                        <option value="ko">한국어</option>
                        <option value="pt">Português</option>
                      </select>
                      <button
                        className="btn btn-submit"
                        onClick={handleReply}
                        disabled={sending || !replyContent.trim()}
                      >
                        {sending ? '发送中...' : '回复'}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 平台统计 */}
      {stats && stats.by_platform && Object.keys(stats.by_platform).length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="executions-header">
            <strong>平台消息分布</strong>
          </div>
          <div style={{ display: 'flex', gap: 24, marginTop: 8 }}>
            {Object.entries(stats.by_platform).map(([platform, count]) => (
              <div key={platform} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: PLATFORM_COLORS[platform] ?? '#888' }}>
                  {count}
                </div>
                <div style={{ fontSize: 12, color: '#888' }}>
                  {PLATFORM_LABELS[platform] ?? platform}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}