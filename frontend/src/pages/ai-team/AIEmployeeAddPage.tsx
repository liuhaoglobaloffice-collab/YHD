import React, { useState } from 'react';
import { Bot, Briefcase, Save, Sparkles, UserPlus } from 'lucide-react';

const AIEmployeeAddPage: React.FC = () => {
  const [form, setForm] = useState({
    name: 'AI Ops Specialist',
    department: 'Operations',
    position: 'Operations Manager',
    agentType: 'workflow',
    status: 'active',
    description: 'Handles operational triage, alerts, and workflow handoff automation.',
  });

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-violet-300">AI Team</p>
          <h1 className="text-3xl font-bold mt-2">添加员工</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-violet-500/10 border border-violet-500/20 rounded-lg text-violet-300">
          <UserPlus className="w-4 h-4" />
          <span className="text-sm">Create AI employee</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.3fr_0.7fr] gap-6">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-sm text-gray-400 mb-2">员工名称</label>
              <input
                value={form.name}
                onChange={(e) => handleChange('name', e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">部门</label>
              <select
                value={form.department}
                onChange={(e) => handleChange('department', e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white"
              >
                <option>Operations</option>
                <option>Sales</option>
                <option>R&D</option>
                <option>Marketing</option>
                <option>Procurement</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">职位</label>
              <input
                value={form.position}
                onChange={(e) => handleChange('position', e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Agent 类型</label>
              <select
                value={form.agentType}
                onChange={(e) => handleChange('agentType', e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white"
              >
                <option value="workflow">Workflow Agent</option>
                <option value="supplier">Supplier Agent</option>
                <option value="analytics">Analytics Agent</option>
                <option value="support">Support Agent</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm text-gray-400 mb-2">职责说明</label>
              <textarea
                value={form.description}
                onChange={(e) => handleChange('description', e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white h-32"
              />
            </div>
          </div>

          <div className="flex justify-end mt-6">
            <button className="inline-flex items-center gap-2 px-5 py-3 bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors">
              <Save className="w-4 h-4" />
              保存员工
            </button>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
            <div className="flex items-center gap-2 text-violet-300 mb-4">
              <Bot className="w-4 h-4" />
              <span className="font-medium">Agent profile</span>
            </div>
            <div className="space-y-3 text-sm text-gray-300">
              <div className="flex justify-between"><span>Type</span><span>{form.agentType}</span></div>
              <div className="flex justify-between"><span>Status</span><span className="text-green-300">{form.status}</span></div>
              <div className="flex justify-between"><span>Department</span><span>{form.department}</span></div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
            <div className="flex items-center gap-2 text-violet-300 mb-4">
              <Briefcase className="w-4 h-4" />
              <span className="font-medium">Setup checklist</span>
            </div>
            <ul className="space-y-2 text-sm text-gray-300">
              <li className="flex items-start gap-2"><span className="mt-1 text-green-300">●</span> Assign routing policy</li>
              <li className="flex items-start gap-2"><span className="mt-1 text-green-300">●</span> Define task SLA</li>
              <li className="flex items-start gap-2"><span className="mt-1 text-green-300">●</span> Enable access scope</li>
              <li className="flex items-start gap-2"><span className="mt-1 text-green-300">●</span> Validate onboarding</li>
            </ul>
          </div>

          <div className="bg-gradient-to-br from-violet-500/10 to-cyan-500/10 border border-violet-500/20 rounded-xl p-5">
            <div className="flex items-center gap-2 text-cyan-300 mb-3">
              <Sparkles className="w-4 h-4" />
              <span className="font-medium">Assistant suggestion</span>
            </div>
            <p className="text-sm text-gray-300">
              Recommended to enable workflow handoff and supplier sync tasks for this employee during the first onboarding cycle.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default AIEmployeeAddPage;
