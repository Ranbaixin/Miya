/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#00bcd4',
        'primary-dim': 'rgba(0, 188, 212, 0.6)',
        secondary: '#9c27b0',
        accent: '#e91e63',
        'bg-dark': 'rgba(0, 0, 0, 0.3)',
        'glass-bg': 'rgba(0, 30, 60, 0.5)',
        'glass-border': 'rgba(0, 188, 212, 0.2)',
        'glow-primary': 'rgba(0, 188, 212, 0.3)',
        'glow-secondary': 'rgba(156, 39, 176, 0.25)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'glass': '0 0 20px rgba(0, 188, 212, 0.1), inset 0 0 30px rgba(0, 188, 212, 0.03)',
        'glass-hover': '0 0 30px rgba(0, 188, 212, 0.2), inset 0 0 40px rgba(0, 188, 212, 0.05)',
        'glow': '0 0 10px rgba(0, 188, 212, 0.4), 0 0 20px rgba(0, 188, 212, 0.4)',
        'glow-secondary': '0 0 8px rgba(156, 39, 176, 0.3)',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
        pulseGlow: {
          '0%, 100%': { 
            boxShadow: '0 0 10px rgba(0, 188, 212, 0.4)',
          },
          '50%': { 
            boxShadow: '0 0 25px rgba(0, 188, 212, 0.6), 0 0 40px rgba(0, 188, 212, 0.4)',
          }
        },
        breathe: {
          '0%, 100%': { 
            opacity: '0.5',
            transform: 'scale(1)',
          },
          '50%': { 
            opacity: '1',
            transform: 'scale(1.05)',
          }
        },
        dataFlow: {
          '0%': { 'background-position': '100% 0' },
          '100%': { 'background-position': '-100% 0' },
        },
        particleFloat: {
          '0%, 100%': { 
            transform: 'translateY(0) scale(1)',
            opacity: '0.6',
          },
          '50%': { 
            transform: 'translateY(-20px) scale(0.5)',
            opacity: '0',
          }
        },
        progressShine: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        }
      },
      animation: {
        float: 'float 4s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        breathe: 'breathe 3s ease-in-out infinite',
        'data-flow': 'dataFlow 2s linear infinite',
        'particle-float': 'particleFloat 4s ease-in-out infinite',
        'progress-shine': 'progressShine 1.5s ease-in-out infinite',
      }
    },
  },
  plugins: [],
}