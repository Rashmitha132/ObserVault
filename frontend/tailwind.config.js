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
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#b9ddfd',
          300: '#7cc2fb',
          400: '#36a3f7',
          500: '#0c87eb',
          600: '#026bc9',
          700: '#0255a3',
          800: '#064986',
          900: '#0a3d6f',
          950: '#07274a',
        },
        vault: {
          950: '#070b14',
          900: '#0b1120',
          850: '#0f172a',
          800: '#142036',
          700: '#1e2e4a',
          600: '#334155',
          500: '#64748b',
          400: '#94a3b8',
          accent: '#06b6d4',
          accentGlow: '#0891b2',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          shield: '#6366f1',
          lavender: '#8b5cf6'
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'soft-sm': '0 2px 8px -2px rgba(15, 23, 42, 0.05), 0 1px 4px -1px rgba(15, 23, 42, 0.03)',
        'soft-md': '0 6px 20px -4px rgba(15, 23, 42, 0.08), 0 2px 6px -1px rgba(15, 23, 42, 0.04)',
        'soft-lg': '0 12px 30px -6px rgba(15, 23, 42, 0.12), 0 4px 10px -2px rgba(15, 23, 42, 0.06)',
        'glow-cyan': '0 0 25px -4px rgba(6, 182, 212, 0.35)',
        'glow-indigo': '0 0 25px -4px rgba(99, 102, 241, 0.35)',
        'glow-purple': '0 0 25px -4px rgba(139, 92, 246, 0.35)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        pulseSlow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        }
      },
      animation: {
        fadeIn: 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        pulseSlow: 'pulseSlow 3s ease-in-out infinite',
      }
    },
  },
  plugins: [],
}
