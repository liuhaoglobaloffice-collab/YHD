/**
 * Alert 提示框组件 - 赛博朋克版本
 * 用于系统消息、警告、错误提示
 */

import React from 'react';
import { X, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

export interface AlertProps {
  children: React.ReactNode;
  type?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  closable?: boolean;
  onClose?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  children,
  type = 'info',
  title,
  closable = false,
  onClose,
  className = '',
}) => {
  const typeConfig = {
    info: {
      icon: Info,
      bgClass: 'bg-neon-cyan/10 border-neon-cyan',
      textClass: 'text-neon-cyan',
    },
    success: {
      icon: CheckCircle,
      bgClass: 'bg-neon-green/10 border-neon-green',
      textClass: 'text-neon-green',
    },
    warning: {
      icon: AlertTriangle,
      bgClass: 'bg-neon-yellow/10 border-neon-yellow',
      textClass: 'text-neon-yellow',
    },
    error: {
      icon: AlertCircle,
      bgClass: 'bg-red-500/10 border-red-500',
      textClass: 'text-red-400',
    },
  };

  const config = typeConfig[type];
  const Icon = config.icon;

  return (
    <div
      className={`
        relative rounded-lg border-l-4 p-4 backdrop-blur-sm
        ${config.bgClass}
        ${className}
      `}
    >
      <div className="flex items-start">
        <Icon className={`w-5 h-5 mr-3 mt-0.5 ${config.textClass}`} />
        <div className="flex-1">
          {title && (
            <h4 className={`text-sm font-semibold mb-1 ${config.textClass}`}>
              {title}
            </h4>
          )}
          <div className="text-sm text-text-primary">{children}</div>
        </div>
        {closable && (
          <button
            onClick={onClose}
            className={`ml-3 hover:opacity-70 transition-opacity ${config.textClass}`}
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

export default Alert;
