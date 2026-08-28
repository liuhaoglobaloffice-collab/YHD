import { useEffect, useState } from 'react';
import { useI18n } from '../i18n';

const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000';
const API_PREFIX = '/api/v1';

function token(): string {
  return localStorage.getItem('liuhao_auth_token') ?? '';
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const t = token();
  const headers: Record<string, string> = { ...(extra ?? {}) };
  if (t) headers.Authorization = `Bearer ${t}`;
  return headers;
}

export interface ApprovalRequest {
  id: number;
  request_type: string;
  requester_id: number;
  target_resource: string;
  target_action: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  reason?: string;
  payload?: Record<string, any>;
  created_at: string;
  reviewed_at?: string;
  review_reason?: string;
}

const RISK_COLORS: Record<string, string> = {
  low: '#06d6a0',
  medium: '#facc15',
  high: '#fb8500',
  critical: '#ef233c',
};

const RISK_LABELS: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '极高',
};

export function ApprovalQueuePage() {
  const { t } = useI18n();
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('pending');

  const loadRequests = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set('status', statusFilter);
      const res = await fetch(`${API_BASE}${API_PREFIX}/approvals?${params.toString()}`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setRequests(data.requests);
      }
    } catch (e) {
      setError('加载审批队列失败');
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadRequests();
  }, [statusFilter]);

  const handleApprove = async (requestId: number, reason: string) => {
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/approvals/${requestId}/approve`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ reason: reason || '批准' }),
      });
      if (res.ok) {
        loadRequests();
      }
    } catch (e) {
      console.error(e);
      alert('审批失败');
    }
  };

  const handleReject = async (requestId: number, reason: string) => {
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/approvals/${requestId}/reject`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ reason: reason || '拒绝' }),
      });
      if (res.ok) {
        loadRequests();
      }
    } catch (e) {
      console.error(e);
      alert('拒绝失败');
    }
  };

  if (loading) return <div className="page-loading">{t('loading')}...</div>;

  return (
    <section className="page">
      <div className="page-header-row">
        <h1>审批队列</h1>
      </div>
      <p className="card-desc">高风险操作等待主账号批准，子账号操作需要审批才能执行</p>

      {error && <p className="error-text">{error}</p>}

      {/* 过滤 */}
      <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
        {['pending', 'approved', 'rejected'].map(s => (
          <button
            key={s}
            className={`btn btn-sm ${statusFilter === s ? 'btn-submit' : ''}`}
            onClick={() => setStatusFilter(s === statusFilter ? '' : s)}
          >
            {{
              pending: '待处理',
              approved: '已批准',
              rejected: '已拒绝',
            }[s]}
          </button>
        ))}
      </div>

      {requests.length === 0 && (
        <div className="executions-empty">暂无审批请求</div>
      )}

      {requests.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>ID</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>类型</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>操作</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>风险</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>申请人</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>申请时间</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>状态</th>
                <th style={{ padding: '10px 12px', textAlign: 'left' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {requests.map(req => (
                <tr key={req.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 500 }}>{req.id}</td>
                  <td style={{ padding: '10px 12px', color: 'rgba(255,255,255,0.6)' }}>{req.request_type}</td>
                  <td style={{ padding: '10px 12px', color: 'rgba(255,255,255,0.6)' }}>
                    {req.target_resource}:{req.target_action}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: 4,
                      background: `${RISK_COLORS[req.risk_level]}22`,
                      color: RISK_COLORS[req.risk_level],
                      border: `1px solid ${RISK_COLORS[req.risk_level]}`,
                    }}>
                      {RISK_LABELS[req.risk_level]}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', color: 'rgba(255,255,255,0.6)' }}>{req.requester_id}</td>
                  <td style={{ padding: '10px 12px', color: 'rgba(255,255,255,0.6)' }}>
                    {new Date(req.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: 4,
                      fontSize: 12,
                      background: req.status === 'pending' ? 'rgba(250, 204, 21, 0.15)'
                        : req.status === 'approved' ? 'rgba(6, 214, 160, 0.15)'
                        : 'rgba(255, 107, 107, 0.15)',
                      color: req.status === 'pending' ? '#faccc'
                        : req.status === 'approved' ? '#06d6a0'
                        : '#ff6b6b',
                    }}>
                      {{
                        pending: '待处理',
                        approved: '已批准',
                        rejected: '已拒绝',
                        cancelled: '已取消',
                      }[req.status]}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                    {req.status === 'pending' && (
                      <>
                        <button
                          className="btn btn-sm btn-submit"
                          style={{ marginRight: 6 }}
                          onClick={() => {
                            const reason = prompt('输入审批理由（可选）', '批准');
                            handleApprove(req.id, reason || '');
                          }}
                        >
                          批准
                        </button>
                        <button
                          className="btn btn-sm btn-cancel"
                          onClick={() => {
                            const reason = prompt('输入拒绝理由（可选）', '拒绝');
                            handleReject(req.id, reason || '');
                          }}
                        >
                          拒绝
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
