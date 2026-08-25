import React from 'react';
import { AlertTriangle, BellRing, CheckCircle2, ShieldAlert, SlidersHorizontal } from 'lucide-react';

interface AlertsPageProps {
  mode?: 'list' | 'rules';
}

const alertRows = [
  { title: 'Supplier latency spike', source: 'Supplier API', severity: 'High', owner: 'Ops Team', status: 'Investigating' },
  { title: 'AI provider retry storm', source: 'AI Gateway', severity: 'Critical', owner: 'Platform', status: 'Mitigated' },
  { title: 'Task queue backlog', source: 'Workflow Engine', severity: 'Medium', owner: 'Workflow Ops', status: 'Open' },
  { title: 'Security policy drift', source: 'Identity', severity: 'High', owner: 'Security', status: 'Reviewing' },
];

const ruleRows = [
  { name: 'Supplier latency threshold', scope: 'Supplier API', trigger: 'P95 > 2.5s', action: 'Notify Ops' },
  { name: 'AI provider error burst', scope: 'AI Gateway', trigger: '5xx > 10%', action: 'Auto retry + page' },
  { name: 'Workflow backlog guard', scope: 'Tasks queue', trigger: 'queue > 35', action: 'Escalate to owner' },
];

const AlertsPage: React.FC<AlertsPageProps> = ({ mode = 'list' }) => {
  const title = mode === 'list' ? '告警列表' : '告警规则';
  const badge = mode === 'list' ? 'Alert stream' : 'Rule policy';

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-red-300">Overview</p>
          <h1 className="text-3xl font-bold mt-2">{title}</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300">
          {mode === 'list' ? <BellRing className="w-4 h-4" /> : <SlidersHorizontal className="w-4 h-4" />}
          <span className="text-sm">{badge}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: 'Open alerts', value: '12', icon: AlertTriangle },
          { label: 'Critical', value: '3', icon: ShieldAlert },
          { label: 'Mitigated today', value: '8', icon: CheckCircle2 },
          { label: 'Escalated', value: '2', icon: BellRing },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-red-500/10 text-red-300">
                <Icon className="w-4 h-4" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {mode === 'list' ? (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Active incidents</h2>
            <span className="text-sm text-gray-400">Last refreshed 2 min ago</span>
          </div>
          <div className="divide-y divide-gray-700">
            {alertRows.map((row) => (
              <div key={row.title} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                <div>
                  <p className="font-medium text-white">{row.title}</p>
                  <p className="text-sm text-gray-400 mt-1">Source: {row.source}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs ${row.severity === 'Critical' ? 'bg-red-500/10 text-red-300' : row.severity === 'High' ? 'bg-orange-500/10 text-orange-300' : 'bg-yellow-500/10 text-yellow-300'}`}>
                    {row.severity}
                  </span>
                  <span className="text-gray-300">Owner {row.owner}</span>
                  <span className="px-2 py-1 rounded-full bg-blue-500/10 text-blue-300 text-xs">{row.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Rule catalog</h2>
            <span className="text-sm text-gray-400">Policy guardrails</span>
          </div>
          <div className="divide-y divide-gray-700">
            {ruleRows.map((row) => (
              <div key={row.name} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                <div>
                  <p className="font-medium text-white">{row.name}</p>
                  <p className="text-sm text-gray-400 mt-1">Scope: {row.scope}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="text-gray-300">Trigger {row.trigger}</span>
                  <span className="px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-300 text-xs">{row.action}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AlertsPage;
