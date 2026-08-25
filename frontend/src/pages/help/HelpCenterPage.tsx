import React from 'react';
import { BookOpen, Headphones, PlayCircle, ShieldCheck } from 'lucide-react';

interface HelpCenterPageProps {
  section?: 'docs' | 'videos' | 'support';
}

const docRows = [
  { title: 'Getting started', category: 'Onboarding', updated: '2d ago' },
  { title: 'Supplier operations guide', category: 'Operations', updated: '5d ago' },
  { title: 'AI provider rollout notes', category: 'Platform', updated: '1w ago' },
];

const videoRows = [
  { title: 'Workflow overview', duration: '08:42', level: 'Beginner' },
  { title: 'Business dashboard walkthrough', duration: '12:15', level: 'Intermediate' },
  { title: 'Operations and alert tuning', duration: '06:33', level: 'Advanced' },
];

const supportRows = [
  { title: 'Production issue escalation', owner: 'Ops desk', status: 'Open' },
  { title: 'Feature request pipeline', owner: 'Product', status: 'In review' },
  { title: 'Security policy consultation', owner: 'Security', status: 'Resolved' },
];

const HelpCenterPage: React.FC<HelpCenterPageProps> = ({ section = 'docs' }) => {
  const titleMap = {
    docs: '使用文档',
    videos: '视频教程',
    support: '技术支持',
  };

  const iconMap = {
    docs: BookOpen,
    videos: PlayCircle,
    support: Headphones,
  };

  const Icon = iconMap[section];

  const rows = section === 'docs' ? docRows : section === 'videos' ? videoRows : supportRows;

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-amber-300">Help</p>
          <h1 className="text-3xl font-bold mt-2">{titleMap[section]}</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-300">
          <Icon className="w-4 h-4" />
          <span className="text-sm">Support center</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Docs', value: '24', icon: BookOpen },
          { label: 'Videos', value: '9', icon: PlayCircle },
          { label: 'Support cases', value: '13', icon: ShieldCheck },
        ].map(({ label, value, icon: CardIcon }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-300">
                <CardIcon className="w-4 h-4" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Latest content</h2>
          <span className="text-sm text-gray-400">Updated today</span>
        </div>
        <div className="divide-y divide-gray-700">
          {rows.map((row: any) => (
            <div key={row.title} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
              <div>
                <p className="font-medium text-white">{row.title}</p>
                <p className="text-sm text-gray-400 mt-1">
                  {row.category ? `Category: ${row.category}` : row.duration ? `Duration: ${row.duration}` : `Owner: ${row.owner}`}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                {row.updated && <span className="text-gray-300">Updated {row.updated}</span>}
                {row.level && <span className="px-2 py-1 rounded-full bg-blue-500/10 text-blue-300">{row.level}</span>}
                {row.status && (
                  <span className={`px-2 py-1 rounded-full text-xs ${row.status === 'Open' ? 'bg-red-500/10 text-red-300' : row.status === 'Resolved' ? 'bg-green-500/10 text-green-300' : 'bg-yellow-500/10 text-yellow-300'}`}>
                    {row.status}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HelpCenterPage;
