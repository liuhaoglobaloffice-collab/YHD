import { useEffect, useState } from 'react';
import { fetchProviders, ProviderInfo } from '../services/models';
import { useI18n } from '../i18n';

export function ModelsPage() {
  const { t } = useI18n();
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      const data = await fetchProviders();
      setProviders(data);
    } catch (e) {
      console.error('Failed to load providers', e);
      setError('加载模型列表失败');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <section className="page">
        <h1>{t('models')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="page">
        <h1>{t('models')}</h1>
        <p className="error-text">{error}</p>
      </section>
    );
  }

  return (
    <section className="page">
      <h1>{t('models')}</h1>
      {providers.length === 0 ? (
        <p>暂未配置模型 Provider，请通过 Productization 流程配置</p>
      ) : (
        <div className="grid">
          {providers.map((p, i) => (
            <div className="card" key={i}>
              <strong>{p.provider}</strong>
              <div className="card-meta">
                <span>模型: {p.model}</span>
              </div>
              <div className="card-status">
                {p.enabled ? 'Available' : 'Disabled'}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}