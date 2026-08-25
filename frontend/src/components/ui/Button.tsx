import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'neon';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  children,
  className = '',
  disabled,
  ...props
}) => {
  // 赛博朋克基础样式：添加霓虹发光和动画效果
  const baseClasses = 'inline-flex items-center justify-center font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed btn-glow relative overflow-hidden';
  
  // 赛博朋克主题变体：使用新的霓虹色系
  const variantClasses = {
    // 主按钮：霓虹蓝发光
    primary: 'bg-neon-blue text-primary-bg hover:bg-neon-cyan active:bg-neon-cyan shadow-neon-blue border border-neon-blue/50',
    // 次要按钮：青色发光
    secondary: 'bg-neon-cyan text-primary-bg hover:bg-neon-blue active:bg-neon-blue shadow-neon-cyan border border-neon-cyan/50',
    // 轮廓按钮：透明背景 + 霓虹边框
    outline: 'bg-transparent border-2 border-neon-blue text-neon-blue hover:bg-neon-blue/10 hover:shadow-neon-blue',
    // 幽灵按钮：玻璃态效果
    ghost: 'bg-glass-light text-text-primary hover:bg-glass-md hover:text-neon-cyan border border-surface-border/30',
    // 危险按钮：红色霓虹发光
    danger: 'bg-neon-red text-white hover:bg-neon-red/80 active:bg-neon-red shadow-neon-red border border-neon-red/50',
    // 霓虹特效按钮（极致发光）
    neon: 'bg-gradient-to-r from-neon-blue to-neon-purple text-white border-2 border-neon-cyan hover:shadow-2xl hover:shadow-neon-cyan animate-pulse-glow',
  };
  
  // 按钮尺寸
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm rounded-md',
    md: 'px-4 py-2 text-base rounded-lg',
    lg: 'px-6 py-3 text-lg rounded-xl',
  };
  
  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {/* 加载状态：霓虹旋转动画 */}
      {isLoading && (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4 text-neon-cyan"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      )}
      {children}
    </button>
  );
};

export default Button;
