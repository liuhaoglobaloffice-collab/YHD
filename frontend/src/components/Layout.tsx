import React, { useEffect, useMemo, useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { GlobalAIStatusBar } from './GlobalAIStatusBar';
import { fetchLiveActivity, deriveAICoreState, type LiveActivity } from '../services/live';

/**
 * Layout — 应用骨架（Y1.0）。
 *
 * AI Core 状态单一数据源：这里每 20s 轮询一次 /dashboard/live-activity，
 * 派生出统一的 AI Core 状态后分发给 Header / Sidebar / GlobalAIStatusBar，
 * 避免多个组件各自轮询同一接口（全站仅此一处全局轮询）。
 */
const AI_CORE_POLL_MS = 20000;

export function Layout({ children }: { children: React.ReactNode }) {
  const [live, setLive] = useState<LiveActivity | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await fetchLiveActivity(12);
        if (!cancelled) setLive(data);
      } catch {
        // API 不可达：置 null → AI Core 显示「连接中断」（真实状态，绝不伪造在线）
        if (!cancelled) setLive(null);
      }
    };

    load();
    const timer = setInterval(load, AI_CORE_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const aiCore = useMemo(() => deriveAICoreState(live), [live]);

  return (
    <div className="app-shell">
      <Sidebar aiCore={aiCore} />
      <div className="app-main">
        <Header aiCore={aiCore} />
        <GlobalAIStatusBar live={live} />
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
