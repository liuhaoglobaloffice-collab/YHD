import React from 'react';
import { ArrowUpRight, Building2, KeyRound, Lock, Shield, Users } from 'lucide-react';

interface TenantManagementPageProps {
  section?: 'accounts-main' | 'accounts-sub' | 'tokens-pool' | 'tokens-usage' | 'tokens-stealth' | 'permissions';
  title?: string;
}

const accountRows = [
  { name: 'Main Tenant', owner: 'admin', region: 'China East', status: 'Healthy', quota: '98%' },
  { name: 'Operations Branch', owner: 'ops', region: 'China South', status: 'Active', quota: '73%' },
  { name: 'Supplier Network', owner: 'supplier-admin', region: 'Global', status: 'Monitoring', quota: '64%' },
];

const subAccountRows = [
  { name: 'AI Ops', owner: 'ops-ai', role: 'Operator', status: 'Active', lastLogin: '2m ago' },
  { name: 'Procurement', owner: 'procurement', role: 'Analyst', status: 'Active', lastLogin: '9m ago' },
  { name: 'Customer Success', owner: 'success', role: 'Manager', status: 'Pending', lastLogin: '1d ago' },
];

const tokenPoolRows = [
  { name: 'Supplier API', usage: '4.2k / 10k', health: 'Healthy', rotation: '12d' },
  { name: 'Workflow Engine', usage: '7.1k / 12k', health: 'Monitoring', rotation: '9d' },
  { name: 'AI Gateway', usage: '2.9k / 8k', health: 'Healthy', rotation: '15d' },
];

const tokenUsageRows = [
  { label: 'Daily token volume', value: '82.4k', trend: '+12%' },
  { label: 'Peak load window', value: '09:30–11:00', trend: '+8%' },
  { label: 'Consumed by AI', value: '61%', trend: '+5%' },
  { label: 'Reserved budget', value: '24%', trend: '-3%' },
];

const stealthRows = [
  { name: 'Stealth dispatch', target: 'Workflow Worker A', mode: 'Hidden', status: 'Enabled' },
  { name: 'Cross-tenant relay', target: 'Supplier Sync', mode: 'Masked', status: 'Enabled' },
  { name: 'Shadow queue', target: 'Audit Trail', mode: 'Private', status: 'Standby' },
];

const permissionRows = [
  { policy: 'tenant.read', scope: 'Tenant overview', grant: 'All roles' },
  { policy: 'tenant.token.manage', scope: 'Token pool', grant: 'Operator' },
  { policy: 'tenant.permission.audit', scope: 'Permissions & audit', grant: 'Owner' },
];

const sectionMap = {
  'accounts-main': {
    title: '主账号管理',
    icon: Building2,
    cards: [
      { label: 'Active accounts', value: '12', trend: '+2' },
      { label: 'Primary tenants', value: '4', trend: '+1' },
      { label: 'Healthy status', value: '91%', trend: '+6%' },
      { label: 'Security posture', value: 'A+', trend: '+2%' },
    ],
    rows: accountRows,
  },
  'accounts-sub': {
    title: '子账号管理',
    icon: Users,
    cards: [
      { label: 'Sub accounts', value: '38', trend: '+7' },
      { label: 'Pending invites', value: '5', trend: '+2' },
      { label: 'Inactive', value: '3', trend: '-1' },
      { label: 'Avg. login', value: '4.8h', trend: '+0.3h' },
    ],
    rows: subAccountRows,
  },
  'tokens-pool': {
    title: 'Token池管理',
    icon: KeyRound,
    cards: [
      { label: 'Managed keys', value: '18', trend: '+3' },
      { label: 'Rotating soon', value: '5', trend: '+1' },
      { label: 'Valid rate', value: '99.2%', trend: '+0.4%' },
      { label: 'Active pools', value: '6', trend: '+1' },
    ],
    rows: tokenPoolRows,
  },
  'tokens-usage': {
    title: '使用统计',
    icon: ArrowUpRight,
    cards: tokenUsageRows,
    rows: tokenUsageRows,
  },
  'tokens-stealth': {
    title: '隐秘调度',
    icon: Shield,
    cards: [
      { label: 'Stealth jobs', value: '7', trend: '+2' },
      { label: 'Masked dispatch', value: '93%', trend: '+5%' },
      { label: 'Failure rate', value: '0.8%', trend: '-0.2%' },
      { label: 'Local isolation', value: '99.6%', trend: '+0.3%' },
    ],
    rows: stealthRows,
  },
  permissions: {
    title: '权限配置',
    icon: Lock,
    cards: [
      { label: 'Policies', value: '26', trend: '+4' },
      { label: 'Owner rules', value: '6', trend: '+1' },
      { label: 'Operator scope', value: '14', trend: '+2' },
      { label: 'Audit coverage', value: '100%', trend: '+3%' },
    ],
    rows: permissionRows,
  },
};

const TenantManagementPage: React.FC<TenantManagementPageProps> = ({
  section = 'accounts-main',
  title,
}) => {
  const config = sectionMap[section];
  const Icon = config.icon;

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-purple-300">Tenant</p>
          <h1 className="text-3xl font-bold mt-2">{title || config.title}</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-purple-500/10 border border-purple-500/20 rounded-lg text-purple-300">
          <Icon className="w-4 h-4" />
          <span className="text-sm">Multi-tenant management</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {config.cards.map(({ label, value, trend }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-300">
                <ArrowUpRight className="w-4 h-4" />
              </div>
            </div>
            <p className="mt-3 text-xs text-purple-300">{trend} vs last cycle</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Management details</h2>
          <span className="text-sm text-gray-400">Last refreshed 2 min ago</span>
        </div>

        {section === 'tokens-usage' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 p-5">
            {config.rows.map((row: any) => (
              <div key={row.label} className="bg-gray-900 border border-gray-700 rounded-xl p-4">
                <p className="text-sm text-gray-400">{row.label}</p>
                <p className="text-2xl font-bold mt-2">{row.value}</p>
                <p className="mt-3 text-xs text-purple-300">{row.trend}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {config.rows.map((row: any) => (
              <div key={row.name || row.policy} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                <div>
                  <p className="font-medium text-white">{row.name || row.policy}</p>
                  <p className="text-sm text-gray-400 mt-1">
                    {row.owner ? `Owner: ${row.owner}` : row.scope ? `Scope: ${row.scope}` : row.target ? `Target: ${row.target}` : ''}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-sm">
                  {row.region && (
                    <span className="px-2 py-1 rounded-full bg-blue-500/10 text-blue-300">{row.region}</span>
                  )}
                  {row.role && (
                    <span className="px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-300">{row.role}</span>
                  )}
                  {row.usage && (
                    <span className="px-2 py-1 rounded-full bg-indigo-500/10 text-indigo-300">{row.usage}</span>
                  )}
                  {row.grant && (
                    <span className="px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-300">{row.grant}</span>
                  )}
                  {row.status && (
                    <span className={`px-2 py-1 rounded-full text-xs ${row.status === 'Healthy' || row.status === 'Active' || row.status === 'Enabled' ? 'bg-green-500/10 text-green-300' : row.status === 'Monitoring' || row.status === 'Pending' ? 'bg-yellow-500/10 text-yellow-300' : 'bg-gray-500/10 text-gray-300'}`}>
                      {row.status}
                    </span>
                  )}
                  {row.quota && <span className="text-gray-300">Quota {row.quota}</span>}
                  {row.rotation && <span className="text-gray-300">Rotation {row.rotation}</span>}
                  {row.lastLogin && <span className="text-gray-300">Last login {row.lastLogin}</span>}
                  {row.mode && <span className="text-gray-300">Mode {row.mode}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TenantManagementPage;
