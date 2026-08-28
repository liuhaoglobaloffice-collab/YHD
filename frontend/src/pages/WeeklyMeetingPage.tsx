import { useState, useRef, useEffect, useCallback } from 'react';
import {
  fetchMeetings, createMeeting, fetchMessages, sendMessage, generateSummary,
  updateMeeting, updateMessage, deleteMessage, deleteMeeting,
  type Meeting, type Message,
} from '../services/meetings';
import { isLoggedIn } from '../services/auth';
import { useI18n } from '../i18n';
import { AIWorkStatus, type AIStatus } from '../components/AIWorkStatus';
import { AIActivityFeed, type ActivityItem } from '../components/AIActivityFeed';
import { AIEmptyState } from '../components/AIEmptyState';

export function WeeklyMeetingPage() {
  const { t } = useI18n();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [activeMeeting, setActiveMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [showNewMeeting, setShowNewMeeting] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDate, setNewDate] = useState(new Date().toISOString().split('T')[0]);
  const [error, setError] = useState('');
  const [apiError, setApiError] = useState(false);
  const [editingMsg, setEditingMsg] = useState<Message | null>(null);
  const [editContent, setEditContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => { loadMeetings(); }, []);
  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);
  useEffect(() => { if (activeMeeting) loadMessages(activeMeeting.id); }, [activeMeeting?.id]);

  const loadMeetings = async () => {
    try {
      const data = await fetchMeetings();
      setMeetings(data.meetings);
      if (data.meetings.length > 0) setActiveMeeting(data.meetings[0]);
      setApiError(false);
    } catch (e) {
      console.error('Failed to load meetings', e);
      setError('加载会议列表失败');
      setApiError(true);
    }
    setLoading(false);
  };

  const loadMessages = async (meetingId: string) => {
    try {
      const data = await fetchMessages(meetingId);
      setMessages(data.messages);
    } catch (e) { console.error('Failed to load messages', e); }
  };

  const handleNewMeeting = async () => {
    if (!newTitle.trim()) return;
    try {
      const meeting = await createMeeting(newTitle.trim(), newDate);
      setMeetings([meeting, ...meetings]);
      setActiveMeeting(meeting);
      setShowNewMeeting(false);
      setNewTitle('');
      setNewDate(new Date().toISOString().split('T')[0]);
      await sendMessage(meeting.id, '系统', 'admin', `📋 ${meeting.title}已开始，请各位成员汇报本周工作进展。`);
      await loadMessages(meeting.id);
    } catch (e) {
      console.error('Failed to create meeting', e);
      setError(isLoggedIn() ? '创建会议失败' : '请先登录');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !activeMeeting) return;
    setSending(true);
    try {
      await sendMessage(activeMeeting.id, input.trim(), 'user');
      setInput('');
      await loadMessages(activeMeeting.id);
    } catch (e) {
      console.error('Failed to send message', e);
      setError('发送失败');
    }
    setSending(false);
  };

  const handleGenerateSummary = async () => {
    if (!activeMeeting) return;
    try {
      await generateSummary(activeMeeting.id);
      await loadMessages(activeMeeting.id);
    } catch (e) {
      console.error('Failed to generate summary', e);
      setError('生成总结失败');
    }
  };

  const handleDeleteMeeting = async (meetingId: string) => {
    if (!confirm('确定删除此会议？')) return;
    try {
      await deleteMeeting(meetingId);
      const updated = meetings.filter(m => m.id !== meetingId);
      setMeetings(updated);
      if (activeMeeting?.id === meetingId) setActiveMeeting(updated[0] ?? null);
    } catch (e) {
      console.error('Failed to delete meeting', e);
      setError('删除失败');
    }
  };

  const handleEditMessage = (msg: Message) => {
    setEditingMsg(msg);
    setEditContent(msg.content);
  };

  const handleSaveEdit = async () => {
    if (!editingMsg || !editContent.trim()) return;
    try {
      await updateMessage(editingMsg.id, editContent.trim());
      setEditingMsg(null);
      setEditContent('');
      if (activeMeeting) loadMessages(activeMeeting.id);
    } catch (e) {
      console.error('Failed to update message', e);
      setError('编辑失败');
    }
  };

  const handleDeleteMessage = async (msgId: string) => {
    if (!confirm('确定删除此消息？')) return;
    try {
      await deleteMessage(msgId);
      if (activeMeeting) loadMessages(activeMeeting.id);
    } catch (e) {
      console.error('Failed to delete message', e);
      setError('删除失败');
    }
  };

  if (loading) {
    return <section className="page"><h1>AI CEO 会议</h1><p>{t('loading')}</p></section>;
  }

  if (apiError) {
    return (
      <section className="page">
        <h1>AI CEO 会议</h1>
        <AIEmptyState isError errorMessage={error} onRetry={loadMeetings} />
      </section>
    );
  }

  const hasMeetings = meetings.length > 0;

  return (
    <section className="page">
      <h1>AI CEO 会议</h1>

      {hasMeetings ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: 16, marginTop: 8 }}>
          {/* 左侧：会议列表 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                会议列表
              </span>
              <button className="btn btn-sm btn-submit" onClick={() => setShowNewMeeting(true)}>+ 新建</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {meetings.map(m => (
                <button
                  key={m.id}
                  className={`sub-mgmt-acc ${activeMeeting?.id === m.id ? 'active' : ''}`}
                  onClick={() => setActiveMeeting(m)}
                  style={{ textAlign: 'left', padding: '10px 12px' }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{m.title}</div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>
                    {m.date ? new Date(m.date).toLocaleDateString('zh-CN') : 'N/A'}
                  </div>
                </button>
              ))}
            </div>

            {/* AI 会议助手状态 */}
            <AIWorkStatus
              name="AI 会议助手"
              status="working"
              currentTask={activeMeeting ? `正在记录「${activeMeeting.title}」` : '等待会议开始'}
              todayCompleted={meetings.length}
              compact
            />
          </div>

          {/* 右侧：会议聊天 */}
          <div>
            {activeMeeting && (
              <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                {/* 会议标题栏 */}
                <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(110,130,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <strong>{activeMeeting.title}</strong>
                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginLeft: 8 }}>
                      {activeMeeting.date ? new Date(activeMeeting.date).toLocaleDateString('zh-CN') : ''}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button className="btn btn-sm" onClick={handleGenerateSummary} title="AI 生成会议总结">📝 总结</button>
                    <button className="btn btn-sm btn-cancel" onClick={() => handleDeleteMeeting(activeMeeting.id)}>🗑</button>
                  </div>
                </div>

                {/* 消息列表 */}
                <div style={{ height: 400, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {messages.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 40, color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>
                      暂无消息，开始汇报本周工作
                    </div>
                  ) : (
                    messages.map(msg => (
                      <div key={msg.id} className={`meeting-msg ${msg.sender === '系统' ? 'system' : ''}`}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                          <span style={{ fontSize: 12, fontWeight: 600, color: msg.sender === '系统' ? '#facc15' : '#4cc9f0' }}>
                            {msg.sender === '系统' ? '🤖 AI 助手' : msg.sender_name || msg.sender}
                          </span>
                          <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>
                            {msg.created_at ? new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}
                          </span>
                        </div>

                        {editingMsg?.id === msg.id ? (
                          <div>
                            <textarea value={editContent} onChange={e => setEditContent(e.target.value)} rows={2} className="modal-textarea" style={{ fontSize: 12 }} />
                            <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                              <button className="btn btn-sm btn-submit" onClick={handleSaveEdit}>保存</button>
                              <button className="btn btn-sm btn-cancel" onClick={() => setEditingMsg(null)}>取消</button>
                            </div>
                          </div>
                        ) : (
                          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                            {msg.content}
                          </div>
                        )}

                        {msg.sender !== '系统' && editingMsg?.id !== msg.id && (
                          <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                            <button className="btn btn-sm" style={{ fontSize: 10, padding: '2px 8px' }} onClick={() => handleEditMessage(msg)}>编辑</button>
                            <button className="btn btn-sm btn-cancel" style={{ fontSize: 10, padding: '2px 8px' }} onClick={() => handleDeleteMessage(msg.id)}>删除</button>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* 输入框 */}
                <div style={{ padding: '8px 12px', borderTop: '1px solid rgba(110,130,255,0.12)', display: 'flex', gap: 8 }}>
                  <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    placeholder="输入本周工作汇报..."
                    style={{ flex: 1, fontSize: 13 }}
                    disabled={sending}
                  />
                  <button className="btn btn-submit" onClick={handleSend} disabled={sending || !input.trim()}>
                    {sending ? '发送中...' : '发送'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <AIEmptyState
          title="AI 会议助手已准备好"
          description="等待生成第一次会议。创建周会后，AI 将自动记录会议内容、生成总结和待办事项。"
          aiStatus="waiting"
          availableTasks={['创建项目周会', 'AI 自动生成会议总结', '跟踪会议待办事项']}
          nextStep="建议先创建一个本周的项目周会"
          actionLabel="+ 创建首次会议"
          onAction={() => setShowNewMeeting(true)}
        />
      )}

      {/* 新建会议弹窗 */}
      {showNewMeeting && (
        <div className="modal-overlay" onClick={() => setShowNewMeeting(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>创建新会议</h2>
            <div className="form-group">
              <label>会议标题</label>
              <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="如：第12周项目周会" />
            </div>
            <div className="form-group">
              <label>会议日期</label>
              <input type="date" value={newDate} onChange={e => setNewDate(e.target.value)} />
            </div>
            <div className="modal-actions">
              <button className="btn btn-cancel" onClick={() => setShowNewMeeting(false)}>取消</button>
              <button className="btn btn-submit" onClick={handleNewMeeting} disabled={!newTitle.trim()}>创建</button>
            </div>
            {error && <div className="modal-error"><strong>错误：</strong> {error}</div>}
          </div>
        </div>
      )}
    </section>
  );
}