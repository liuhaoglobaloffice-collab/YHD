import { useEffect, useState } from 'react';
import { fetchMetrics, MetricsData } from '../services/metrics';
import { useI18n } from '../i18n';

export function MetricsPage() {
  const { t } = useI18n();
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    try {
      const data = await fetchMetrics();
      setMetrics(data);
    } catch (e) {
      console.error('Failed to load metrics', e);
      setError('加载系统指标失败');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <section className="page">
        <h1>{t('metrics')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  if (error || !metrics) {
    return (
      <section className="page">
        <h1>{t('metrics')}</h1>
        <p className="error-text">{error || t('loadFailed')}</p>
      </section>
    );
  }

  return (
    <section className="page">
      <h1>{t('metrics')}</h1>
      <div className="grid">
        <div className="card">
          <strong>CPU</strong>
          <div className="card-value">{metrics.cpu_load}%</div>
        </div>
        <div className="card">
          <strong>Memory</strong>
          <div className="card-value">{metrics.memory_load}%</div>
        </div>
        <div className="card">
          <strong>Latency</strong>
          <div className="card-value">{metrics.latency_ms}ms</div>
        </div>
        <div className="card">
          <strong>Throughput</strong>
          <div className="card-value">{metrics.throughput} req/s</div>
        </div>
        <div className="card">
          <strong>System</strong>
          <div className="card-meta">v{metrics.system_version}</div>
          <div className="card-status">{metrics.overall_status}</div>
        </div>
        <div className="card">
          <strong>Environment</strong>
          <div className="card-meta">{metrics.environment}</div>
        </div>
      </div>
    </section>
  );
}