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
        cyber: {
          950: '#070B14',
          900: '#0B1120',
          850: '#0F172A',
          800: '#1E293B',
          750: '#27354A',
          700: '#334155',
          600: '#475569',
          500: '#64748B',
          cyan: '#06B6D4',
          neon: '#00F0FF',
          emerald: '#10B981',
          amber: '#F59E0B',
          crimson: '#EF4444',
          shaBlue: '#1E40AF',
          shaRed: '#DC2626',
          shaGreen: '#16A34A',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      boxShadow: {
        'glow-cyan': '0 0 15px -3px rgba(6, 182, 212, 0.25)',
        'glow-crimson': '0 0 15px -3px rgba(239, 68, 68, 0.25)',
        'glow-emerald': '0 0 15px -3px rgba(16, 185, 129, 0.25)',
      }
    },
  },
  plugins: [],
}
