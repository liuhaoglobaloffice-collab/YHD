/**
 * Card 组件 - 赛博朋克版本
 * 提供 3 种变体：default（标准玻璃态）、glass（深度玻璃态）、neon（霓虹发光）
 * 支持标题、副标题、操作按钮
 */

import React from 'react';

export interface CardProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  variant?: 'default' | 'glass' | 'neon';
}

const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  actions,
  className = '',
  variant = 'default',
}) => {
  // 赛博朋克卡片变体：玻璃态 + 霓虹发光效果
  const variantClasses = {
    // 默认卡片：玻璃态材质 + 边框发光
    default: 'glass card-hover',
    // 深度玻璃态：更强的模糊效果
    glass: 'glass-heavy card-hover',
    // 霓虹发光卡片：强烈的边框发光
    neon: 'glass border-glow-blue card-hover scan-lines',
  };
  
  return (
    <div className={`rounded-lg overflow-hidden ${variantClasses[variant]} ${className}`}>
      {(title || subtitle || actions) && (
        <div className="px-6 py-4 border-b border-surface-border/50 flex items-center justify-between backdrop-blur-sm">
          <div>
            {title && (
              <h3 className="text-lg font-semibold text-neon-blue neon-text-blue">{title}</h3>
            )}
            {subtitle && (
              <p className="text-sm text-text-secondary mt-1">{subtitle}</p>
            )}
          </div>
          {actions && (
            <div className="flex items-center gap-2">{actions}</div>
          )}
        </div>
      )}
      <div className="px-6 py-4 relative z-10">{children}</div>
    </div>
  );
};

export { Card };
export default Card;
