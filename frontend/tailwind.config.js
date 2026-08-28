/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 赛博朋克色彩主题
        cyber: {
          bg: '#0a0e27',        // 深空蓝
          bgSecondary: '#0f1629', // 次要背景
          accent: '#00d9ff',     // 霓虹青
          accentSecondary: '#a855f7', // 电子紫
          text: '#e5e7eb',      // 主文字
          textSecondary: '#9ca3af', // 次要文字
          success: '#10b981',    // 成功翡翠绿
          warning: '#f59e0b',    // 警告琥珀橙
          danger: '#ef4444',      // 危险赤红
          info: '#3b82f6',        // 信息蓝
        },
        glass: {
          bg: 'rgba(15, 22, 41, 0.6)',
          border: 'rgba(255, 255, 255, 0.1)',
        },
      },
      fontFamily: {
        orbitron: ['Orbitron', 'system-ui', 'sans-serif'],
        jetbrains: ['JetBrains Mono', 'monospace'],
        sans: ['Noto Sans SC', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'neon': '0 0 5px var(--tw-shadow-color), 0 0 20px var(--tw-shadow-color)',
      },
    },
  },
  plugins: [],
};
