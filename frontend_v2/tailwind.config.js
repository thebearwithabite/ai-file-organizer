/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Liquid Glass Design System
        background: '#0A0E1A',
        foreground: '#FFFFFF',

        primary: {
          DEFAULT: '#3B82F6',
          hover: '#2563EB',
        },

        secondary: {
          DEFAULT: '#6366F1',
          hover: '#4F46E5',
        },

        'accent-purple': {
          DEFAULT: '#8B5CF6',
          hover: '#7C3AED',
        },

        'accent-cyan': {
          DEFAULT: '#06B6D4',
          hover: '#0891B2',
        },

        success: '#10B981',
        warning: '#F59E0B',
        destructive: '#EF4444',

        'glass-border': 'rgba(255, 255, 255, 0.1)',
        'glass-bg': 'rgba(255, 255, 255, 0.07)',
      },

      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glass-lg': '0 12px 48px 0 rgba(0, 0, 0, 0.47)',
      },

      backdropBlur: {
        'xs': '2px',
        'sm': '4px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        '2xl': '24px',
        '3xl': '32px',
      },

      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
