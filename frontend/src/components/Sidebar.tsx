/**
 * CEO Dashboard 侧边栏组件 - 赛博朋克版本
 * 支持三级菜单折叠展开 + localStorage持久化 + 自动展开当前路径
 * 赛博朋克风格：玻璃态 + 霓虹发光 + 扫描线动画
 */

import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronDown, ChevronRight, ChevronLeft } from "lucide-react";
import { menuConfig } from "../config/menuConfig";

interface SidebarProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  isCollapsed = false, 
  onToggleCollapse 
}) => {
  const location = useLocation();

  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const saved = localStorage.getItem("sidebarExpanded");
    return saved ? JSON.parse(saved) : {};
  });

  useEffect(() => {
    const newExpanded = { ...expanded };
    menuConfig.forEach((l1, l1Index) => {
      if (location.pathname.startsWith(l1.path)) newExpanded[`l1-${l1Index}`] = true;
      l1.children.forEach((l2, l2Index) => {
        if (location.pathname.startsWith(l2.path)) newExpanded[`l2-${l1Index}-${l2Index}`] = true;
      });
    });
    setExpanded(newExpanded);
  }, []);

  useEffect(() => {
    localStorage.setItem("sidebarExpanded", JSON.stringify(expanded));
  }, [expanded]);

  const toggleExpanded = (id: string) => {
    const newExpanded = { ...expanded };
    newExpanded[id] = !expanded[id];
    setExpanded(newExpanded);
  };

  const handleL1Click = (l1Path: string, l1Index: number) => {
    toggleExpanded(`l1-${l1Index}`);
  };

  return (
    <aside className={`glass-heavy text-text-primary h-screen overflow-y-auto transition-all duration-300 border-r border-surface-border scan-lines ${isCollapsed ? "w-16" : "w-64"}`}>
      {/* Logo 区域：霓虹发光效果 */}
      <div className="flex items-center justify-between px-4 py-6 border-b border-surface-border/50 backdrop-blur-md">
        <h2 className="text-xl font-bold neon-text-blue">鎏灏 AI-OS</h2>
        {onToggleCollapse && (
          <button 
            onClick={onToggleCollapse} 
            className="p-2 rounded-lg glass-light hover:glass-heavy transition-all duration-300 lg:block hidden border border-surface-border/30 hover:border-neon-blue/50" 
            title="折叠侧边栏"
          >
            <ChevronLeft size={20} className="text-neon-cyan" />
          </button>
        )}
      </div>
      
      {/* 导航菜单 */}
      <nav className="py-4">
        <ul className="space-y-1">
          {menuConfig.map((l1, l1Index) => {
            const isL1Expanded = expanded[`l1-${l1Index}`];
            const isL1Active = location.pathname.startsWith(l1.path);
            return (
              <li key={`l1-${l1Index}`}>
                {/* 一级菜单：霓虹蓝激活状态 */}
                <button 
                  onClick={() => handleL1Click(l1.path, l1Index)} 
                  className={`w-full flex items-center justify-between px-4 py-3 text-left transition-all duration-300 relative ${isL1Active ? "bg-neon-blue/10 border-l-2 border-neon-blue neon-glow-blue" : "hover:bg-glass-light"}`}
                >
                  <div className="flex items-center space-x-3">
                    <l1.icon size={20} className={isL1Active ? "text-neon-blue" : ""} />
                    <span className="flex-1 text-sm font-medium">{l1.name}</span>
                  </div>
                  <ChevronRight 
                    size={16} 
                    className={`transition-transform duration-300 ${isL1Expanded ? "rotate-90" : ""}`}>
                  </ChevronRight>
                </button>
                
                {/* 二级菜单 */}
                {isL1Expanded && (
                  <ul className="pl-4 mt-1 space-y-1">
                    {l1.children.map((l2, l2Index) => {
                      const isL2Expanded = expanded[`l2-${l1Index}-${l2Index}`];
                      const isL2Active = location.pathname.startsWith(l2.path);
                      return (
                        <li key={`l2-${l1Index}-${l2Index}`}>
                          <button 
                            onClick={() => {if (l2.children) toggleExpanded(`l2-${l1Index}-${l2Index}`);}} 
                            className={`w-full flex items-center justify-between px-4 py-2 text-left text-sm transition-colors ${isL2Active ? "text-neon-cyan" : "hover:text-neon-blue/70"}`}
                          >
                            <div className="flex items-center space-x-2">
                              {l2.icon && <l2.icon size={16} />}
                              <span>{l2.name}</span>
                            </div>
                            {l2.children && (
                              <ChevronDown 
                                size={14} 
                                className={`transition-transform ${isL2Expanded ? "rotate-180" : ""}`} 
                              />
                            )}
                          </button>
                          
                          {/* 三级菜单 */}
                          {isL2Expanded && l2.children && (
                            <ul className="pl-6 mt-1 space-y-1">
                              {l2.children.map((l3, l3Index) => (
                                <li key={`l3-${l1Index}-${l2Index}-${l3Index}`}>
                                  <Link 
                                    to={l3.path} 
                                    className={`block px-4 py-2 text-xs transition-colors ${location.pathname === l3.path ? "text-neon-purple" : "hover:text-neon-cyan/70"}`}
                                  >
                                    {l3.name}
                                  </Link>
                                </li>
                              ))}
                            </ul>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
};
