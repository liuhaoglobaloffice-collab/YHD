/**
 * 占位页面组件
 * 用于未完成的页面，显示"Coming Soon"
 */

import React from 'react';
import { Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description?: string;
}

const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[calc(100vh-200px)]">
      <Construction className="w-20 h-20 text-gray-400 mb-6" />
      <h1 className="text-4xl font-bold text-gray-800 mb-4">{title}</h1>
      <p className="text-xl text-gray-500 mb-8">
        {description || '该功能正在开发中...'}
      </p>
      <div className="flex items-center space-x-2 text-sm text-gray-400">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
        <span>敬请期待</span>
      </div>
    </div>
  );
};

export default PlaceholderPage;
