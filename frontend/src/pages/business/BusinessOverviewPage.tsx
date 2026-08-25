import React from 'react';
import { ArrowUpRight, Briefcase, DollarSign, FileText, Rocket, Target, TrendingUp, Users } from 'lucide-react';

interface BusinessOverviewPageProps {
  section?: 'research' | 'sales' | 'operations';
  title?: string;
}

const researchCards = [
  { label: 'Active R&D projects', value: '14', trend: '+12%' },
  { label: 'Innovation backlog', value: '7', trend: '+3%' },
  { label: 'Prototype readiness', value: '81%', trend: '+9%' },
  { label: 'Delivery confidence', value: '88%', trend: '+5%' },
];

const salesCards = [
  { label: 'Qualified leads', value: '328', trend: '+18%' },
  { label: 'Open opportunities', value: '47', trend: '+11%' },
  { label: 'Win rate', value: '31%', trend: '+4%' },
  { label: 'Pipeline value', value: '$2.4M', trend: '+21%' },
];

const operationsCards = [
  { label: 'Daily tasks', value: '186', trend: '+6%' },
  { label: 'On-time delivery', value: '92%', trend: '+4%' },
  { label: 'Escalations', value: '8', trend: '-2' },
  { label: 'SLA coverage', value: '96%', trend: '+3%' },
];

const sectionMap = {
  research: {
    title: '研发管理',
    icon: Rocket,
    rows: [
      { name: 'AI Agent Research Engine', owner: 'R&D Lab', status: 'On track', progress: '82%' },
      { name: 'Supplier Intelligence upgrade', owner: 'Supplier Team', status: 'Review', progress: '64%' },
      { name: 'Workflow optimization v2', owner: 'Ops Platform', status: 'In pilot', progress: '71%' },
    ],
    metrics: researchCards,
  },
  sales: {
    title: '销售管理',
    icon: Target,
    rows: [
      { name: 'Enterprise AI partner', owner: 'North America', status: 'Qualified', progress: '74%' },
      { name: 'Custom workflow expansion', owner: 'EMEA', status: 'Proposal', progress: '62%' },
      { name: 'Supplier enablement bundle', owner: 'APAC', status: 'Negotiation', progress: '58%' },
    ],
    metrics: salesCards,
  },
  operations: {
    title: '日常运营',
    icon: TrendingUp,
    rows: [
      { name: 'Daily operations review', owner: 'Ops Office', status: 'Healthy', progress: '90%' },
      { name: 'Support queue routing', owner: 'Service Desk', status: 'Monitoring', progress: '76%' },
      { name: 'Supplier response SLA', owner: 'Procurement', status: 'Stable', progress: '88%' },
    ],
    metrics: operationsCards,
  },
};

const BusinessOverviewPage: React.FC<BusinessOverviewPageProps> = ({ section = 'operations', title }) => {
  const config = sectionMap[section];
  const Icon = config.icon;

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">Business</p>
          <h1 className="text-3xl font-bold mt-2">{title || config.title}</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-300">
          <Icon className="w-4 h-4" />
          <span className="text-sm">Operations view</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {config.metrics.map(({ label, value, trend }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-green-500/10 text-green-300">
                <ArrowUpRight className="w-4 h-4" />
              </div>
            </div>
            <p className="mt-3 text-xs text-green-300">{trend} vs last cycle</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Current initiatives</h2>
          <span className="text-sm text-gray-400">Updated 5 min ago</span>
        </div>

        <div className="divide-y divide-gray-700">
          {config.rows.map((row) => (
            <div key={row.name} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
              <div>
                <p className="font-medium text-white">{row.name}</p>
                <p className="text-sm text-gray-400 mt-1">Owner: {row.owner}</p>
              </div>

              <div className="flex items-center gap-4">
                <span className="px-2 py-1 rounded-full text-xs bg-blue-500/10 text-blue-300">
                  {row.status}
                </span>
                <div className="w-40">
                  <div className="h-2 rounded-full bg-gray-700 overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-blue-500 to-green-400" style={{ width: row.progress }} />
                  </div>
                </div>
                <span className="text-sm text-gray-300 w-12 text-right">{row.progress}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default BusinessOverviewPage;
