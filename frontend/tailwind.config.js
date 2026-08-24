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
        // 赛博朋克主色调
        cyber: {
          blue: '#0ea5e9', // 科技蓝
          cyan: '#06b6d4', // 霓虹青
          pink: '#ec4899', // 赛博粉
          purple: '#8b5cf6', // 科幻紫
        },
        // 深色背景
        dark: {
          bg: '#0a0e27', // 主背景
          surface: '#111827', // 表面
          card: '#1f2937', // 卡片
          border: '#374151', // 边框
        },
      },
      boxShadow: {
        'neon-blue': '0 0 20px rgba(14, 165, 233, 0.5)',
        'neon-cyan': '0 0 20px rgba(6, 182, 212, 0.5)',
        'neon-pink': '0 0 20px rgba(236, 72, 153, 0.5)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'slide-in': 'slide-in 0.3s ease-out',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'slide-in': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
