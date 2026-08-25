/**
 * Tabs 标签页组件 - 赛博朋克版本
 */

import React, { useState } from 'react';

export interface TabItem {
  id: string;
  label: string;
  content: React.ReactNode;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
  variant?: 'default' | 'neon';
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  items,
  defaultTab,
  onChange,
  variant = 'default',
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState(defaultTab || items[0]?.id);

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    onChange?.(tabId);
  };

  const activeItem = items.find((item) => item.id === activeTab);

  const variantClasses = {
    default: {
      tab: 'border-b-2 border-neon-blue text-neon-blue',
      inactive: 'border-b-2 border-transparent text-text-muted hover:text-text-primary',
    },
    neon: {
      tab: 'border-b-2 border-neon-blue text-neon-blue neon-glow-blue',
      inactive: 'border-b-2 border-transparent text-text-muted hover:text-neon-cyan',
    },
  };

  return (
    <div className={className}>
      {/* Tab Headers */}
      <div className="flex border-b border-surface-border/30">
        {items.map((item) => {
          const isActive = item.id === activeTab;
          return (
            <button
              key={item.id}
              onClick={() => !item.disabled && handleTabChange(item.id)}
              disabled={item.disabled}
              className={`
                px-4 py-3 font-medium transition-all duration-300
                flex items-center gap-2
                ${isActive ? variantClasses[variant].tab : variantClasses[variant].inactive}
                ${item.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              {item.icon}
              {item.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="py-4">
        {activeItem?.content}
      </div>
    </div>
  );
};

export default Tabs;
