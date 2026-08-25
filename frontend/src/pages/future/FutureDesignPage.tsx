import React from 'react';
import { Layers3, Palette, Sparkles, Type, Wand2 } from 'lucide-react';

const palette = [
  { name: 'Cyan Core', value: '#22d3ee' },
  { name: 'Violet Pulse', value: '#8b5cf6' },
  { name: 'Fuchsia Signal', value: '#d946ef' },
  { name: 'Emerald Success', value: '#34d399' },
  { name: 'Amber Warning', value: '#fbbf24' },
];

const tokens = [
  { label: 'Typography', value: 'Inter / Noto Sans SC / Microsoft YaHei', icon: Type },
  { label: 'Surface', value: 'Glassmorphism + dark gradients', icon: Layers3 },
  { label: 'Motion', value: 'Reactive transitions / pulse / hologram', icon: Wand2 },
  { label: 'Theme', value: 'Future enterprise, bilingual first', icon: Sparkles },
];

const featureRows = [
  { title: '中英双语 UI', description: '支持中文、英文、粤语/国语语音场景切换。' },
  { title: '企业未来感', description: '通过玻璃拟态、流光、等距网格与深色工作台提升品牌辨识。' },
  { title: '跨终端一致性', description: '桌面端、移动端和操作台共用统一视觉语言。' },
  { title: 'AI 辅助动效', description: '通过轻微微动画提升 AI 助手、工作流和状态反馈。' },
];

const FutureDesignPage: React.FC = () => {
  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Design System</p>
          <h1 className="text-3xl font-bold mt-2">未来风品牌与视觉语言</h1>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-200">
          <Palette className="w-4 h-4" />
          Future UI Language
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-gray-700 bg-gray-800 p-5">
          <h2 className="text-xl font-semibold">品牌色板</h2>
          <div className="mt-5 grid grid-cols-2 md:grid-cols-5 gap-3">
            {palette.map((color) => (
              <div key={color.name}>
                <div className="h-16 rounded-xl border border-white/10" style={{ background: color.value }} />
                <p className="mt-2 text-xs text-gray-300">{color.name}</p>
                <p className="text-[11px] text-gray-500">{color.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-gray-700 bg-gray-800 p-5">
          <h2 className="text-xl font-semibold">设计令牌</h2>
          <div className="mt-5 space-y-3">
            {tokens.map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center gap-3 rounded-xl border border-gray-700 bg-slate-950/40 p-3">
                <div className="rounded-xl bg-cyan-500/10 p-2 text-cyan-200"><Icon className="w-4 h-4" /></div>
                <div>
                  <p className="text-sm text-gray-400">{label}</p>
                  <p className="text-sm font-medium">{value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-700 bg-gray-800 p-5">
        <h2 className="text-xl font-semibold">核心视觉原则</h2>
        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {featureRows.map((row) => (
            <div key={row.title} className="rounded-xl border border-gray-700 bg-slate-950/40 p-4">
              <p className="font-medium text-white">{row.title}</p>
              <p className="mt-2 text-sm leading-6 text-gray-300">{row.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-dashed border-violet-500/30 bg-violet-500/5 p-5">
        <p className="text-sm uppercase tracking-[0.2em] text-violet-300">Brand direction</p>
        <h2 className="mt-2 text-2xl font-semibold">Future enterprise: intelligent, calm, high-trust</h2>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-gray-200">
          视觉系统的核心目标是让用户感受到“强大、可信、智能、专业”，同时保持简洁与可操作性。
          通过冷色主基调、柔和灯光与高对比信息层，提升企业管理系统的未来感，而不是单纯追求炫技。
        </p>
      </div>
    </div>
  );
};

export default FutureDesignPage;
