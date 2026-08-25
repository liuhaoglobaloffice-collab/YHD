import React from 'react';
import {
  ArrowRight,
  BellRing,
  Briefcase,
  Building2,
  CheckCircle2,
  Cpu,
  Globe,
  LayoutGrid,
  Monitor,
  Rocket,
  Smartphone,
  Sparkles,
  TabletSmartphone,
  Volume2,
} from 'lucide-react';

interface FuturePlatformPageProps {
  section?: 'platform' | 'desktop' | 'mobile' | 'console';
}

const roadmap = [
  {
    phase: 'P0',
    title: '主线稳定',
    items: ['稳定后端基线', '运营核心流程', '认证与权限', '供应链与工作流'],
  },
  {
    phase: 'P1',
    title: '协同体验',
    items: ['桌面端工作台', '移动端执行面', '中英文/粤语/国语支持', 'Jarvis 语音助手'],
  },
  {
    phase: 'P2',
    title: '扩展生态',
    items: ['多端同步', '模式化操作台', 'AI 语音翻译', '定制主题与品牌系统'],
  },
];

const platformCards = [
  {
    icon: LayoutGrid,
    title: '桌面应用',
    description: '高密度工作台、操作中心、任务看板、导航简洁，可对接企业级大屏与管理端。',
    accent: 'from-cyan-500/20 to-blue-500/10',
    bullets: ['跨平台 Electron / Tauri', '大屏工作台', '快捷命令中心'],
  },
  {
    icon: Smartphone,
    title: '移动应用',
    description: '面向现场运营、审批、通知与语音指令的移动端体验，支持快速决策。',
    accent: 'from-fuchsia-500/20 to-violet-500/10',
    bullets: ['审批审批提醒', '移动看板', '离线缓存'],
  },
  {
    icon: Globe,
    title: '中英文 / 粤语 / 国语',
    description: '国际化与本地化支持覆盖中文、英文以及粤语/国语语音互译场景。',
    accent: 'from-emerald-500/20 to-teal-500/10',
    bullets: ['中英文切换', '粤语/国语语音', '自动翻译'],
  },
  {
    icon: Volume2,
    title: 'Jarvis 式对话',
    description: '提供像 Jarvis 一样的语音助手，支持自然语言命令、语音翻译与语音播报。',
    accent: 'from-amber-500/20 to-orange-500/10',
    bullets: ['实时语音交互', '领域指令执行', '多语音输出'],
  },
];

const capabilities = [
  { label: 'Brand UI', value: 'Future', icon: Sparkles },
  { label: 'Interaction', value: 'Voice + Touch', icon: BellRing },
  { label: 'Operations', value: 'Desktop + Mobile', icon: TabletSmartphone },
  { label: 'AI Runtime', value: 'Multi-model', icon: Cpu },
];

const FuturePlatformPage: React.FC<FuturePlatformPageProps> = ({ section = 'platform' }) => {
  const isDesktop = section === 'desktop';
  const isMobile = section === 'mobile';
  const isConsole = section === 'console';

  if (isDesktop) {
    return (
      <div className="p-6 space-y-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Desktop</p>
            <h1 className="text-3xl font-bold mt-2">桌面应用工作台</h1>
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-200">
            <Monitor className="w-4 h-4" />
            Future Desktop
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1.4fr_0.6fr] gap-6">
          <div className="rounded-2xl border border-gray-700 bg-gray-800 p-5">
            <div className="flex items-center justify-between pb-4 border-b border-gray-700">
              <div>
                <p className="text-sm text-gray-400">AI Management Console</p>
                <h2 className="text-2xl font-semibold mt-1">Operations Center</h2>
              </div>
              <div className="rounded-full bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">Online</div>
            </div>
            <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                ['AI Agents', '12 active'],
                ['Workflow Runs', '48 today'],
                ['Risk Items', '7 alerts'],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-gray-700 bg-slate-950/40 p-4">
                  <p className="text-sm text-gray-400">{label}</p>
                  <p className="mt-2 text-xl font-bold">{value}</p>
                </div>
              ))}
            </div>
            <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                ['供应商风险', 'Low risk 86%'],
                ['供应链订单', '102 new orders'],
                ['客户增长', '+18.4% MoM'],
                ['执行效率', '92.6%'],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-gray-700 bg-slate-950/40 p-4">
                  <p className="text-sm text-gray-400">{label}</p>
                  <p className="mt-2 text-lg font-semibold">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            {[ 'Command palette', 'AI copilots', 'Enterprise widgets' ].map((item) => (
              <div key={item} className="rounded-xl border border-gray-700 bg-gray-800 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">{item}</span>
                  <Rocket className="w-4 h-4 text-cyan-300" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isMobile) {
    return (
      <div className="p-6 space-y-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-fuchsia-300">Mobile</p>
            <h1 className="text-3xl font-bold mt-2">移动端执行面</h1>
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl border border-fuchsia-500/30 bg-fuchsia-500/10 px-3 py-2 text-sm text-fuchsia-200">
            <Smartphone className="w-4 h-4" />
            Mobile Command
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            ['审批提醒', '4 items'],
            ['费用审批', '2 pending'],
            ['风险通知', '1 critical'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-gray-700 bg-gray-800 p-4">
              <p className="text-sm text-gray-400">{label}</p>
              <p className="mt-2 text-xl font-bold">{value}</p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-gray-700 bg-gradient-to-br from-fuchsia-500/20 to-violet-500/10 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300">Quick actions</p>
              <h2 className="text-xl font-semibold mt-1">移动审批与语音任务</h2>
            </div>
            <Volume2 className="w-5 h-5 text-fuchsia-200" />
          </div>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-gray-100">
            {['批准采购', '更新状态', '语音录入', '提交报告'].map((item) => (
              <div key={item} className="rounded-xl border border-white/10 bg-slate-900/30 p-3">
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isConsole) {
    return (
      <div className="p-6 space-y-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-amber-300">UI Console</p>
            <h1 className="text-3xl font-bold mt-2">未来风操作台</h1>
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            <LayoutGrid className="w-4 h-4" />
            Futuristic UI
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1.3fr_0.7fr] gap-6">
          <div className="rounded-2xl border border-gray-700 bg-gray-800 p-5">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {['Market pulse', 'Operations', 'Risk map'].map((label) => (
                <div key={label} className="rounded-xl border border-gray-700 bg-slate-950/40 p-4">
                  <p className="text-sm text-gray-400">{label}</p>
                  <div className="mt-3 h-24 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/10" />
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-700 bg-gray-800 p-5">
            <p className="text-sm text-gray-400">Command Queue</p>
            <div className="mt-4 space-y-3">
              {['AI 预测分析', '供应链审计', '语音交互协同', '自动报告'].map((item) => (
                <div key={item} className="flex items-center justify-between rounded-xl border border-gray-700 bg-slate-950/40 p-3 text-sm">
                  <span>{item}</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-300" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-violet-300">Future Platform</p>
          <h1 className="text-3xl font-bold mt-2">未来产品化扩展</h1>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 px-3 py-2 text-sm text-violet-200">
          <Briefcase className="w-4 h-4" />
          90-Day Product Roadmap
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {capabilities.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-2xl border border-gray-700 bg-gray-800 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{label}</p>
                <p className="mt-2 text-2xl font-bold">{value}</p>
              </div>
              <div className="rounded-xl bg-violet-500/10 p-2 text-violet-300">
                <Icon className="w-5 h-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        {platformCards.map(({ icon: Icon, title, description, accent, bullets }) => (
          <div key={title} className={`rounded-2xl border border-gray-700 bg-gradient-to-br ${accent} p-5`}>
            <div className="mb-4 inline-flex rounded-xl border border-white/10 bg-slate-900/40 p-2">
              <Icon className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-semibold">{title}</h2>
            <p className="mt-3 text-sm leading-6 text-gray-200">{description}</p>
            <ul className="mt-4 space-y-2 text-sm text-gray-100">
              {bullets.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 w-4 h-4 text-emerald-300" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-gray-700 bg-gray-800 p-5">
        <h2 className="text-xl font-semibold">分阶段路线图</h2>
        <div className="mt-5 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {roadmap.map((item) => (
            <div key={item.phase} className="rounded-2xl border border-gray-600 bg-slate-950/40 p-4">
              <div className="mb-3 inline-flex rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-xs font-medium text-violet-200">
                {item.phase}
              </div>
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <ul className="mt-4 space-y-2 text-sm text-gray-200">
                {item.items.map((point) => (
                  <li key={point} className="flex items-start gap-2">
                    <ArrowRight className="mt-0.5 w-4 h-4 text-violet-300" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-dashed border-cyan-500/40 bg-cyan-500/5 p-5">
        <div className="flex items-center gap-3">
          <Building2 className="w-5 h-5 text-cyan-300" />
          <h2 className="text-xl font-semibold">实施原则</h2>
        </div>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-200">
          <div className="rounded-xl border border-gray-700 bg-gray-900/40 p-4">
            <p className="font-medium text-white">先主线后扩展</p>
            <p className="mt-2 text-gray-300">核心运营路径必须稳定，扩展功能才进入产品面。</p>
          </div>
          <div className="rounded-xl border border-gray-700 bg-gray-900/40 p-4">
            <p className="font-medium text-white">统一体验栈</p>
            <p className="mt-2 text-gray-300">桌面端、移动端、操作台和语音助手共享同一信息模型。</p>
          </div>
          <div className="rounded-xl border border-gray-700 bg-gray-900/40 p-4">
            <p className="font-medium text-white">多语言优先</p>
            <p className="mt-2 text-gray-300">中英双语与粤语/国语语音互译提升企业覆盖能力。</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FuturePlatformPage;
