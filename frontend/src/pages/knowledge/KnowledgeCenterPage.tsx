import React from 'react';
import { BookOpen, BrainCircuit, Database, FolderTree, Search, Zap } from 'lucide-react';

interface KnowledgeCenterPageProps {
  section?: 'documents-list' | 'documents-upload' | 'documents-categories' | 'memory-search' | 'memory-manage' | 'brain-entities' | 'brain-graph';
}

const documentRows = [
  { name: 'Supplier onboarding memo', owner: 'Ops', category: 'Procurement', updated: '2h ago' },
  { name: 'AI provider policy brief', owner: 'Platform', category: 'Platform', updated: '5h ago' },
  { name: 'Workflow runbook', owner: 'Engineering', category: 'Automation', updated: '1d ago' },
];

const memoryRows = [
  { name: 'Supplier relationship memory', status: 'Synced', quality: '96%' },
  { name: 'Market opportunity summary', status: 'Indexed', quality: '91%' },
  { name: 'Customer interaction recap', status: 'Needs review', quality: '88%' },
];

const brainRows = [
  { name: 'LiuHao supply graph', relation: '12 linked nodes', maturity: 'Healthy' },
  { name: 'Risk and opportunity graph', relation: '8 linked nodes', maturity: 'Monitoring' },
  { name: 'Customer service map', relation: '5 linked nodes', maturity: 'Draft' },
];

const sectionMap = {
  'documents-list': {
    title: '文档列表',
    icon: BookOpen,
    cards: [
      { label: 'Documents', value: '124', detail: '+12 this week' },
      { label: 'Active tags', value: '18', detail: '+2 new' },
      { label: 'Indexed', value: '91%', detail: '+5%' },
      { label: 'Storage', value: '64 GB', detail: '+8 GB' },
    ],
    rows: documentRows,
  },
  'documents-upload': {
    title: '上传文档',
    icon: FolderTree,
    cards: [
      { label: 'Uploads today', value: '15', detail: '8 processed' },
      { label: 'Queued', value: '4', detail: '2 high priority' },
      { label: 'OCR success', value: '96%', detail: '+3%' },
      { label: 'Approval pending', value: '5', detail: '2 due today' },
    ],
    rows: documentRows,
  },
  'documents-categories': {
    title: '分类管理',
    icon: FolderTree,
    cards: [
      { label: 'Categories', value: '12', detail: '3 updated' },
      { label: 'Shared tags', value: '37', detail: '6 pinned' },
      { label: 'Policy docs', value: '9', detail: '2 new' },
      { label: 'Unclassified', value: '4', detail: '1 urgent' },
    ],
    rows: documentRows,
  },
  'memory-search': {
    title: '知识检索',
    icon: Search,
    cards: [
      { label: 'Indexed entries', value: '18.3k', detail: '+400' },
      { label: 'Avg recall', value: '92%', detail: '+4%' },
      { label: 'Search latency', value: '0.6s', detail: '-0.2s' },
      { label: 'Top intent', value: 'Supplier', detail: '41%' },
    ],
    rows: memoryRows,
  },
  'memory-manage': {
    title: '记忆管理',
    icon: Database,
    cards: [
      { label: 'Memory groups', value: '23', detail: '+3' },
      { label: 'Retention', value: '180d', detail: 'policy matched' },
      { label: 'Conflicts', value: '2', detail: '1 resolved' },
      { label: 'Quality score', value: '93%', detail: '+6%' },
    ],
    rows: memoryRows,
  },
  'brain-entities': {
    title: '实体管理',
    icon: BrainCircuit,
    cards: [
      { label: 'Entities', value: '682', detail: '+46' },
      { label: 'Core concepts', value: '38', detail: '+4' },
      { label: 'Linked to ops', value: '91%', detail: '+7%' },
      { label: 'New discoveries', value: '5', detail: '2 significant' },
    ],
    rows: brainRows,
  },
  'brain-graph': {
    title: '关系图谱',
    icon: Zap,
    cards: [
      { label: 'Graphs', value: '7', detail: '+1' },
      { label: 'Connections', value: '1.8k', detail: '+120' },
      { label: 'Map health', value: '94%', detail: '+2%' },
      { label: 'Cross-links', value: '41%', detail: '+8%' },
    ],
    rows: brainRows,
  },
};

const KnowledgeCenterPage: React.FC<KnowledgeCenterPageProps> = ({ section = 'documents-list' }) => {
  const config = sectionMap[section];
  const Icon = config.icon;

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-emerald-300">Knowledge</p>
          <h1 className="text-3xl font-bold mt-2">{config.title}</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-300">
          <Icon className="w-4 h-4" />
          <span className="text-sm">Knowledge center</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {config.cards.map(({ label, value, detail }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="text-2xl font-bold mt-2">{value}</p>
              </div>
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-300">
                <Icon className="w-4 h-4" />
              </div>
            </div>
            <p className="mt-3 text-xs text-emerald-300">{detail}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Current records</h2>
          <span className="text-sm text-gray-400">Last sync 3 min ago</span>
        </div>
        <div className="divide-y divide-gray-700">
          {config.rows.map((row: any) => (
            <div key={row.name} className="px-5 py-4 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
              <div>
                <p className="font-medium text-white">{row.name}</p>
                <p className="text-sm text-gray-400 mt-1">
                  {row.category ? `Category: ${row.category}` : row.status ? `Status: ${row.status}` : `Relation: ${row.relation}`}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                {row.owner && <span className="text-gray-300">Owner {row.owner}</span>}
                {row.updated && <span className="text-gray-300">Updated {row.updated}</span>}
                {row.quality && <span className="px-2 py-1 rounded-full bg-green-500/10 text-green-300">Quality {row.quality}</span>}
                {row.maturity && <span className={`px-2 py-1 rounded-full text-xs ${row.maturity === 'Healthy' ? 'bg-green-500/10 text-green-300' : row.maturity === 'Monitoring' ? 'bg-yellow-500/10 text-yellow-300' : 'bg-blue-500/10 text-blue-300'}`}>{row.maturity}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default KnowledgeCenterPage;
