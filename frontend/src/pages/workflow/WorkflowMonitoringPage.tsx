import React from 'react';
import { Activity, CheckCircle2, Clock3, Gauge, Play, Zap } from 'lucide-react';

const metrics = [
  { label: 'Running', value: '14', icon: Activity },
  { label: 'Completed Today', value: '32', icon: CheckCircle2 },
  { label: 'Avg Duration', value: '14m', icon: Clock3 },
  { label: 'Throughput', value: '92%', icon: Gauge },
];

const recentRuns = [
  { name: 'Supplier Risk Scan', status: 'Running', duration: '06m 12s', owner: 'supplier-bot' },
  { name: 'Daily Ops Summary', status: 'Completed', duration: '02m 18s', owner: 'ops-agent' },
  { name: 'AI Provider Retry', status: 'Queued', duration: 'Pending', owner: 'fallback-scheduler' },
  { name: 'Customer Lead Sync', status: 'Failed', duration: '00m 44s', owner: 'sales-orchestrator' },
];

const WorkflowMonitoringPage: React.FC = () => {
  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">Workflow</p>
          <h1 className="text-3xl font-bold mt-2">实时监控</h1>
        </div>
        <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg">
          <Play className="w-4 h-4" />
          运行任务
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {metrics.map(({ label, value, icon: Icon }) => (
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

      <div className="grid grid-cols-1 xl:grid-cols-[1.3fr_0.7fr] gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recent executions</h2>
            <span className="text-sm text-gray-400">Last 24h</span>
          </div>
          <div className="divide-y divide-gray-700">
            {recentRuns.map((run) => (
              <div key={run.name} className="flex items-center justify-between px-5 py-4">
                <div>
                  <p className="font-medium">{run.name}</p>
                  <p className="text-sm text-gray-400">{run.owner}</p>
                </div>
                <div className="text-right">
                  <p
                    className={`inline-flex px-2 py-1 rounded-full text-xs ${
                      run.status === 'Completed'
                        ? 'bg-green-500/10 text-green-300'
                        : run.status === 'Running'
                          ? 'bg-yellow-500/10 text-yellow-300'
                          : run.status === 'Failed'
                            ? 'bg-red-500/10 text-red-300'
                            : 'bg-gray-500/10 text-gray-300'
                    }`}
                  >
                    {run.status}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">{run.duration}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-5">
            <div className="p-2 rounded-lg bg-yellow-500/10 text-yellow-300">
              <Zap className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold">Execution health</h2>
          </div>
          <div className="space-y-4">
            {[
              { label: 'Success rate', value: '92%' },
              { label: 'Retry rate', value: '8%' },
              { label: 'Queue length', value: '19' },
              { label: 'Avg wait time', value: '1.4m' },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between border-b border-gray-700 pb-3 last:border-b-0 last:pb-0">
                <span className="text-gray-300">{item.label}</span>
                <span className="font-semibold text-white">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkflowMonitoringPage;
