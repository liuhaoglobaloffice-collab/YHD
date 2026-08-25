import React from 'react';
import { CheckCircle2, Clock3, PlusCircle, Workflow } from 'lucide-react';

interface WorkflowDesignPageProps {
  mode?: 'list' | 'create';
}

const workflowRows = [
  { name: 'Supplier intake flow', owner: 'Ops Platform', status: 'Live', duration: '4 min' },
  { name: 'Customer onboarding', owner: 'Sales Ops', status: 'Draft', duration: '7 min' },
  { name: 'AI support triage', owner: 'Service Desk', status: 'Review', duration: '3 min' },
];

const WorkflowDesignPage: React.FC<WorkflowDesignPageProps> = ({ mode = 'list' }) => {
  if (mode === 'create') {
    return (
      <div className="p-6 space-y-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-blue-300">Workflow</p>
            <h1 className="text-3xl font-bold mt-2">创建流程</h1>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-300">
            <PlusCircle className="w-4 h-4" />
            <span className="text-sm">New design</span>
          </div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-5">
          <div>
            <label className="block text-sm text-gray-400 mb-2">流程名称</label>
            <input className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white" placeholder="例如：订单自动化审核" />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">所属部门</label>
            <select className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white">
              <option>Operations</option>
              <option>Sales</option>
              <option>Procurement</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">触发条件</label>
            <textarea className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white h-28" placeholder="描述流程触发器、输入条件和关键节点" />
          </div>
          <div className="flex justify-end">
            <button className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">保存流程</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-indigo-300">Workflow</p>
          <h1 className="text-3xl font-bold mt-2">流程列表</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-300">
          <Workflow className="w-4 h-4" />
          <span className="text-sm">Design center</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Active flows', value: '18', icon: CheckCircle2 },
          { label: 'Drafts', value: '6', icon: Clock3 },
          { label: 'Avg step time', value: '3.6m', icon: Workflow },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-300">
                <Icon className="w-4 h-4" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Workflow library</h2>
          <span className="text-sm text-gray-400">Latest design</span>
        </div>
        <div className="divide-y divide-gray-700">
          {workflowRows.map((row) => (
            <div key={row.name} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
              <div>
                <p className="font-medium text-white">{row.name}</p>
                <p className="text-sm text-gray-400 mt-1">Owner: {row.owner}</p>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <span className={`px-2 py-1 rounded-full text-xs ${row.status === 'Live' ? 'bg-green-500/10 text-green-300' : row.status === 'Review' ? 'bg-yellow-500/10 text-yellow-300' : 'bg-blue-500/10 text-blue-300'}`}>
                  {row.status}
                </span>
                <span className="text-gray-300">Duration {row.duration}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default WorkflowDesignPage;
