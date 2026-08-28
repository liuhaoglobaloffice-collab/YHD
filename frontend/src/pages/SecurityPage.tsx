import { useEffect, useState } from 'react';
import { fetchSecurityStatus, SecurityStatus } from '../services/security';
import { useI18n } from '../i18n';

export function SecurityPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSecurityStatus();
  }, []);

  const loadSecurityStatus = async () => {
    try {
      const data = await fetchSecurityStatus();
      setStatus(data);
    } catch (e) {
      console.error('Failed to load security status', e);
      setError('加载安全状态失败');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <section className="page">
        <h1>{t('security')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  if (error || !status) {
    return (
      <section className="page">
        <h1>{t('security')}</h1>
        <p className="error-text">{error || t('loadFailed')}</p>
      </section>
    );
  }

  return (
    <section className="page">
      <h1>{t('security')}</h1>
      <div className="grid">
        <div className="card">
          <strong>RBAC</strong>
          <div className="card-status">{status.rbac}</div>
          <div className="card-meta">{status.permissions_count} 个权限</div>
        </div>
        <div className="card">
          <strong>Roles</strong>
          <div className="card-status">Ready</div>
          <div className="card-meta">{status.roles_count} 个角色</div>
        </div>
        <div className="card">
          <strong>Audit</strong>
          <div className="card-status">Active</div>
          <div className="card-meta">{status.audit_count} 条最近记录</div>
        </div>
        <div className="card">
          <strong>Secret</strong>
          <div className="card-status">Protected</div>
          <div className="card-meta">环境: {status.last_audit_time ? new Date(status.last_audit_time).toLocaleString() : 'N/A'}</div>
        </div>
      </div>
    </section>
  );
}