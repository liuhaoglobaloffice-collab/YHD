/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // === 赛博朋克主色盘 (v5.3) ===
        primary: {
          bg: '#0a1628',
          surface: '#0f1f3a',
          elevated: '#142847',
        },
        // 新增：surface 单独定义（兼容旧代码）
        surface: {
          base: '#0f1f3a',
          elevated: '#142847',
          border: 'rgba(0, 217, 255, 0.3)',
        },
        neon: {
          blue: '#00d9ff',
          cyan: '#00ffff',
          purple: '#9900ff',
          pink: '#ff00ff',
          green: '#00ff88',
          yellow: '#ffaa00',
          red: '#ff4444',
        },
        glass: {
          light: 'rgba(15, 31, 58, 0.2)',
          md: 'rgba(15, 31, 58, 0.4)',
          heavy: 'rgba(15, 31, 58, 0.6)',
          10: 'rgba(15, 31, 58, 0.1)',
          20: 'rgba(15, 31, 58, 0.2)',
          30: 'rgba(15, 31, 58, 0.3)',
          40: 'rgba(15, 31, 58, 0.4)',
          50: 'rgba(15, 31, 58, 0.5)',
          60: 'rgba(15, 31, 58, 0.6)',
          70: 'rgba(15, 31, 58, 0.7)',
          80: 'rgba(15, 31, 58, 0.8)',
        },
        text: {
          primary: '#ffffff',
          secondary: 'rgba(255, 255, 255, 0.8)',
          muted: 'rgba(255, 255, 255, 0.6)',
          disabled: 'rgba(255, 255, 255, 0.4)',
        },
        border: {
          default: 'rgba(0, 217, 255, 0.3)',
          hover: 'rgba(0, 217, 255, 0.6)',
          active: 'rgba(0, 217, 255, 1)',
        },
        cyber: {
          blue: '#00d9ff',
          cyan: '#00ffff',
          purple: '#9900ff',
          pink: '#ff00ff',
        },
      },
      
      boxShadow: {
        'neon-blue': '0 0 20px rgba(0, 217, 255, 0.5)',
        'neon-blue-lg': '0 0 40px rgba(0, 217, 255, 0.6)',
        'neon-cyan': '0 0 20px rgba(0, 255, 255, 0.5)',
        'neon-purple': '0 0 20px rgba(153, 0, 255, 0.5)',
        'neon-pink': '0 0 20px rgba(255, 0, 255, 0.5)',
        'neon-green': '0 0 20px rgba(0, 255, 136, 0.5)',
        'neon-red': '0 0 20px rgba(255, 68, 68, 0.5)',
        'glass': '0 8px 32px 0 rgba(0, 217, 255, 0.1)',
        'glass-lg': '0 16px 48px 0 rgba(0, 217, 255, 0.15)',
        'inner-glow': 'inset 0 0 20px rgba(0, 217, 255, 0.2)',
        'depth-1': '0 2px 8px rgba(0, 0, 0, 0.3)',
        'depth-2': '0 4px 16px rgba(0, 0, 0, 0.4)',
        'depth-3': '0 8px 32px rgba(0, 0, 0, 0.5)',
      },
      
      backdropBlur: {
        'xs': '2px',
        'sm': '4px',
        'md': '8px',
        'lg': '16px',
        'xl': '24px',
        '2xl': '40px',
        '3xl': '64px',
      },
      
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'pulse-glow-fast': 'pulse-glow 1s ease-in-out infinite',
        'pulse-glow-slow': 'pulse-glow 3s ease-in-out infinite',
        'breathe': 'breathe 4s ease-in-out infinite',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'slide-in-left': 'slide-in-left 0.3s ease-out',
        'slide-in-top': 'slide-in-top 0.3s ease-out',
        'slide-in-bottom': 'slide-in-bottom 0.3s ease-out',
        'fade-in': 'fade-in 0.5s ease-out',
        'fade-in-fast': 'fade-in 0.3s ease-out',
        'scale-in': 'scale-in 0.3s ease-out',
        'spin-slow': 'spin 3s linear infinite',
        'spin-slower': 'spin 6s linear infinite',
        'float': 'float 3s ease-in-out infinite',
        'blink': 'blink 1s step-start infinite',
        'scan-line': 'scan-line 2s linear infinite',
        'data-flow': 'data-flow 1.5s linear infinite',
      },
      
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1', filter: 'brightness(1)' },
          '50%': { opacity: '0.7', filter: 'brightness(1.2)' },
        },
        'breathe': {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.05)', opacity: '0.8' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-in-left': {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-in-top': {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-in-bottom': {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'data-flow': {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '50%': { opacity: '1' },
          '100%': { transform: 'translateX(100%)', opacity: '0' },
        },
      },
      
      fontFamily: {
        'sans': ['Inter', 'Microsoft YaHei', 'PingFang SC', 'sans-serif'],
        'mono': ['Fira Code', 'Consolas', 'monospace'],
        'display': ['Orbitron', 'sans-serif'],
      },
      
      borderRadius: {
        'cyber': '0.5rem',
        'cyber-lg': '0.75rem',
      },
      
      backgroundImage: {
        'gradient-cyber': 'linear-gradient(135deg, #00d9ff 0%, #9900ff 100%)',
        'gradient-cyber-2': 'linear-gradient(135deg, #00ffff 0%, #ff00ff 100%)',
        'gradient-dark': 'linear-gradient(135deg, #0a1628 0%, #1a2744 100%)',
        'grid-pattern': 'linear-gradient(to right, rgba(0, 217, 255, 0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 217, 255, 0.1) 1px, transparent 1px)',
      },
      
      spacing: {
        '18': '4.5rem',
        '112': '28rem',
        '128': '32rem',
      },
      
      maxWidth: {
        '8xl': '88rem',
        '9xl': '96rem',
      },
      
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },
    },
  },
  plugins: [
    function({ addUtilities }) {
      const newUtilities = {
        '.glass-effect': {
          backgroundColor: 'rgba(15, 31, 58, 0.4)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(0, 217, 255, 0.3)',
        },
        '.glass-effect-light': {
          backgroundColor: 'rgba(15, 31, 58, 0.2)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(0, 217, 255, 0.2)',
        },
        '.glass-effect-strong': {
          backgroundColor: 'rgba(15, 31, 58, 0.6)',
          backdropFilter: 'blur(24px)',
          border: '1px solid rgba(0, 217, 255, 0.4)',
        },
        '.text-neon-blue': {
          color: '#00d9ff',
          textShadow: '0 0 10px rgba(0, 217, 255, 0.5)',
        },
        '.text-neon-cyan': {
          color: '#00ffff',
          textShadow: '0 0 10px rgba(0, 255, 255, 0.5)',
        },
        '.text-neon-purple': {
          color: '#9900ff',
          textShadow: '0 0 10px rgba(153, 0, 255, 0.5)',
        },
        '.border-neon-glow': {
          boxShadow: '0 0 20px rgba(0, 217, 255, 0.5), inset 0 0 20px rgba(0, 217, 255, 0.1)',
        },
        '.scan-lines': {
          background: 'repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.1) 0px, rgba(0, 0, 0, 0.1) 1px, transparent 1px, transparent 2px)',
        },
        '.grid-background': {
          backgroundImage: 'linear-gradient(to right, rgba(0, 217, 255, 0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 217, 255, 0.1) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        },
      }
      
      addUtilities(newUtilities)
    },
  ],
}
