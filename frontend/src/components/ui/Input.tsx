/**
 * Input 输入框组件 - 赛博朋克版本
 * 支持多种类型、前后缀图标、错误状态
 */

import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  error?: string;
  helperText?: string;
  prefixIcon?: LucideIcon;
  suffixIcon?: LucideIcon;
  variant?: 'default' | 'neon';
  fullWidth?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      prefixIcon: PrefixIcon,
      suffixIcon: SuffixIcon,
      variant = 'default',
      fullWidth = false,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const variantClasses = {
      default: 'bg-glass-light border-surface-border/30 focus:border-neon-blue',
      neon: 'bg-glass-light border-neon-blue/50 neon-glow-blue focus:border-neon-cyan',
    };

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        {label && (
          <label className="block text-sm font-medium text-neon-cyan mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          {PrefixIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <PrefixIcon className="w-5 h-5 text-text-muted" />
            </div>
          )}
          <input
            ref={ref}
            disabled={disabled}
            className={`
              px-4 py-3 rounded-lg text-text-primary placeholder-text-muted
              border transition-all duration-300 outline-none
              ${variantClasses[variant]}
              ${PrefixIcon ? 'pl-11' : ''}
              ${SuffixIcon ? 'pr-11' : ''}
              ${error ? 'border-red-500 focus:border-red-500 focus:ring-2 focus:ring-red-500/20' : 'focus:ring-2 focus:ring-neon-blue/20'}
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-neon-blue/50'}
              ${fullWidth ? 'w-full' : ''}
              ${className}
            `}
            {...props}
          />
          {SuffixIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <SuffixIcon className="w-5 h-5 text-text-muted" />
            </div>
          )}
        </div>
        {error && (
          <p className="text-sm text-red-400 mt-1">{error}</p>
        )}
        {helperText && !error && (
          <p className="text-sm text-text-muted mt-1">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
export default Input;
