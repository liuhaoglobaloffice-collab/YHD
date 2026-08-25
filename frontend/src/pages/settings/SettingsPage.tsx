import React from 'react';
import { Activity, KeyRound, Lock, Shield } from 'lucide-react';

interface SettingsPageProps {
  section?: 'general' | 'security' | 'users' | 'roles' | 'permissions' | 'audit';
}

const generalCards = [
  { label: 'System name', value: 'LiuHao AI OS' },
  { label: 'Environment', value: 'Production Preview' },
  { label: 'Timezone', value: 'Asia/Shanghai' },
  { label: 'Version', value: 'Y1.0 Phase10' },
];

const securityCards = [
  { label: 'MFA', value: 'Enabled', icon: Shield },
  { label: 'Sessions', value: '32 active', icon: Lock },
  { label: 'API Keys', value: '14 managed', icon: KeyRound },
  { label: 'Last Audit', value: '2h ago', icon: Activity },
];

const userRows = [
  { name: 'admin', email: 'admin@liuhao.ai', role: 'Owner', status: 'Active' },
  { name: 'ops', email: 'ops@liuhao.ai', role: 'Operator', status: 'Active' },
  { name: 'analyst', email: 'analyst@liuhao.ai', role: 'Analyst', status: 'Pending' },
];

const roleRows = [
  { name: 'Owner', scope: 'All modules', members: '1' },
  { name: 'Operator', scope: 'Operations', members: '8' },
  { name: 'Analyst', scope: 'Read-only', members: '4' },
];

const permissionRows = [
  { name: 'supplier.read', type: 'Read', scope: 'Supplier' },
  { name: 'workflow.execute', type: 'Execute', scope: 'Workflow' },
  { name: 'ai.provider.manage', type: 'Manage', scope: 'AI Provider' },
];

const auditRows = [
  { time: '2026-08-24 12:40', actor: 'admin', action: 'Updated security policy', result: 'Success' },
  { time: '2026-08-24 11:55', actor: 'ops', action: 'Restarted workflow tasks', result: 'Success' },
  { time: '2026-08-24 09:20', actor: 'analyst', action: 'Read supplier detail', result: 'Success' },
];

const SettingsPage: React.FC<SettingsPageProps> = ({ section = 'general' }) => {
  const titleMap = {
    general: '通用设置',
    security: '安全设置',
    users: '用户列表',
    roles: '角色管理',
    permissions: '权限管理',
    audit: '审计日志',
  };

  const renderSection = () => {
    switch (section) {
      case 'security':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {securityCards.map(({ label, value, icon: Icon }) => (
              <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-400">{label}</p>
                    <p className="text-xl font-bold mt-2">{value}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-300">
                    <Icon className="w-5 h-5" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
      case 'users':
        return (
          <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-900">
                  <tr>
                    <th className="px-5 py-3 text-gray-400">User</th>
                    <th className="px-5 py-3 text-gray-400">Email</th>
                    <th className="px-5 py-3 text-gray-400">Role</th>
                    <th className="px-5 py-3 text-gray-400">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {userRows.map((row) => (
                    <tr key={row.name} className="border-t border-gray-700">
                      <td className="px-5 py-3 font-medium">{row.name}</td>
                      <td className="px-5 py-3 text-gray-300">{row.email}</td>
                      <td className="px-5 py-3 text-gray-300">{row.role}</td>
                      <td className="px-5 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs ${row.status === 'Active' ? 'bg-green-500/10 text-green-300' : 'bg-yellow-500/10 text-yellow-300'}`}>
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      case 'roles':
        return (
          <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-5 py-3 text-gray-400">Role</th>
                  <th className="px-5 py-3 text-gray-400">Scope</th>
                  <th className="px-5 py-3 text-gray-400">Members</th>
                </tr>
              </thead>
              <tbody>
                {roleRows.map((row) => (
                  <tr key={row.name} className="border-t border-gray-700">
                    <td className="px-5 py-3 font-medium">{row.name}</td>
                    <td className="px-5 py-3 text-gray-300">{row.scope}</td>
                    <td className="px-5 py-3 text-gray-300">{row.members}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      case 'permissions':
        return (
          <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-5 py-3 text-gray-400">Permission</th>
                  <th className="px-5 py-3 text-gray-400">Type</th>
                  <th className="px-5 py-3 text-gray-400">Scope</th>
                </tr>
              </thead>
              <tbody>
                {permissionRows.map((row) => (
                  <tr key={row.name} className="border-t border-gray-700">
                    <td className="px-5 py-3 font-medium">{row.name}</td>
                    <td className="px-5 py-3 text-gray-300">{row.type}</td>
                    <td className="px-5 py-3 text-gray-300">{row.scope}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      case 'audit':
        return (
          <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-5 py-3 text-gray-400">Time</th>
                  <th className="px-5 py-3 text-gray-400">Actor</th>
                  <th className="px-5 py-3 text-gray-400">Action</th>
                  <th className="px-5 py-3 text-gray-400">Result</th>
                </tr>
              </thead>
              <tbody>
                {auditRows.map((row, index) => (
                  <tr key={`${row.time}-${index}`} className="border-t border-gray-700">
                    <td className="px-5 py-3 text-gray-300">{row.time}</td>
                    <td className="px-5 py-3 text-gray-300">{row.actor}</td>
                    <td className="px-5 py-3 text-gray-300">{row.action}</td>
                    <td className="px-5 py-3">
                      <span className="px-2 py-1 rounded-full bg-green-500/10 text-green-300 text-xs">{row.result}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      case 'general':
      default:
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {generalCards.map((card) => (
              <div key={card.label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
                <p className="text-sm text-gray-400">{card.label}</p>
                <p className="text-xl font-bold mt-2">{card.value}</p>
              </div>
            ))}
          </div>
        );
    }
  };

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">System</p>
          <h1 className="text-3xl font-bold mt-2">{titleMap[section]}</h1>
        </div>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium">
          Save changes
        </button>
      </div>

      {renderSection()}
    </div>
  );
};

export default SettingsPage;
