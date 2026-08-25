/**
 * Loading 加载动画组件 - 赛博朋克版本
 * 提供多种加载样式：spinner、pulse、dots
 */

import React from 'react';

export interface LoadingProps {
  type?: 'spinner' | 'pulse' | 'dots';
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  fullScreen?: boolean;
  className?: string;
}

export const Loading: React.FC<LoadingProps> = ({
  type = 'spinner',
  size = 'md',
  text,
  fullScreen = false,
  className = '',
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  const renderLoader = () => {
    switch (type) {
      case 'spinner':
        return (
          <div
            className={`
              border-2 border-neon-blue/30 border-t-neon-blue 
              rounded-full animate-spin
              ${sizeClasses[size]}
            `}
          />
        );
      case 'pulse':
        return (
          <div className="flex items-center gap-2">
            <div className={`bg-neon-blue rounded-full animate-pulse ${sizeClasses[size]}`} />
            <div className={`bg-neon-cyan rounded-full animate-pulse ${sizeClasses[size]}`} style={{ animationDelay: '0.2s' }} />
            <div className={`bg-neon-purple rounded-full animate-pulse ${sizeClasses[size]}`} style={{ animationDelay: '0.4s' }} />
          </div>
        );
      case 'dots':
        return (
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-neon-blue rounded-full animate-bounce" />
            <div className="w-2 h-2 bg-neon-cyan rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
            <div className="w-2 h-2 bg-neon-purple rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
          </div>
        );
      default:
        return null;
    }
  };

  const content = (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      {renderLoader()}
      {text && (
        <p className="text-sm text-neon-cyan animate-pulse">{text}</p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-primary-bg/90 backdrop-blur-sm flex items-center justify-center z-50">
        {content}
      </div>
    );
  }

  return content;
};

export default Loading;
