# 🎨 鎏灏 AI-OS v5.3 UI设计系统完整规范

**版本**: v5.3 Final  
**风格**: 赛博朋克 + 未来科技风  
**创建日期**: 2026-08-24  
**参考UI**: C:/Users/Administrator/Desktop/贸易/ui.png

---

## 📐 设计理念

### **核心设计原则**

```yaml
视觉风格: 赛博朋克 + 科幻未来
情感基调: 专业、高效、科技感、信任
用户体验: 流畅、直观、沉浸式
交互反馈: 实时、清晰、愉悦

设计目标:
  1. 视觉冲击力 - 让CEO一眼就被吸引
  2. 信息密度 - 在一个屏幕展示最多有用信息
  3. 操作效率 - 最少点击完成任务
  4. 沉浸感 - 让用户感觉在操控未来
```

### **设计灵感来源**

```
参考案例:
- 电影《创：战纪》(Tron: Legacy) - 霓虹线条
- 电影《银翼杀手2049》(Blade Runner 2049) - 赛博朋克美学
- 游戏《赛博朋克2077》(Cyberpunk 2077) - 全息界面
- 特斯拉Model S屏幕 - 极简科技
- 钢铁侠贾维斯界面 - 3D全息投影

关键特征:
✅ 深色背景（深蓝黑）
✅ 霓虹色彩（青色/蓝色/紫色）
✅ 发光效果（glow/bloom）
✅ 玻璃态材质（glassmorphism）
✅ 扫描线动画
✅ 粒子系统
✅ 3D元素
✅ 流畅动画
```

---

## 🎨 视觉设计

### **1. 配色系统**

#### **主色调**

```typescript
// 深蓝黑系列（背景）
const backgroundColors = {
  primary: '#0a1628',      // 主背景
  secondary: '#0d1b2a',    // 次级背景
  tertiary: '#1a2332',     // 卡片背景
};

// 霓虹蓝系列（强调色）
const accentColors = {
  cyan: {
    50:  '#e0f7ff',
    100: '#b3ecff',
    200: '#80e1ff',
    300: '#4dd5ff',
    400: '#26cbff',
    500: '#00d9ff',   // 主霓虹蓝 ⭐
    600: '#00b8e6',
    700: '#0097cc',
    800: '#0076b3',
    900: '#005599',
  },
  
  blue: {
    500: '#0099ff',   // 亮蓝
    600: '#0066ff',   // 标准蓝
    700: '#0033ff',   // 深蓝
  },
  
  purple: {
    500: '#9900ff',   // 紫色（点缀）
    600: '#8800ee',
    700: '#7700dd',
  }
};

// 功能色（状态）
const functionalColors = {
  success: {
    main: '#00ff88',      // 绿色（成功/增长）
    light: '#33ffaa',
    dark: '#00cc66',
  },
  
  warning: {
    main: '#ffbb00',      // 黄色（警告/中度风险）
    light: '#ffcc33',
    dark: '#ee9900',
  },
  
  danger: {
    main: '#ff4444',      // 红色（危险/高风险）
    light: '#ff6666',
    dark: '#ee2222',
  },
  
  info: {
    main: '#0099ff',      // 蓝色（信息）
    light: '#33aaff',
    dark: '#0077cc',
  }
};

// 中性色（文字/边框）
const neutralColors = {
  gray: {
    50:  '#f8f9fa',
    100: '#e9ecef',
    200: '#dee2e6',
    300: '#ced4da',
    400: '#adb5bd',
    500: '#6c757d',
    600: '#495057',
    700: '#343a40',
    800: '#212529',
    900: '#0d1117',
  },
  
  white: {
    100: 'rgba(255, 255, 255, 1.0)',
    90:  'rgba(255, 255, 255, 0.9)',
    80:  'rgba(255, 255, 255, 0.8)',
    70:  'rgba(255, 255, 255, 0.7)',
    50:  'rgba(255, 255, 255, 0.5)',
    30:  'rgba(255, 255, 255, 0.3)',
    20:  'rgba(255, 255, 255, 0.2)',
    10:  'rgba(255, 255, 255, 0.1)',
    5:   'rgba(255, 255, 255, 0.05)',
  }
};
```

#### **配色规则**

```yaml
背景层级:
  - Level 1 (页面背景): #0a1628
  - Level 2 (卡片背景): rgba(255,255,255,0.05) + blur
  - Level 3 (嵌套卡片): rgba(255,255,255,0.08) + blur

文字颜色:
  - 标题/重点: #ffffff (100%)
  - 正文: #e9ecef (90%)
  - 次要文字: #adb5bd (70%)
  - 禁用/占位符: #6c757d (50%)

强调色使用:
  - 主按钮/链接: #00d9ff (霓虹蓝)
  - 图标/徽章: #00ffff (青色)
  - 点缀/渐变: #9900ff (紫色)

功能色使用:
  - 成功/增长: #00ff88 (绿色)
  - 警告/中度: #ffbb00 (黄色)
  - 危险/高风险: #ff4444 (红色)
  - 信息提示: #0099ff (蓝色)
```

---

### **2. 字体系统**

#### **字体家族**

```typescript
const typography = {
  fontFamily: {
    // 主字体（正文/UI）
    primary: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      'Segoe UI',
      'Roboto',
      'Helvetica Neue',
      'Arial',
      'Noto Sans SC',  // 中文
      'sans-serif',
    ].join(','),
    
    // 等宽字体（代码/数据）
    mono: [
      'Fira Code',
      'JetBrains Mono',
      'Monaco',
      'Consolas',
      'Courier New',
      'monospace',
    ].join(','),
    
    // 展示字体（标题/Logo）
    display: [
      'Orbitron',      // 科技感
      'Rajdhani',
      'Exo 2',
      'Inter',
      'sans-serif',
    ].join(','),
  },
  
  // 字重
  fontWeight: {
    light: 300,
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },
  
  // 字号
  fontSize: {
    xs:   ['0.75rem',  { lineHeight: '1rem' }],    // 12px
    sm:   ['0.875rem', { lineHeight: '1.25rem' }], // 14px
    base: ['1rem',     { lineHeight: '1.5rem' }],  // 16px
    lg:   ['1.125rem', { lineHeight: '1.75rem' }], // 18px
    xl:   ['1.25rem',  { lineHeight: '1.75rem' }], // 20px
    '2xl': ['1.5rem',   { lineHeight: '2rem' }],    // 24px
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
    '4xl': ['2.25rem',  { lineHeight: '2.5rem' }],  // 36px
    '5xl': ['3rem',     { lineHeight: '1' }],       // 48px
    '6xl': ['3.75rem',  { lineHeight: '1' }],       // 60px
    '7xl': ['4.5rem',   { lineHeight: '1' }],       // 72px
  },
  
  // 字间距
  letterSpacing: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },
};
```

#### **文本样式**

```typescript
// 标题样式
const headingStyles = {
  h1: {
    fontFamily: 'display',
    fontSize: '3rem',         // 48px
    fontWeight: 700,
    letterSpacing: '0.05em',
    color: '#00d9ff',
    textShadow: '0 0 20px rgba(0, 217, 255, 0.6)',
  },
  
  h2: {
    fontFamily: 'display',
    fontSize: '2.25rem',      // 36px
    fontWeight: 600,
    letterSpacing: '0.025em',
    color: '#00d9ff',
  },
  
  h3: {
    fontFamily: 'primary',
    fontSize: '1.875rem',     // 30px
    fontWeight: 600,
    color: '#ffffff',
  },
  
  h4: {
    fontFamily: 'primary',
    fontSize: '1.5rem',       // 24px
    fontWeight: 600,
    color: '#ffffff',
  },
  
  h5: {
    fontFamily: 'primary',
    fontSize: '1.25rem',      // 20px
    fontWeight: 600,
    color: '#e9ecef',
  },
  
  h6: {
    fontFamily: 'primary',
    fontSize: '1rem',         // 16px
    fontWeight: 600,
    color: '#e9ecef',
  },
};

// 正文样式
const bodyStyles = {
  body1: {
    fontFamily: 'primary',
    fontSize: '1rem',         // 16px
    fontWeight: 400,
    lineHeight: '1.5',
    color: '#e9ecef',
  },
  
  body2: {
    fontFamily: 'primary',
    fontSize: '0.875rem',     // 14px
    fontWeight: 400,
    lineHeight: '1.43',
    color: '#adb5bd',
  },
  
  caption: {
    fontFamily: 'primary',
    fontSize: '0.75rem',      // 12px
    fontWeight: 400,
    lineHeight: '1.33',
    color: '#6c757d',
  },
  
  code: {
    fontFamily: 'mono',
    fontSize: '0.875rem',     // 14px
    fontWeight: 400,
    color: '#00d9ff',
    background: 'rgba(0, 217, 255, 0.1)',
    padding: '0.125rem 0.25rem',
    borderRadius: '0.25rem',
  },
};
```

---

### **3. 间距系统**

```typescript
const spacing = {
  0:   '0',
  1:   '0.25rem',   // 4px
  2:   '0.5rem',    // 8px
  3:   '0.75rem',   // 12px
  4:   '1rem',      // 16px
  5:   '1.25rem',   // 20px
  6:   '1.5rem',    // 24px
  7:   '1.75rem',   // 28px
  8:   '2rem',      // 32px
  9:   '2.25rem',   // 36px
  10:  '2.5rem',    // 40px
  11:  '2.75rem',   // 44px
  12:  '3rem',      // 48px
  14:  '3.5rem',    // 56px
  16:  '4rem',      // 64px
  20:  '5rem',      // 80px
  24:  '6rem',      // 96px
  28:  '7rem',      // 112px
  32:  '8rem',      // 128px
  36:  '9rem',      // 144px
  40:  '10rem',     // 160px
  44:  '11rem',     // 176px
  48:  '12rem',     // 192px
  52:  '13rem',     // 208px
  56:  '14rem',     // 224px
  60:  '15rem',     // 240px
  64:  '16rem',     // 256px
  72:  '18rem',     // 288px
  80:  '20rem',     // 320px
  96:  '24rem',     // 384px
};

// 组件间距规则
const componentSpacing = {
  // 页面边距
  page: {
    padding: '1.5rem',        // 24px
    maxWidth: '1600px',
  },
  
  // 卡片间距
  card: {
    padding: '1.5rem',        // 24px
    gap: '1rem',              // 16px
  },
  
  // 表单间距
  form: {
    fieldGap: '1rem',         // 16px
    labelMargin: '0.5rem',    // 8px
  },
  
  // 列表间距
  list: {
    itemGap: '0.5rem',        // 8px
    iconMargin: '0.75rem',    // 12px
  },
};
```

---

### **4. 圆角系统**

```typescript
const borderRadius = {
  none: '0',
  sm:   '0.25rem',   // 4px
  base: '0.5rem',    // 8px
  md:   '0.75rem',   // 12px
  lg:   '1rem',      // 16px
  xl:   '1.5rem',    // 24px
  '2xl': '2rem',     // 32px
  '3xl': '3rem',     // 48px
  full: '9999px',    // 圆形
};

// 组件圆角规则
const componentBorderRadius = {
  button: 'lg',       // 16px
  card: 'xl',         // 24px
  input: 'lg',        // 16px
  badge: 'full',      // 圆形
  avatar: 'full',     // 圆形
  modal: '2xl',       // 32px
};
```

---

### **5. 阴影系统**

```typescript
const shadows = {
  // 常规阴影
  sm:   '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md:   '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg:   '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl:   '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  
  // 发光效果（赛博朋克特色）⭐
  glow: {
    cyan: {
      sm:   '0 0 10px rgba(0, 217, 255, 0.4)',
      base: '0 0 20px rgba(0, 217, 255, 0.6)',
      lg:   '0 0 30px rgba(0, 217, 255, 0.8)',
    },
    blue: {
      sm:   '0 0 10px rgba(0, 153, 255, 0.4)',
      base: '0 0 20px rgba(0, 153, 255, 0.6)',
      lg:   '0 0 30px rgba(0, 153, 255, 0.8)',
    },
    purple: {
      sm:   '0 0 10px rgba(153, 0, 255, 0.4)',
      base: '0 0 20px rgba(153, 0, 255, 0.6)',
      lg:   '0 0 30px rgba(153, 0, 255, 0.8)',
    },
    green: {
      sm:   '0 0 10px rgba(0, 255, 136, 0.4)',
      base: '0 0 20px rgba(0, 255, 136, 0.6)',
      lg:   '0 0 30px rgba(0, 255, 136, 0.8)',
    },
    red: {
      sm:   '0 0 10px rgba(255, 68, 68, 0.4)',
      base: '0 0 20px rgba(255, 68, 68, 0.6)',
      lg:   '0 0 30px rgba(255, 68, 68, 0.8)',
    },
  },
  
  // 内阴影
  inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
};
```

---

## 🧩 组件设计

### **1. 玻璃态卡片（Glass Card）** ⭐

> **核心组件，整个系统的基础**

```typescript
// GlassCard.tsx

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: boolean;
  glowColor?: 'cyan' | 'blue' | 'purple' | 'green' | 'red';
  animated?: boolean;
  padding?: 'sm' | 'md' | 'lg' | 'xl';
  blur?: 'sm' | 'md' | 'lg' | 'xl';
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  glow = false,
  glowColor = 'cyan',
  animated = true,
  padding = 'lg',
  blur = 'xl',
}) => {
  const paddingClasses = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
    xl: 'p-8',
  };
  
  const blurClasses = {
    sm: 'backdrop-blur-sm',
    md: 'backdrop-blur-md',
    lg: 'backdrop-blur-lg',
    xl: 'backdrop-blur-xl',
  };
  
  const glowClasses = {
    cyan: 'shadow-glow-cyan',
    blue: 'shadow-glow-blue',
    purple: 'shadow-glow-purple',
    green: 'shadow-glow-green',
    red: 'shadow-glow-red',
  };
  
  return (
    <motion.div
      className={`
        relative
        bg-white/5
        ${blurClasses[blur]}
        border border-cyan-500/30
        rounded-xl
        ${paddingClasses[padding]}
        transition-all duration-300
        hover:bg-white/8
        hover:border-cyan-500/60
        ${glow ? glowClasses[glowColor] : ''}
        ${className}
      `}
      initial={animated ? { opacity: 0, y: 20 } : {}}
      animate={animated ? { opacity: 1, y: 0 } : {}}
      whileHover={animated ? { scale: 1.01 } : {}}
    >
      {/* 扫描线效果 */}
      <div className="absolute inset-0 scan-lines opacity-10 pointer-events-none rounded-xl overflow-hidden" />
      
      {/* 发光边框（可选） */}
      {glow && (
        <div className={`
          absolute -inset-0.5 
          bg-gradient-to-r from-${glowColor}-500 to-blue-500 
          rounded-xl opacity-20 blur-sm
          pointer-events-none
        `} />
      )}
      
      {/* 内容 */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
};
```

**CSS样式**:
```css
/* glassmorphism.css */

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 217, 255, 0.3);
  border-radius: 1.5rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.glass-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(0, 217, 255, 0.6);
  box-shadow: 
    0 8px 32px rgba(0, 217, 255, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

/* 扫描线动画 */
.scan-lines {
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 217, 255, 0.03) 2px,
    rgba(0, 217, 255, 0.03) 4px
  );
  animation: scan-lines-move 8s linear infinite;
}

@keyframes scan-lines-move {
  0% { transform: translateY(0); }
  100% { transform: translateY(100%); }
}

/* 发光阴影 */
.shadow-glow-cyan {
  box-shadow: 0 0 20px rgba(0, 217, 255, 0.6);
}

.shadow-glow-blue {
  box-shadow: 0 0 20px rgba(0, 153, 255, 0.6);
}

.shadow-glow-purple {
  box-shadow: 0 0 20px rgba(153, 0, 255, 0.6);
}

.shadow-glow-green {
  box-shadow: 0 0 20px rgba(0, 255, 136, 0.6);
}

.shadow-glow-red {
  box-shadow: 0 0 20px rgba(255, 68, 68, 0.6);
}
```

---

### **2. 发光按钮（Glow Button）** ⭐

```typescript
// GlowButton.tsx

interface GlowButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  fullWidth?: boolean;
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
}

export const GlowButton: React.FC<GlowButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  loading = false,
  onClick,
}) => {
  const variantClasses = {
    primary: 'bg-cyan-500/20 text-cyan-400 border-2 border-cyan-500 hover:bg-cyan-500/30 shadow-glow-cyan',
    secondary: 'bg-blue-500/20 text-blue-400 border-2 border-blue-500 hover:bg-blue-500/30 shadow-glow-blue',
    success: 'bg-green-500/20 text-green-400 border-2 border-green-500 hover:bg-green-500/30 shadow-glow-green',
    warning: 'bg-yellow-500/20 text-yellow-400 border-2 border-yellow-500 hover:bg-yellow-500/30',
    danger: 'bg-red-500/20 text-red-400 border-2 border-red-500 hover:bg-red-500/30 shadow-glow-red',
  };
  
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
    xl: 'px-10 py-5 text-xl',
  };
  
  return (
    <motion.button
      className={`
        relative
        rounded-lg
        font-semibold
        transition-all duration-300
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${fullWidth ? 'w-full' : ''}
      `}
      whileHover={!disabled ? { scale: 1.05 } : {}}
      whileTap={!disabled ? { scale: 0.95 } : {}}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {/* 发光效果 */}
      <div className={`
        absolute inset-0 
        ${variantClasses[variant].split(' ')[0]} 
        rounded-lg blur-lg opacity-0 
        hover:opacity-100 transition-opacity
      `} />
      
      {/* 内容 */}
      <span className="relative z-10 flex items-center justify-center gap-2">
        {loading && (
          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>
        )}
        {children}
      </span>
    </motion.button>
  );
};
```

---

### **3. 数字滚动动画（Count Up）** ⭐

```typescript
// CountUpNumber.tsx

interface CountUpNumberProps {
  value: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}

export const CountUpNumber: React.FC<CountUpNumberProps> = ({
  value,
  duration = 1000,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
}) => {
  const [displayValue, setDisplayValue] = useState(0);
  
  useEffect(() => {
    let start = 0;
    const increment = value / (duration / 16);
    
    const timer = setInterval(() => {
      start += increment;
      if (start >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(start);
      }
    }, 16);
    
    return () => clearInterval(timer);
  }, [value, duration]);
  
  const formatted = decimals > 0
    ? displayValue.toFixed(decimals)
    : Math.floor(displayValue).toLocaleString();
  
  return (
    <span className={`font-mono text-cyan-400 tabular-nums ${className}`}>
      {prefix}{formatted}{suffix}
    </span>
  );
};
```

---

### **4. 进度条（Progress Bar）**

```typescript
// ProgressBar.tsx

interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  color?: 'cyan' | 'blue' | 'green' | 'yellow' | 'red';
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  striped?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  label,
  showValue = true,
  color = 'cyan',
  size = 'md',
  animated = true,
  striped = false,
}) => {
  const percentage = Math.min((value / max) * 100, 100);
  
  const colorClasses = {
    cyan: 'bg-cyan-500',
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  };
  
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-6',
  };
  
  return (
    <div className="w-full">
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-2">
          {label && <span className="text-sm text-gray-400">{label}</span>}
          {showValue && (
            <span className="text-sm text-cyan-400 font-mono">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      
      <div className={`
        w-full 
        ${sizeClasses[size]} 
        bg-white/5 
        rounded-full 
        overflow-hidden 
        border border-white/10
      `}>
        <motion.div
          className={`
            h-full 
            ${colorClasses[color]} 
            rounded-full
            ${striped ? 'bg-stripes' : ''}
            shadow-glow-${color}
          `}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: animated ? 1 : 0, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
};
```

**CSS样式**:
```css
/* 条纹动画 */
.bg-stripes {
  background-image: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.2) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.2) 50%,
    rgba(255, 255, 255, 0.2) 75%,
    transparent 75%,
    transparent
  );
  background-size: 1rem 1rem;
  animation: move-stripes 1s linear infinite;
}

@keyframes move-stripes {
  0% { background-position: 0 0; }
  100% { background-position: 1rem 0; }
}
```

---

### **5. 徽章（Badge）**

```typescript
// Badge.tsx

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  pulse?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'info',
  size = 'md',
  dot = false,
  pulse = false,
}) => {
  const variantClasses = {
    success: 'bg-green-500/20 text-green-400 border-green-500/30',
    warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    danger: 'bg-red-500/20 text-red-400 border-red-500/30',
    info: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    neutral: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };
  
  if (dot) {
    return (
      <span className={`
        inline-block
        w-2 h-2
        rounded-full
        ${variantClasses[variant].split(' ')[0].replace('bg-', 'bg-').replace('/20', '')}
        ${pulse ? 'animate-pulse' : ''}
      `} />
    );
  }
  
  return (
    <span className={`
      inline-flex items-center
      rounded-full
      border
      font-semibold
      ${variantClasses[variant]}
      ${sizeClasses[size]}
      ${pulse ? 'animate-pulse' : ''}
    `}>
      {children}
    </span>
  );
};
```

---

### **6. 输入框（Input）**

```typescript
// Input.tsx

interface InputProps {
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  label?: string;
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  icon?: React.ReactNode;
  suffix?: React.ReactNode;
  disabled?: boolean;
  fullWidth?: boolean;
}

export const Input: React.FC<InputProps> = ({
  type = 'text',
  label,
  placeholder,
  value,
  onChange,
  error,
  icon,
  suffix,
  disabled = false,
  fullWidth = false,
}) => {
  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label className="block text-sm font-medium text-gray-400 mb-2">
          {label}
        </label>
      )}
      
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
            {icon}
          </div>
        )}
        
        <input
          type={type}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={`
            w-full
            px-4 py-3
            ${icon ? 'pl-10' : ''}
            ${suffix ? 'pr-10' : ''}
            bg-white/5
            backdrop-blur-xl
            border border-cyan-500/30
            rounded-lg
            text-gray-200
            placeholder-gray-500
            focus:border-cyan-500
            focus:outline-none
            focus:ring-2
            focus:ring-cyan-500/20
            disabled:opacity-50
            disabled:cursor-not-allowed
            transition-all
          `}
        />
        
        {suffix && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
            {suffix}
          </div>
        )}
      </div>
      
      {error && (
        <p className="mt-2 text-sm text-red-400">
          {error}
        </p>
      )}
    </div>
  );
};
```

---

### **7. 选择器（Select）**

```typescript
// Select.tsx

interface SelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

interface SelectProps {
  options: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  fullWidth?: boolean;
}

export const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
  placeholder = '请选择',
  label,
  error,
  fullWidth = false,
}) => {
  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label className="block text-sm font-medium text-gray-400 mb-2">
          {label}
        </label>
      )}
      
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className={`
          w-full
          px-4 py-3
          bg-white/5
          backdrop-blur-xl
          border border-cyan-500/30
          rounded-lg
          text-gray-200
          focus:border-cyan-500
          focus:outline-none
          focus:ring-2
          focus:ring-cyan-500/20
          transition-all
          appearance-none
          cursor-pointer
        `}
      >
        <option value="" disabled>{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      
      {/* 下拉箭头 */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/>
        </svg>
      </div>
      
      {error && (
        <p className="mt-2 text-sm text-red-400">
          {error}
        </p>
      )}
    </div>
  );
};
```

---

## ✨ 动画设计

### **1. 动画时长**

```typescript
const animations = {
  duration: {
    instant: 0,
    fast: 150,
    normal: 300,
    slow: 500,
    slower: 700,
    slowest: 1000,
  },
  
  easing: {
    linear: 'linear',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
};
```

### **2. 常用动画**

**淡入淡出**:
```typescript
const fadeVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

<motion.div
  initial="hidden"
  animate="visible"
  exit="hidden"
  variants={fadeVariants}
  transition={{ duration: 0.3 }}
>
  {children}
</motion.div>
```

**滑入滑出**:
```typescript
const slideVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
};

<motion.div
  initial="hidden"
  animate="visible"
  variants={slideVariants}
  transition={{ duration: 0.3, ease: 'easeOut' }}
>
  {children}
</motion.div>
```

**缩放**:
```typescript
const scaleVariants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: { opacity: 1, scale: 1 },
};

<motion.div
  initial="hidden"
  animate="visible"
  variants={scaleVariants}
  transition={{ duration: 0.3, ease: 'spring' }}
>
  {children}
</motion.div>
```

**旋转**:
```typescript
<motion.div
  animate={{ rotate: 360 }}
  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
>
  {children}
</motion.div>
```

**脉冲**:
```typescript
<motion.div
  animate={{
    scale: [1, 1.05, 1],
    opacity: [1, 0.8, 1],
  }}
  transition={{
    duration: 2,
    repeat: Infinity,
    ease: 'easeInOut',
  }}
>
  {children}
</motion.div>
```

---

## 🎬 特效设计

### **1. 粒子背景系统** ⭐

```typescript
// ParticleBackground.tsx

import Particles from 'react-tsparticles';
import { loadFull } from 'tsparticles';

export const ParticleBackground = () => {
  const particlesInit = useCallback(async (engine) => {
    await loadFull(engine);
  }, []);
  
  return (
    <Particles
      id="particle-background"
      init={particlesInit}
      options={{
        fullScreen: {
          enable: true,
          zIndex: -1,
        },
        background: {
          color: "transparent"
        },
        fpsLimit: 60,
        particles: {
          number: {
            value: 100,
            density: {
              enable: true,
              area: 800
            }
          },
          color: {
            value: ["#00d9ff", "#00ffff", "#0099ff", "#9900ff"]
          },
          shape: {
            type: "circle"
          },
          opacity: {
            value: 0.5,
            random: true,
            animation: {
              enable: true,
              speed: 1,
              minimumValue: 0.1
            }
          },
          size: {
            value: 3,
            random: true,
            animation: {
              enable: true,
              speed: 2,
              minimumValue: 0.5
            }
          },
          move: {
            enable: true,
            speed: 0.5,
            direction: "none",
            outModes: {
              default: "out"
            }
          },
          links: {
            enable: true,
            distance: 150,
            color: "#00d9ff",
            opacity: 0.2,
            width: 1
          }
        },
        interactivity: {
          events: {
            onHover: {
              enable: true,
              mode: "grab"
            },
            onClick: {
              enable: true,
              mode: "push"
            }
          },
          modes: {
            grab: {
              distance: 200,
              links: {
                opacity: 0.5
              }
            },
            push: {
              quantity: 4
            }
          }
        }
      }}
    />
  );
};
```

---

### **2. 扫描线效果**

```css
/* scan-lines.css */

.scan-lines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 217, 255, 0.03) 2px,
    rgba(0, 217, 255, 0.03) 4px
  );
  pointer-events: none;
  animation: scan-lines-move 8s linear infinite;
}

@keyframes scan-lines-move {
  0% {
    transform: translateY(0);
  }
  100% {
    transform: translateY(100%);
  }
}
```

---

### **3. 全息闪烁效果**

```css
/* hologram.css */

.hologram {
  position: relative;
  background: radial-gradient(
    ellipse at center,
    rgba(0, 217, 255, 0.2) 0%,
    transparent 70%
  );
  animation: hologram-flicker 3s ease-in-out infinite;
}

@keyframes hologram-flicker {
  0%, 100% {
    opacity: 1;
  }
  45%, 55% {
    opacity: 0.95;
  }
  50% {
    opacity: 0.9;
  }
}
```

---

### **4. 发光脉冲**

```css
/* glow-pulse.css */

.glow-pulse {
  animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% {
    box-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(0, 217, 255, 0.8);
  }
}
```

---

## 📱 响应式设计

### **断点系统**

```typescript
const breakpoints = {
  xs: '375px',    // 小手机
  sm: '640px',    // 手机
  md: '768px',    // 平板竖屏
  lg: '1024px',   // 平板横屏/小笔记本
  xl: '1280px',   // 笔记本
  '2xl': '1536px',  // 桌面显示器
  '3xl': '1920px',  // 大显示器
};
```

### **响应式规则**

```yaml
布局:
  - Mobile (< 768px): 单列布局
  - Tablet (768px - 1024px): 双列布局
  - Desktop (> 1024px): 三列/四列布局

字体:
  - Mobile: 基础字号 14px
  - Tablet: 基础字号 15px
  - Desktop: 基础字号 16px

间距:
  - Mobile: 更紧凑（padding: 1rem）
  - Tablet: 标准（padding: 1.5rem）
  - Desktop: 更宽松（padding: 2rem）

导航:
  - Mobile: 底部导航栏
  - Tablet/Desktop: 左侧边栏
```

---

## 🎨 设计资源

### **图标库**

```typescript
// 推荐图标库
import {
  HomeIcon,
  ChartBarIcon,
  UsersIcon,
  CogIcon,
  BellIcon,
  // ... 更多
} from '@heroicons/react/24/outline';

// 或使用 Lucide Icons
import {
  Home,
  BarChart,
  Users,
  Settings,
  Bell,
} from 'lucide-react';
```

### **插图资源**

```yaml
3D模型:
  - 贾维斯头像: public/models/jarvis-head.glb
  - 3D图标: Ready Player Me / Mixamo

插图:
  - 空状态: Undraw.co
  - 加载动画: Lottie Files
  - 背景: Unsplash / Pexels

字体:
  - Inter: https://fonts.google.com/specimen/Inter
  - Fira Code: https://fonts.google.com/specimen/Fira+Code
  - Orbitron: https://fonts.google.com/specimen/Orbitron
```

---

## ✅ 实施清单

### **Phase 1: 设计Token实施**
- [ ] 定义颜色系统
- [ ] 配置字体系统
- [ ] 设置间距系统
- [ ] 定义圆角/阴影

### **Phase 2: 核心组件开发**
- [ ] GlassCard
- [ ] GlowButton
- [ ] Input/Select
- [ ] Badge/Tag
- [ ] ProgressBar
- [ ] CountUpNumber

### **Phase 3: 特效实现**
- [ ] 粒子背景系统
- [ ] 扫描线效果
- [ ] 全息闪烁
- [ ] 发光脉冲

### **Phase 4: 动画集成**
- [ ] Framer Motion配置
- [ ] GSAP动画
- [ ] 页面切换动画
- [ ] 微交互动画

### **Phase 5: 响应式优化**
- [ ] 移动端适配
- [ ] 平板适配
- [ ] 桌面优化
- [ ] 触摸手势

---

## 📚 参考资源

```yaml
设计规范:
  - Material Design 3: https://m3.material.io/
  - Apple Human Interface Guidelines
  - Ant Design
  - shadcn/ui

技术文档:
  - TailwindCSS: https://tailwindcss.com/
  - Framer Motion: https://www.framer.com/motion/
  - Three.js: https://threejs.org/
  - React Spring: https://react-spring.dev/

设计工具:
  - Figma
  - Adobe XD
  - Spline (3D设计)
  - Lottie (动画)
```

---

**文档完成！现在你拥有完整的UI设计系统规范！** 🎨✨
