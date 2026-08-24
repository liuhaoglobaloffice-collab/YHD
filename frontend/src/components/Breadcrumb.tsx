/**
 * 面包屑导航组件 - 所有项目可点击
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";
import { getBreadcrumbs } from "../config/menuConfig";

export const Breadcrumb: React.FC = () => {
  const location = useLocation();
  const breadcrumbs = getBreadcrumbs(location.pathname);

  return (
    <nav className="flex items-center space-x-2 text-sm text-gray-600">
      {/* 首页 */}
      <Link
        to="/"
        className="flex items-center hover:text-blue-600 transition-colors"
        title="返回首页"
      >
        <Home className="w-4 h-4" />
      </Link>

      {/* 面包屑项 */}
      {breadcrumbs.map((item, index) => (
        <React.Fragment key={item.path}>
          <ChevronRight className="w-4 h-4 text-gray-400" />
          {index === breadcrumbs.length - 1 ? (
            // 当前页面，不可点击
            <span className="text-gray-900 font-medium">{item.name}</span>
          ) : (
            // 父级页面，可点击
            <Link
              to={item.path}
              className="hover:text-blue-600 transition-colors"
              title="返回"
            >
              {item.name}
            </Link>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
};
