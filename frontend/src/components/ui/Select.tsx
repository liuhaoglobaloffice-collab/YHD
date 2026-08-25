/**
 * Select 下拉选择组件 - 赛博朋克版本
 */

import React from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label?: string;
  error?: string;
  options: SelectOption[];
  placeholder?: string;
  fullWidth?: boolean;
  variant?: 'default' | 'neon';
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      label,
      error,
      options,
      placeholder,
      fullWidth = false,
      variant = 'default',
      className = '',
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
          <select
            ref={ref}
            className={`
              px-4 py-3 pr-10 rounded-lg text-text-primary
              border transition-all duration-300 outline-none
              appearance-none cursor-pointer
              ${variantClasses[variant]}
              ${error ? 'border-red-500 focus:border-red-500' : 'focus:ring-2 focus:ring-neon-blue/20'}
              ${fullWidth ? 'w-full' : ''}
              ${className}
            `}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((option) => (
              <option
                key={option.value}
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted pointer-events-none" />
        </div>
        {error && (
          <p className="text-sm text-red-400 mt-1">{error}</p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';
export default Select;
