import React from 'react';
import { Activity, ArrowUpRight, Gauge, TrendingUp, Users } from 'lucide-react';

const performanceCards = [
  { label: 'Avg efficiency', value: '92%', trend: '+7%' },
  { label: 'Task completion', value: '96%', trend: '+5%' },
  { label: 'Customer response', value: '1.8s', trend: '-0.4s' },
  { label: 'Satisfaction', value: '4.8/5', trend: '+0.3' },
];

const teamRows = [
  { name: 'AI Ops Specialist', department: 'Operations', score: '94%', status: 'Excellent' },
  { name: 'Supplier Negotiator', department: 'Procurement', score: '89%', status: 'Strong' },
  { name: 'AI Sales Copilot', department: 'Sales', score: '87%', status: 'Strong' },
  { name: 'Research Analyst', department: 'R&D', score: '82%', status: 'Stable' },
];

const AIEmployeePerformancePage: React.FC = () => {
  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">AI Team</p>
          <h1 className="text-3xl font-bold mt-2">绩效管理</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-cyan-500/10 border border-cyan-500/20 rounded-lg text-cyan-300">
          <TrendingUp className="w-4 h-4" />
          <span className="text-sm">Performance dashboard</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {performanceCards.map(({ label, value, trend }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-300">
                <ArrowUpRight className="w-4 h-4" />
              </div>
            </div>
            <p className="mt-3 text-xs text-cyan-300">{trend}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[0.9fr_1.1fr] gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
          <div className="flex items-center gap-2 text-cyan-300 mb-4">
            <Gauge className="w-4 h-4" />
            <span className="font-medium">Operational pulse</span>
          </div>
          <div className="space-y-4">
            {[
              { label: 'Case handling', value: '87%', width: '87%' },
              { label: 'Task orchestration', value: '91%', width: '91%' },
              { label: 'Precision', value: '94%', width: '94%' },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-300">{item.label}</span>
                  <span className="text-white">{item.value}</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500" style={{ width: item.width }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Team performance</h2>
            <span className="text-sm text-gray-400">Updated 10m ago</span>
          </div>
          <div className="divide-y divide-gray-700">
            {teamRows.map((row) => (
              <div key={row.name} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                <div>
                  <p className="font-medium text-white">{row.name}</p>
                  <p className="text-sm text-gray-400 mt-1">Department: {row.department}</p>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <span className="text-gray-300">Score {row.score}</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${row.status === 'Excellent' ? 'bg-green-500/10 text-green-300' : row.status === 'Strong' ? 'bg-blue-500/10 text-blue-300' : 'bg-yellow-500/10 text-yellow-300'}`}>
                    {row.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <div className="flex items-center gap-2 text-cyan-300 mb-3">
          <Users className="w-4 h-4" />
          <span className="font-medium">Recommended action</span>
        </div>
        <p className="text-gray-300">
          Prioritize coaching for the lower-scoring intelligence units and continue scaling the highest-performing operational agents for production tasks.
        </p>
      </div>
    </div>
  );
};

export default AIEmployeePerformancePage;
