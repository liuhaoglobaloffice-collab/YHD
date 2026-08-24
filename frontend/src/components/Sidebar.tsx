/**
 * CEO Dashboard 侧边栏组件
 * 支持三级菜单折叠展开 + localStorage持久化 + 自动展开当前路径
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
    <aside className={`bg-gray-900 text-white h-screen overflow-y-auto transition-all duration-300 ${isCollapsed ? "w-0 overflow-hidden" : "w-64"}`}>
      <div className="flex items-center justify-between px-4 py-6 border-b border-gray-800">
        <h2 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">鎏灏 AI-OS</h2>
        {onToggleCollapse && (<button onClick={onToggleCollapse} className="p-2 rounded-lg hover:bg-gray-800 transition-colors lg:block hidden" title="折叠侧边栏"><ChevronLeft size={20} /></button>)}
      </div>
      <nav className="py-4">
        <ul className="space-y-1">
          {menuConfig.map((l1, l1Index) => {
            const isL1Expanded = expanded[`l1-${l1Index}`];
            const isL1Active = location.pathname.startsWith(l1.path);
            return (
              <li key={`l1-${l1Index}`}>
                <button onClick={() => handleL1Click(l1.path, l1Index)} className={`w-full flex items-center justify-between px-4 py-3 text-left transition-all duration-300 ${isL1Active ? "bg-blue-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)]" : "text-gray-300 hover:bg-gray-800 hover:text-white"}`}>
                  <div className="flex items-center space-x-3"><l1.icon size={20} /><span className="flex-1 text-sm font-medium">{l1.name}</span></div>
                  <ChevronRight size={16} className={`transition-transform duration-300 ${isL1Expanded ? "rotate-90" : ""}`} />
                </button>
                {isL1Expanded && (
                  <ul className="pl-4 mt-1 space-y-1">
                    {l1.children.map((l2, l2Index) => {
                      const isL2Expanded = expanded[`l2-${l1Index}-${l2Index}`];
                      const isL2Active = location.pathname.startsWith(l2.path);
                      return (
                        <li key={`l2-${l1Index}-${l2Index}`}>
                          <button onClick={() => {if (l2.children) toggleExpanded(`l2-${l1Index}-${l2Index}`);}} className={`w-full flex items-center justify-between px-4 py-2 text-left text-sm transition-colors ${isL2Active ? "text-blue-400 bg-gray-800" : "text-gray-400 hover:text-white hover:bg-gray-800"}`}>
                            <div className="flex items-center space-x-2">{l2.icon && <l2.icon size={16} />}<span>{l2.name}</span></div>
                            {l2.children && (<ChevronDown size={14} className={`transition-transform ${isL2Expanded ? "" : "-rotate-90"}`} />)}
                          </button>
                          {isL2Expanded && l2.children && (
                            <ul className="pl-6 mt-1 space-y-1">
                              {l2.children.map((l3, l3Index) => (
                                <li key={`l3-${l1Index}-${l2Index}-${l3Index}`}>
                                  <Link to={l3.path} className={`block px-4 py-2 text-xs transition-colors ${location.pathname === l3.path ? "text-cyan-400 bg-gray-800 border-l-2 border-cyan-400" : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"}`}>{l3.name}</Link>
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
