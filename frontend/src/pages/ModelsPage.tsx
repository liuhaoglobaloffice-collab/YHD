import { useEffect, useState } from 'react';
import { fetchProviderStatus, type ProviderStatus, type ProviderRuntimeInfo } from '../services/models';
import { useI18n } from '../i18n';

function statusMeta(status: string): { color: string; bg: string; label: string } {
  switch (status) {
    case 'healthy':
      return { color: '#00e676', bg: 'rgba(0,230,118,0.12)', label: '可用' };
    case 'error':
      return { color: '#ff5252', bg: 'rgba(255,82,82,0.12)', label: '异常' };
    case 'unconfigured':
    default:
      return { color: '#777', bg: 'rgba(255,255,255,0.04)', label: '未配置' };
  }
}

function ProviderCard({ p, active }: { p: ProviderRuntimeInfo; active: boolean }) {
  const meta = statusMeta(p.status);
  return (
    <div
      style={{
        background: active ? '#14233a' : '#12121e',
        border: `1px solid ${active ? '#4cc9f0' : '#2a2a3e'}`,
        borderRadius: 8,
        padding: 16,
        position: 'relative',
      }}
    >
      {active && (
        <span
          style={{
            position: 'absolute', top: 12, right: 12,
            background: '#4cc9f0', color: '#04121f', fontSize: 10, fontWeight: 700,
            padding: '2px 8px', borderRadius: 10,
          }}
        >
          当前生效
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <strong style={{ color: '#e0e0e0', fontSize: 14 }}>{p.name}</strong>
        <span
          style={{
            fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 10,
            color: meta.color, background: meta.bg,
          }}
        >
          ● {meta.label}
        </span>
      </div>
      <div style={{ color: '#888', fontSize: 11, marginBottom: 8 }}>
        类型: {p.type}
        {p.env_var && <span> · 凭据: {p.env_var}</span>}
      </div>
      {p.models && p.models.length > 0 ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {p.models.map((m) => (
            <span
              key={m}
              style={{
                fontSize: 10, padding: '2px 8px', borderRadius: 4,
                background: p.status === 'healthy' ? 'rgba(76,201,240,0.12)' : 'rgba(255,255,255,0.05)',
                color: p.status === 'healthy' ? '#4cc9f0' : '#666',
                border: '1px solid rgba(76,201,240,0.2)',
              }}
            >
              {m}
            </span>
          ))}
        </div>
      ) : (
        <div style={{ color: '#555', fontSize: 11, fontStyle: 'italic' }}>暂无已注册模型</div>
      )}
    </div>
  );
}

export function ModelsPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        setStatus(await fetchProviderStatus());
      } catch (e) {
        console.error('Failed to load provider status', e);
        setError('加载模型 Provider 状态失败');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <section className="page">
        <h1>{t('models')}</h1>
        <p>{t('loading')}</p>
      </section>
    );
  }

  if (error || !status) {
    return (
      <section className="page">
        <h1>{t('models')}</h1>
        <p className="error-text">{error || '无法获取 Provider 状态'}</p>
      </section>
    );
  }

  const healthyCount = status.providers.filter((p) => p.status === 'healthy').length;
  const activeProvider = status.providers.find((p) => p.type === status.provider && p.status === 'healthy');

  return (
    <div style={{ padding: '24px 32px', color: '#e0e0e0', fontFamily: 'monospace', maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ color: '#4cc9f0', fontSize: 20, margin: '0 0 4px 0' }}>模型与 Provider</h1>
      <p style={{ color: '#888', fontSize: 12, margin: '0 0 20px 0' }}>
        实时检测各 AI Provider 的真实可用状态与已注册模型
      </p>

      {/* 全局状态横幅 */}
      <div
        style={{
          background: status.using_mock ? 'rgba(255,215,64,0.08)' : 'rgba(0,230,118,0.08)',
          border: `1px solid ${status.using_mock ? '#ffd740' : '#00e676'}`,
          borderRadius: 8,
          padding: '14px 16px',
          marginBottom: 20,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
        }}
      >
        <div>
          <div style={{ fontSize: 10, color: '#888' }}>当前生效 Provider</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#4cc9f0' }}>
            {activeProvider?.name ?? status.provider ?? '—'}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#888' }}>运行环境</div>
          <div style={{ fontSize: 13, color: '#e0e0e0' }}>{status.environment}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#888' }}>可用 Provider</div>
          <div style={{ fontSize: 13, color: healthyCount > 0 ? '#00e676' : '#ff5252' }}>
            {healthyCount} / {status.providers.length} 可用
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#888' }}>调用模式</div>
          <div style={{ fontSize: 13, color: status.using_mock ? '#ffd740' : '#00e676', fontWeight: 600 }}>
            {status.using_mock ? '⚠ Mock 模式（非真实调用）' : '✓ 真实模型调用'}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#888' }}>生产门禁</div>
          <div style={{ fontSize: 13, color: status.production_blocked ? '#ff5252' : '#00e676', fontWeight: 600 }}>
            {status.production_blocked ? '✗ 被阻断' : '✓ 放行'}
          </div>
        </div>
      </div>

      {/* Provider 卡片网格 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
        {status.providers.map((p) => (
          <ProviderCard key={p.type} p={p} active={p.type === status.provider && p.status === 'healthy'} />
        ))}
      </div>

      <p style={{ color: '#666', fontSize: 11, marginTop: 20 }}>
        提示：云端 Provider（OpenAI / Anthropic / Gemini 等）在配置对应 API Key 环境变量后自动变为可用；
        Ollama 为本地 Provider，需保证 Ollama 服务已启动并拉取模型。
      </p>
    </div>
  );
}
