import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Bot, Cpu, Database, ShieldCheck, Sparkles } from 'lucide-react';

interface AIProvidersPageProps {
  mode?: 'list' | 'models';
}

interface ProviderHealthItem {
  provider: string;
  name: string;
  status: 'healthy' | 'degraded' | 'unconfigured' | 'disabled' | 'warning';
  enabled: boolean;
  models: string[];
  latency_ms?: number;
  last_checked?: string;
}

const fallbackProviders: ProviderHealthItem[] = [
  {
    provider: 'openai',
    name: 'OpenAI',
    status: 'healthy',
    enabled: true,
    models: ['gpt-4o', 'gpt-4o-mini'],
    latency_ms: 420,
  },
  {
    provider: 'anthropic',
    name: 'Anthropic',
    status: 'unconfigured',
    enabled: false,
    models: ['claude-3-5-sonnet'],
    latency_ms: 0,
  },
  {
    provider: 'ollama',
    name: 'Ollama Local',
    status: 'healthy',
    enabled: true,
    models: ['qwen2.5:7b', 'llama3.1:8b'],
    latency_ms: 680,
  },
];

const statusStyles: Record<string, string> = {
  healthy: 'bg-green-500/10 text-green-300 border border-green-500/20',
  degraded: 'bg-yellow-500/10 text-yellow-300 border border-yellow-500/20',
  unconfigured: 'bg-gray-500/10 text-gray-200 border border-gray-500/20',
  disabled: 'bg-slate-500/10 text-slate-200 border border-slate-500/20',
  warning: 'bg-orange-500/10 text-orange-300 border border-orange-500/20',
};

const Sparkline: React.FC<{ points: number[]; width?: number; height?: number }> = ({ points, width = 120, height = 28 }) => {
  if (!points || points.length === 0) return <div className="text-xs text-gray-400">no data</div>;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = Math.max(1, max - min);
  const step = width / Math.max(1, points.length - 1);
  const coords = points.map((v, i) => `${i * step},${height - ((v - min) / range) * height}`).join(' ');
  return (
    <svg className="w-full h-7" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polyline fill="none" stroke="#60a5fa" strokeWidth={1.5} points={coords} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

const AIProvidersPage: React.FC<AIProvidersPageProps> = ({ mode = 'list' }) => {
  const isModelsView = mode === 'models';
  const [providers, setProviders] = useState<ProviderHealthItem[]>(fallbackProviders);
  const [metrics, setMetrics] = useState<Record<string, number[]>>({});
  const [modelMetrics, setModelMetrics] = useState<Record<string, { model: string; points: number[] }[]>>({});
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadProviders = async () => {
      try {
        const response = await axios.get('/api/v1/providers');
        if (isMounted && Array.isArray(response.data)) {
          setProviders(response.data);
        }
      } catch (err) {
        if (isMounted) {
          setError('Provider status service not available yet; using local fallback data.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

      const loadMetrics = async () => {
      try {
        const r = await axios.get('/api/v1/providers/metrics');
        if (isMounted && Array.isArray(r.data)) {
          // build both per-provider merged series and per-provider per-model series
          const map: Record<string, number[]> = {};
          const modelMap: Record<string, { model: string; points: number[] }[]> = {};
          for (const item of r.data) {
            const key = item.provider;
            // extract latency series for this model
            const latencies = (item.points || []).map((p: any) => p.latency_ms ?? 0);
            if (!modelMap[key]) modelMap[key] = [];
            modelMap[key].push({ model: item.model ?? item.model_name ?? 'model', points: latencies });

            if (!map[key]) map[key] = [];
            if (map[key].length === 0) map[key] = latencies;
            else {
              const merged = [];
              const len = Math.max(map[key].length, latencies.length);
              for (let i = 0; i < len; i++) {
                const a = map[key][i] ?? 0;
                const b = latencies[i] ?? 0;
                merged.push(Math.round((a + b) / 2));
              }
              map[key] = merged;
            }
          }
          setMetrics(map);
          setModelMetrics(modelMap);
        }
      } catch (err) {
        // metrics are optional — ignore errors silently
      }
    };

    loadProviders();
    loadMetrics();

    return () => {
      isMounted = false;
    };
  }, []);


  const modelRows = useMemo(
    () =>
      providers.flatMap((provider) =>
        provider.models.map((model) => ({
          name: model,
          provider: provider.name,
          type: provider.provider === 'ollama' ? 'Local' : 'Cloud',
          status: provider.status === 'healthy' ? 'Healthy' : provider.status === 'degraded' ? 'Degraded' : 'Unconfigured',
          queue: provider.provider === 'ollama' ? '3' : '12',
        }))
      ),
    [providers]
  );

  const openProviderModal = (providerKey: string) => {
    setSelectedProvider(providerKey);
  };

  const closeModal = () => setSelectedProvider(null);

  const healthyCount = providers.filter((item) => item.status === 'healthy').length;
  const averageLatency = Math.round(
    providers.reduce((total, item) => total + (item.latency_ms ?? 0), 0) / providers.length || 0
  );

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">AI Provider</p>
          <h1 className="text-3xl font-bold mt-2">{isModelsView ? '模型配置' : 'Provider 列表'}</h1>
        </div>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium">
          新增 Provider
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3 text-yellow-200 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Active Providers', value: `${providers.filter((item) => item.enabled).length}`, icon: Bot },
          { label: 'Healthy Models', value: `${healthyCount}`, icon: Cpu },
          { label: 'Avg Latency', value: `${averageLatency}ms`, icon: Database },
          { label: 'Security', value: 'Strong', icon: ShieldCheck },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-300">
                <Icon className="w-5 h-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {isModelsView ? (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold">模型健康状态</h2>
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <Sparkles className="w-4 h-4 text-purple-400" />
              {loading ? 'Loading...' : '低延迟优先'}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-5 py-3 text-gray-400 font-medium">Model</th>
                  <th className="px-5 py-3 text-gray-400 font-medium">Provider</th>
                  <th className="px-5 py-3 text-gray-400 font-medium">Type</th>
                  <th className="px-5 py-3 text-gray-400 font-medium">Status</th>
                  <th className="px-5 py-3 text-gray-400 font-medium">Queue</th>
                </tr>
              </thead>
              <tbody>
                {modelRows.map((row) => (
                  <tr key={`${row.provider}-${row.name}`} className="border-t border-gray-700">
                    <td className="px-5 py-3 font-medium">{row.name}</td>
                    <td className="px-5 py-3 text-gray-300">{row.provider}</td>
                    <td className="px-5 py-3 text-gray-300">{row.type}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs ${statusStyles[row.status.toLowerCase()] ?? 'bg-gray-500/10 text-gray-200'}`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-300">{row.queue}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {providers.map((provider) => (
            <div key={provider.provider} className="bg-gray-800 border border-gray-700 rounded-xl p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-gray-400">{provider.provider}</p>
                  <h3 className="text-xl font-semibold mt-2">{provider.name}</h3>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${statusStyles[provider.status] ?? statusStyles.unconfigured}`}>
                  {provider.status}
                </span>
              </div>

              <div className="mt-5 space-y-3 text-sm text-gray-300">
                  <div className="flex justify-between items-center">
                  <span>Latency</span>
                  <span className="font-medium text-white">{provider.latency_ms ? `${provider.latency_ms}ms` : 'N/A'}</span>
                </div>
                  {/* inline sparkline if metrics exist for this provider */}
                  <div className="mt-2">
                    {metrics[provider.provider] && metrics[provider.provider].length > 0 ? (
                      <div className="w-36">
                        <Sparkline points={metrics[provider.provider]} width={140} height={28} />
                      </div>
                    ) : (
                      <div className="text-xs text-gray-400">No metrics</div>
                    )}
                  </div>

                  <div className="flex justify-between">
                    <span>Enabled</span>
                    <span className="font-medium text-white">{provider.enabled ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Models</span>
                    <span className="font-medium text-white">{provider.models.length}</span>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  {provider.models.map((model) => (
                    <span key={model} className="px-2 py-1 text-xs rounded-full bg-gray-700 text-gray-200">
                      {model}
                    </span>
                  ))}
                </div>

                <div className="mt-4">
                  <button onClick={() => setSelectedProvider(provider.provider)} className="text-sm px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded-md">View models</button>
                </div>
              </div>
          ))}
        </div>
      )}
      {/* Provider models modal */}
      {selectedProvider && (
        <div className="fixed inset-0 z-40 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSelectedProvider(null)} />
          <div className="relative z-50 max-w-3xl w-full bg-gray-900 border border-gray-700 rounded-lg p-6">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold">Models for {selectedProvider}</h3>
                <p className="text-sm text-gray-400">Per-model latency series (last N samples)</p>
              </div>
              <div>
                <button onClick={() => setSelectedProvider(null)} className="px-3 py-1 bg-gray-800 rounded-md">Close</button>
              </div>
            </div>

            <div className="mt-4 space-y-4 max-h-96 overflow-y-auto">
              {(modelMetrics[selectedProvider] || []).map((m) => {
                const latest = m.points && m.points.length ? `${m.points[m.points.length - 1]}ms` : 'N/A';
                const avg = m.points && m.points.length ? `${Math.round(m.points.reduce((a, b) => a + b, 0) / m.points.length)}ms` : 'N/A';
                return (
                  <div key={m.model} className="bg-gray-800 border border-gray-700 rounded-md p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">{m.model}</div>
                        <div className="text-xs text-gray-400">Latest: {latest} • Avg: {avg}</div>
                      </div>
                      <div className="w-56">
                        <Sparkline points={m.points} width={220} height={48} />
                      </div>
                    </div>
                  </div>
                );
              })}

              {(!modelMetrics[selectedProvider] || modelMetrics[selectedProvider].length === 0) && (
                <div className="text-sm text-gray-400">No model metrics available for this provider.</div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default AIProvidersPage;
