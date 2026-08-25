/**
 * Badge 徽章组件 - 赛博朋克版本
 * 用于状态指示、标签展示
 */

import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'neon';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className = '',
}) => {
  const variantClasses = {
    default: 'bg-glass-light text-text-primary border-surface-border',
    success: 'bg-neon-green/20 text-neon-green border-neon-green',
    warning: 'bg-neon-yellow/20 text-neon-yellow border-neon-yellow',
    error: 'bg-red-500/20 text-red-400 border-red-500',
    info: 'bg-neon-cyan/20 text-neon-cyan border-neon-cyan',
    neon: 'bg-neon-blue/20 text-neon-blue border-neon-blue neon-glow-blue',
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  return (
    <span
      className={`
        inline-flex items-center rounded-full font-medium border
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {children}
    </span>
  );
};

export default Badge;
