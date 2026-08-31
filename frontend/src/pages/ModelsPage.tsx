import { useEffect, useState } from 'react';
import {
  fetchProviderStatus,
  fetchProviderCatalog,
  fetchProviderConfigs,
  saveProviderConfig,
  deleteProviderConfig,
  type ProviderStatus,
  type ProviderRuntimeInfo,
  type ProviderCatalogItem,
  type ProviderConfigEntry,
} from '../services/models';
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

const inputStyle: React.CSSProperties = {
  width: '100%',
  background: '#0d1420',
  border: '1px solid #2a3a55',
  borderRadius: 6,
  padding: '8px 10px',
  color: '#e0e0e0',
  fontSize: 13,
  fontFamily: 'monospace',
  boxSizing: 'border-box',
};

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 11, color: '#8aa', marginBottom: 4, marginTop: 10,
};

function AddProviderModal({
  catalog,
  initialProvider,
  onClose,
  onSaved,
}: {
  catalog: ProviderCatalogItem[];
  initialProvider?: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const initial = catalog.find((c) => c.name === initialProvider) ?? catalog[0];
  const [provider, setProvider] = useState(initial?.name ?? 'deepseek');
  const [baseUrl, setBaseUrl] = useState(initial?.default_base_url ?? '');
  const [model, setModel] = useState(initial?.default_model ?? '');
  const [apiKey, setApiKey] = useState('');
  const [test, setTest] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');

  const selected = catalog.find((c) => c.name === provider);

  const pickProvider = (name: string) => {
    const c = catalog.find((x) => x.name === name);
    setProvider(name);
    if (c) {
      setBaseUrl(c.default_base_url);
      setModel(c.default_model);
    }
    setError('');
    setOk('');
  };

  const submit = async () => {
    setBusy(true);
    setError('');
    setOk('');
    try {
      const res = await saveProviderConfig({
        provider,
        base_url: baseUrl.trim(),
        model: model.trim(),
        api_key: apiKey.trim() || undefined,
        test,
      });
      setOk(
        (res.health?.status === 'healthy' ? '✓ 连接测试通过。' : '') +
        `已保存并立即生效：${res.config?.display_name ?? provider} / ${res.config?.model ?? model}`,
      );
      setApiKey('');
      onSaved();
      setTimeout(onClose, 1200);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#121a29', border: '1px solid #2a3a55', borderRadius: 12,
          padding: 22, width: 520, maxWidth: '92vw', maxHeight: '90vh', overflowY: 'auto',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, color: '#4cc9f0', fontSize: 16 }}>添加模型 Provider / API Key</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#888', fontSize: 18, cursor: 'pointer' }}>✕</button>
        </div>
        <p style={{ color: '#789', fontSize: 11, margin: '6px 0 0' }}>
          密钥加密后存入数据库，立即生效并在重启后保留；明文密钥不会在任何接口返回。
        </p>

        <label style={labelStyle}>Provider</label>
        <select style={inputStyle} value={provider} onChange={(e) => pickProvider(e.target.value)}>
          {catalog.map((c) => (
            <option key={c.name} value={c.name}>{c.display_name}（{c.name}）</option>
          ))}
        </select>

        <label style={labelStyle}>API Base URL</label>
        <input style={inputStyle} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.example.com/v1" />

        <label style={labelStyle}>默认模型</label>
        <input style={inputStyle} value={model} onChange={(e) => setModel(e.target.value)} placeholder="model id" />

        {selected?.needs_key && (
          <>
            <label style={labelStyle}>API Key{selected.needs_key ? '' : '（可选）'}</label>
            <input
              style={inputStyle}
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="粘贴 API Key；更新已有配置时留空表示不修改"
              autoComplete="off"
            />
          </>
        )}

        <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
          <input type="checkbox" checked={test} onChange={(e) => setTest(e.target.checked)} />
          保存前进行真实连接测试（测试失败则不保存）
        </label>

        {error && (
          <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 6, background: 'rgba(255,82,82,0.1)', border: '1px solid rgba(255,82,82,0.4)', color: '#ff8a80', fontSize: 12 }}>
            ✗ {error}
          </div>
        )}
        {ok && (
          <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 6, background: 'rgba(0,230,118,0.1)', border: '1px solid rgba(0,230,118,0.4)', color: '#69f0ae', fontSize: 12 }}>
            {ok}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
          <button
            onClick={submit}
            disabled={busy}
            style={{
              flex: 1, background: busy ? '#2a4a66' : '#4cc9f0', color: '#04121f',
              border: 'none', borderRadius: 6, padding: '10px 0', fontWeight: 700,
              cursor: busy ? 'wait' : 'pointer', fontSize: 13,
            }}
          >
            {busy ? '保存中…' : test ? '测试连接并保存' : '保存并启用'}
          </button>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: '1px solid #3a4a66', color: '#aab', borderRadius: 6, padding: '10px 18px', cursor: 'pointer', fontSize: 13 }}
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}

export function ModelsPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [catalog, setCatalog] = useState<ProviderCatalogItem[]>([]);
  const [configs, setConfigs] = useState<ProviderConfigEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingProvider, setEditingProvider] = useState<string | undefined>(undefined);
  const [configError, setConfigError] = useState('');

  const loadAll = async () => {
    const [s, cat, cfg] = await Promise.allSettled([
      fetchProviderStatus(),
      fetchProviderCatalog(),
      fetchProviderConfigs(),
    ]);
    if (s.status === 'fulfilled') setStatus(s.value);
    else {
      console.error('Failed to load provider status', s.reason);
      setError('加载模型 Provider 状态失败');
    }
    if (cat.status === 'fulfilled') setCatalog(cat.value);
    if (cfg.status === 'fulfilled') setConfigs(cfg.value);
    else setConfigError('（无 system:read 权限或未登录管理员账号）');
    setLoading(false);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const refreshAfterChange = async () => {
    const [s, cfg] = await Promise.allSettled([fetchProviderStatus(), fetchProviderConfigs()]);
    if (s.status === 'fulfilled') setStatus(s.value);
    if (cfg.status === 'fulfilled') setConfigs(cfg.value);
  };

  const removeConfig = async (name: string) => {
    if (!window.confirm(`确认删除 Provider 配置「${name}」？运行时将立即注销。`)) return;
    try {
      await deleteProviderConfig(name);
      await refreshAfterChange();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : String(e));
    }
  };

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <h1 style={{ color: '#4cc9f0', fontSize: 20, margin: 0 }}>模型与 Provider</h1>
        <button
          onClick={() => { setEditingProvider(undefined); setShowModal(true); }}
          style={{
            background: '#4cc9f0', color: '#04121f', border: 'none', borderRadius: 6,
            padding: '8px 16px', fontWeight: 700, cursor: 'pointer', fontSize: 13,
          }}
        >
          ➕ 添加模型 / API Key
        </button>
      </div>
      <p style={{ color: '#888', fontSize: 12, margin: '0 0 20px 0' }}>
        实时检测各 AI Provider 的真实可用状态；可直接在此添加云端 API（OpenAI / DeepSeek / Kimi 等）或本地 Ollama
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

      {/* 已保存的 Provider 配置（产品内添加，加密持久化） */}
      <h2 style={{ fontSize: 14, color: '#cde', margin: '0 0 10px' }}>已保存的 Provider 配置</h2>
      {configs.length === 0 ? (
        <div style={{
          background: '#12121e', border: '1px dashed #2a2a3e', borderRadius: 8,
          padding: '18px 16px', color: '#667', fontSize: 12, marginBottom: 20,
        }}>
          暂无产品内添加的 Provider 配置 {configError}。点击右上角「➕ 添加模型 / API Key」接入云端模型；
          当前运行中的 Provider 来自环境变量配置。
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12, marginBottom: 20 }}>
          {configs.map((c) => (
            <div key={c.id} style={{ background: '#12121e', border: '1px solid #2a4a3e', borderRadius: 8, padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <strong style={{ color: '#e0e0e0', fontSize: 13 }}>{c.display_name}</strong>
                <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 10, color: c.enabled ? '#00e676' : '#888', background: c.enabled ? 'rgba(0,230,118,0.12)' : 'rgba(255,255,255,0.05)' }}>
                  {c.enabled ? '● 已启用' : '○ 已停用'}
                </span>
              </div>
              <div style={{ color: '#888', fontSize: 11, lineHeight: 1.7 }}>
                <div>模型: <span style={{ color: '#4cc9f0' }}>{c.model}</span></div>
                <div style={{ wordBreak: 'break-all' }}>地址: {c.base_url}</div>
                <div>密钥: {c.has_api_key ? <span style={{ color: '#00e676' }}>已保存 {c.api_key_preview ? `(${c.api_key_preview})` : ''}</span> : <span style={{ color: '#666' }}>无需密钥</span>}</div>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                <button
                  onClick={() => { setEditingProvider(c.provider); setShowModal(true); }}
                  style={{ flex: 1, background: 'transparent', border: '1px solid #3a5a7a', color: '#9cd', borderRadius: 5, padding: '5px 0', fontSize: 11, cursor: 'pointer' }}
                >
                  更新配置
                </button>
                <button
                  onClick={() => removeConfig(c.provider)}
                  style={{ flex: 1, background: 'transparent', border: '1px solid #6a3a3a', color: '#e89', borderRadius: 5, padding: '5px 0', fontSize: 11, cursor: 'pointer' }}
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Provider 运行时状态卡片 */}
      <h2 style={{ fontSize: 14, color: '#cde', margin: '0 0 10px' }}>运行时状态</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
        {status.providers.map((p) => (
          <ProviderCard key={p.type} p={p} active={p.type === status.provider && p.status === 'healthy'} />
        ))}
      </div>

      <p style={{ color: '#666', fontSize: 11, marginTop: 20 }}>
        提示：添加云端 Provider 时填写 API Key 即可自动完成注册与健康检测；
        Ollama 为本地 Provider，需保证 Ollama 服务已启动并拉取模型（容器内默认地址 http://host.docker.internal:11434）。
      </p>

      {showModal && (
        <AddProviderModal
          key={editingProvider ?? 'new'}
          catalog={catalog}
          initialProvider={editingProvider}
          onClose={() => setShowModal(false)}
          onSaved={refreshAfterChange}
        />
      )}
    </div>
  );
}
