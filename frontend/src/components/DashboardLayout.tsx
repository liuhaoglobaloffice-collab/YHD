/**
 * 主布局组件 - 赛博朋克版本
 * 包含：侧边栏 + 顶部导航 + 内容区域 + 移动端侧边栏抽屉
 * 赛博朋克风格：深蓝黑背景 + 网格动画 + 扫描线效果
 */

import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export const DashboardLayout: React.FC = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  const toggleMobileSidebar = () => {
    setIsMobileSidebarOpen(!isMobileSidebarOpen);
  };

  return (
    <div className="flex h-screen bg-primary-bg overflow-hidden relative">
      {/* 赛博朋克网格背景（由全局CSS提供） */}
      
      {/* 桌面端侧边栏 */}
      <div className="hidden md:block relative z-10">
        <Sidebar 
          isCollapsed={isSidebarCollapsed} 
          onToggleCollapse={toggleSidebar} 
        />
      </div>

      {/* 移动端侧边栏遮罩：深色半透明 */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden"
          onClick={toggleMobileSidebar}
        />
      )}

      {/* 移动端侧边栏抽屉 */}
      <div
        className={`fixed inset-y-0 left-0 z-50 md:hidden transform transition-transform duration-300 `}
      >
        <Sidebar />
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden relative z-10">
        {/* 顶部导航 */}
        <Header onMenuClick={toggleMobileSidebar} />

        {/* 内容区域：添加扫描线效果 */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 scan-lines">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
