const API_BASE = import.meta.env?.VITE_API_BASE ?? '';
const API_PREFIX = '/api/v1';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('liuhao_auth_token') ?? '';
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export interface CEOSummaryReport {
  status: 'generated' | 'partially_degraded';
  period_days: number;
  generated_at: string;
  report: {
    kpis: Record<string, unknown> & { message?: string; items?: Array<{ key: string; value: unknown }> };
    alerts: { message?: string; items?: Array<Record<string, unknown>> };
    goals: { message?: string; count?: number };
    cost: { message?: string; total_usd?: number; calls?: number };
  };
}

export async function fetchCEOSummaryReport(periodDays = 7): Promise<CEOSummaryReport> {
  const res = await fetch(`${API_BASE}${API_PREFIX}/ceo/summary-report?period_days=${periodDays}`, {
    headers: authHeaders(),
  });
  if (res.status === 401 || res.status === 403) {
    // 非 admin：返回空壳，前端以"需要管理员权限"的只读徽章显示
    return {
      status: 'partially_degraded',
      period_days: periodDays,
      generated_at: new Date().toISOString(),
      report: {
        kpis: { message: '需要管理员权限查看 KPI', items: [] },
        alerts: { message: '需要管理员权限查看告警', items: [] },
        goals: { message: '需要管理员权限查看目标', count: 0 },
        cost: { message: '需要管理员权限查看成本', total_usd: 0, calls: 0 },
      },
    };
  }
  if (!res.ok) throw new Error(`Failed to fetch CEO summary report: ${res.status}`);
  return res.json();
}
