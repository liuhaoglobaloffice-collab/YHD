import React from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { GlobalAIStatusBar } from './GlobalAIStatusBar';

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <Header />
        <GlobalAIStatusBar />
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
