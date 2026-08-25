/**
 * 顶部导航栏组件 - 赛博朋克版本
 * 玻璃态材质 + 霓虹发光按钮 + 状态指示器
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Search, User, LogOut, Settings, Menu } from "lucide-react";
import { Breadcrumb } from "./Breadcrumb";
import { useAuthStore } from "../stores/authStore";
import { useUIStore } from "../stores/uiStore";

interface HeaderProps {
  onMenuClick?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const showNotification = useUIStore((state) => state.showNotification);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [showNotificationsPanel, setShowNotificationsPanel] = useState(false);

  const handleSearch = () => {
    setShowSearchModal(true);
    showNotification('info', '全局搜索功能开发中');
  };

  const handleNotifications = () => {
    setShowNotificationsPanel(!showNotificationsPanel);
    showNotification('info', '通知中心开发中');
  };

  const handleSettings = () => {
    navigate('/settings/system');
  };

  const handleLogout = () => {
    logout();
    showNotification('success', '已退出登录');
    navigate('/login');
  };

  return (
    <header className="glass-heavy border-b border-surface-border px-4 md:px-6 py-4 relative z-20">
      <div className="flex items-center justify-between">
        {/* 左侧：移动端菜单按钮 + 面包屑 */}
        <div className="flex items-center space-x-4">
          {/* 移动端菜单按钮：霓虹蓝发光 */}
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="md:hidden p-2 glass-light hover:glass-heavy hover:border-neon-blue/50 rounded-lg transition-all duration-300 border border-surface-border"
              aria-label="打开菜单"
            >
              <Menu className="w-5 h-5 text-neon-cyan" />
            </button>
          )}

          {/* 面包屑 */}
          <div className="hidden md:block">
            <Breadcrumb />
          </div>
        </div>

        {/* 右侧：操作按钮 */}
        <div className="flex items-center space-x-2 md:space-x-4">
          {/* 搜索：赛博朋克风格按钮 */}
          <button
            onClick={handleSearch}
            className="p-2 glass-light hover:glass-heavy hover:border-neon-blue/50 rounded-lg transition-all duration-300 border border-surface-border"
            aria-label="搜索"
          >
            <Search className="w-5 h-5 text-neon-cyan" />
          </button>

          {/* 通知：带霓虹红点 */}
          <button
            onClick={handleNotifications}
            className="relative p-2 glass-light hover:glass-heavy hover:border-neon-blue/50 rounded-lg transition-all duration-300 border border-surface-border"
            aria-label="通知"
          >
            <Bell className="w-5 h-5 text-neon-cyan" />
            <span className="status-indicator error absolute top-1 right-1"></span>
          </button>

          {/* 设置 */}
          <button
            onClick={handleSettings}
            className="hidden md:flex p-2 glass-light hover:glass-heavy hover:border-neon-blue/50 rounded-lg transition-all duration-300 border border-surface-border"
            aria-label="设置"
          >
            <Settings className="w-5 h-5 text-neon-cyan" />
          </button>

          {/* 用户菜单：赛博朋克头像 */}
          <div className="relative group">
            <button className="flex items-center space-x-2 p-2 glass-light hover:glass-heavy rounded-lg transition-all duration-300 border border-surface-border hover:border-neon-blue/50">
              <div className="w-8 h-8 bg-gradient-to-br from-neon-blue to-neon-purple rounded-full flex items-center justify-center border border-neon-blue/50 shadow-neon-blue">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="text-left hidden md:block">
                <p className="text-sm font-medium text-neon-blue">Admin</p>
                <p className="text-xs text-text-secondary">管理员</p>
              </div>
            </button>

            {/* 下拉菜单：玻璃态弹窗 */}
            <div className="absolute right-0 mt-2 w-48 glass-heavy rounded-lg shadow-neon-blue border border-surface-border py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
              <button
                onClick={() => navigate('/settings/profile')}
                className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-glass-md hover:text-neon-cyan transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <User className="w-4 h-4" />
                  <span>个人信息</span>
                </div>
              </button>
              <button
                onClick={handleSettings}
                className="w-full text-left px-4 py-2 text-sm text-text-primary hover:bg-glass-md hover:text-neon-cyan transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <Settings className="w-4 h-4" />
                  <span>系统设置</span>
                </div>
              </button>
              <hr className="my-2 border-surface-border/50" />
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-neon-red hover:bg-neon-red/10 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <LogOut className="w-4 h-4" />
                  <span>退出登录</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 移动端面包屑 */}
      <div className="md:hidden mt-3">
        <Breadcrumb />
      </div>
    </header>
  );
};
