/**
 * 顶部导航栏组件 + 移动端菜单按钮
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

  /**
   * 搜索按钮点击处理
   */
  const handleSearch = () => {
    setShowSearchModal(true);
    // TODO: 实现全局搜索弹窗
    showNotification('info', '全局搜索功能开发中');
  };

  /**
   * 通知按钮点击处理
   */
  const handleNotifications = () => {
    setShowNotificationsPanel(!showNotificationsPanel);
    // TODO: 实现通知面板
    showNotification('info', '通知中心开发中');
  };

  /**
   * 设置按钮点击处理
   */
  const handleSettings = () => {
    navigate('/settings/system');
  };

  /**
   * 登出处理
   */
  const handleLogout = () => {
    logout();
    showNotification('success', '已退出登录');
    navigate('/login');
  };

  return (
    <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-4">
      <div className="flex items-center justify-between">
        {/* 左侧：移动端菜单按钮 + 面包屑 */}
        <div className="flex items-center space-x-4">
          {/* 移动端菜单按钮 */}
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="md:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="打开菜单"
            >
              <Menu className="w-5 h-5 text-gray-600" />
            </button>
          )}

          {/* 面包屑 */}
          <div className="hidden md:block">
            <Breadcrumb />
          </div>
        </div>

        {/* 右侧：操作按钮 */}
        <div className="flex items-center space-x-2 md:space-x-4">
          {/* 搜索 */}
          <button
            onClick={handleSearch}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="搜索"
          >
            <Search className="w-5 h-5 text-gray-600" />
          </button>

          {/* 通知 */}
          <button
            onClick={handleNotifications}
            className="relative p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="通知"
          >
            <Bell className="w-5 h-5 text-gray-600" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>

          {/* 设置 */}
          <button
            onClick={handleSettings}
            className="hidden md:flex p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="设置"
          >
            <Settings className="w-5 h-5 text-gray-600" />
          </button>

          {/* 用户菜单 */}
          <div className="relative group">
            <button className="flex items-center space-x-2 p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="text-left hidden md:block">
                <p className="text-sm font-medium text-gray-900">Admin</p>
                <p className="text-xs text-gray-500">管理员</p>
              </div>
            </button>

            {/* 下拉菜单 */}
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
              <button
                onClick={() => navigate('/settings/profile')}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                <div className="flex items-center space-x-2">
                  <User className="w-4 h-4" />
                  <span>个人信息</span>
                </div>
              </button>
              <button
                onClick={handleSettings}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                <div className="flex items-center space-x-2">
                  <Settings className="w-4 h-4" />
                  <span>系统设置</span>
                </div>
              </button>
              <hr className="my-2" />
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
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
