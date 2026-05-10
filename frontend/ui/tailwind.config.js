/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 深蓝星渊 Abyssal Star 主题色
        'void': {
          DEFAULT: '#050810',
          deep: '#020408',
          surface: '#0a1028',
          card: 'rgba(10, 20, 50, 0.55)',
          panel: 'rgba(8, 16, 40, 0.7)',
        },
        'aether': {
          DEFAULT: '#00e5ff',
          bright: '#40f0ff',
          dim: 'rgba(0, 229, 255, 0.35)',
          glow: 'rgba(0, 229, 255, 0.15)',
        },
        'resonance': {
          DEFAULT: '#7c4dff',
          bright: '#b388ff',
          dim: 'rgba(124, 77, 255, 0.3)',
          glow: 'rgba(124, 77, 255, 0.12)',
        },
        'starlight': {
          DEFAULT: '#ffab40',
          dim: 'rgba(255, 171, 64, 0.35)',
        },
        'text': {
          primary: '#e0e6f0',
          secondary: '#8892b0',
          dim: '#4a5580',
        },
        'border': {
          glass: 'rgba(0, 229, 255, 0.12)',
          active: 'rgba(0, 229, 255, 0.3)',
        },
        'status': {
          active: '#4cff8d',
          idle: '#455366',
          error: '#ff5252',
          warning: '#ffab40',
        },
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.25rem',
        '3xl': '1.75rem',
      },
      boxShadow: {
        'card': '0 4px 24px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(0, 229, 255, 0.06)',
        'card-hover': '0 8px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(0, 229, 255, 0.2), 0 0 30px rgba(0, 229, 255, 0.08)',
        'glow-aether': '0 0 20px rgba(0, 229, 255, 0.25), 0 0 60px rgba(0, 229, 255, 0.06)',
        'glow-resonance': '0 0 20px rgba(124, 77, 255, 0.25), 0 0 60px rgba(124, 77, 255, 0.06)',
        'glow-starlight': '0 0 16px rgba(255, 171, 64, 0.25)',
        'inset-glow': 'inset 0 0 30px rgba(0, 229, 255, 0.02)',
      },
      keyframes: {
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        'pulse-energy': {
          '0%, 100%': { opacity: '0.4', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.08)' },
        },
        'border-pulse': {
          '0%, 100%': { borderColor: 'rgba(0, 229, 255, 0.15)' },
          '50%': { borderColor: 'rgba(0, 229, 255, 0.4)' },
        },
        'shine': {
          '0%': { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        'particle-drift': {
          '0%, 100%': { transform: 'translateY(0) translateX(0) scale(1)', opacity: '0.5' },
          '50%': { transform: 'translateY(-15px) translateX(8px) scale(1.3)', opacity: '0.8' },
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(200%)' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'resonance-wave': {
          '0%': { boxShadow: '0 0 0 0 rgba(0, 229, 255, 0.4)' },
          '100%': { boxShadow: '0 0 0 12px rgba(0, 229, 255, 0)' },
        },
        'rotate-aurora': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'float': 'float 5s ease-in-out infinite',
        'pulse-energy': 'pulse-energy 2.5s ease-in-out infinite',
        'border-pulse': 'border-pulse 3s ease-in-out infinite',
        'shine': 'shine 2.5s linear infinite',
        'particle-drift': 'particle-drift 6s ease-in-out infinite',
        'scan-line': 'scan-line 3s linear infinite',
        'fade-in-up': 'fade-in-up 0.4s ease-out both',
        'resonance-wave': 'resonance-wave 2s ease-out infinite',
        'rotate-aurora': 'rotate-aurora 30s linear infinite',
      },
      fontFamily: {
        'display': ['"Noto Sans SC"', '"PingFang SC"', 'sans-serif'],
        'mono': ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
    },
  },
  plugins: [],
}
