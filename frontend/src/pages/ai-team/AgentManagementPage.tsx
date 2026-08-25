import React from 'react';
import { Activity, Bot, Gauge, Layers3, Sparkles, Zap } from 'lucide-react';

interface AgentManagementPageProps {
  mode?: 'list' | 'capabilities';
}

const agentRows = [
  { name: 'Ops Agent', domain: 'Operations', status: 'Healthy', latency: '1.4s', utilization: '76%' },
  { name: 'Supplier Agent', domain: 'Procurement', status: 'Monitoring', latency: '2.3s', utilization: '82%' },
  { name: 'Research Agent', domain: 'R&D', status: 'Healthy', latency: '1.8s', utilization: '68%' },
  { name: 'Sales Agent', domain: 'Sales', status: 'Learning', latency: '2.7s', utilization: '58%' },
];

const capabilityRows = [
  { capability: 'Multi-agent routing', coverage: '99%', latency: '0.9s', sla: '99.5%' },
  { capability: 'Supplier matching', coverage: '95%', latency: '1.6s', sla: '98.7%' },
  { capability: 'Task orchestration', coverage: '97%', latency: '1.3s', sla: '99.2%' },
  { capability: 'Knowledge retrieval', coverage: '92%', latency: '1.9s', sla: '97.9%' },
];

const AgentManagementPage: React.FC<AgentManagementPageProps> = ({ mode = 'list' }) => {
  const headerTitle = mode === 'list' ? 'Agent 列表' : '能力管理';
  const headerTag = mode === 'list' ? 'Agent runtime overview' : 'Capability coverage';

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">AI Team</p>
          <h1 className="text-3xl font-bold mt-2">{headerTitle}</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-cyan-500/10 border border-cyan-500/20 rounded-lg text-cyan-300">
          <Bot className="w-4 h-4" />
          <span className="text-sm">{headerTag}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: 'Active agents', value: '24', icon: Bot },
          { label: 'Avg latency', value: '1.9s', icon: Gauge },
          { label: 'Skill coverage', value: '94%', icon: Layers3 },
          { label: 'Automation health', value: '98.4%', icon: Sparkles },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-300">
                <Icon className="w-4 h-4" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {mode === 'list' ? (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Runtime agents</h2>
            <span className="text-sm text-gray-400">Updated 1 min ago</span>
          </div>
          <div className="divide-y divide-gray-700">
            {agentRows.map((agent) => (
              <div key={agent.name} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                <div>
                  <p className="font-medium text-white">{agent.name}</p>
                  <p className="text-sm text-gray-400 mt-1">Domain: {agent.domain}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs ${agent.status === 'Healthy' ? 'bg-green-500/10 text-green-300' : agent.status === 'Monitoring' ? 'bg-yellow-500/10 text-yellow-300' : 'bg-blue-500/10 text-blue-300'}`}>
                    {agent.status}
                  </span>
                  <span className="text-gray-300">Latency {agent.latency}</span>
                  <span className="text-gray-300">Utilization {agent.utilization}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Capability matrix</h2>
            <span className="text-sm text-gray-400">SLA targets</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-5 py-3 text-gray-400">Capability</th>
                  <th className="px-5 py-3 text-gray-400">Coverage</th>
                  <th className="px-5 py-3 text-gray-400">Latency</th>
                  <th className="px-5 py-3 text-gray-400">SLA</th>
                </tr>
              </thead>
              <tbody>
                {capabilityRows.map((row) => (
                  <tr key={row.capability} className="border-t border-gray-700">
                    <td className="px-5 py-3 font-medium">{row.capability}</td>
                    <td className="px-5 py-3 text-gray-300">{row.coverage}</td>
                    <td className="px-5 py-3 text-gray-300">{row.latency}</td>
                    <td className="px-5 py-3 text-gray-300">{row.sla}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <div className="flex items-center gap-2 text-cyan-300 mb-3">
          <Zap className="w-4 h-4" />
          <span className="font-medium">Current optimization focus</span>
        </div>
        <p className="text-gray-300">
          Improve cross-agent handoff quality, reduce supplier matching latency, and standardize task orchestration policies for the next deployment window.
        </p>
      </div>
    </div>
  );
};

export default AgentManagementPage;
