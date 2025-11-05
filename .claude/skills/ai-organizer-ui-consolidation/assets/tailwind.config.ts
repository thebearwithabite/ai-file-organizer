import type { Config } from 'tailwindcss'

export default {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        border: 'rgba(255, 255, 255, 0.1)',
        input: 'rgba(255, 255, 255, 0.05)',
        ring: 'rgba(10, 132, 255, 0.5)',
        background: '#1e1e2e',
        foreground: '#ffffff',
        primary: {
          DEFAULT: '#0A84FF',
          foreground: '#ffffff',
        },
        secondary: {
          DEFAULT: 'rgba(255, 255, 255, 0.1)',
          foreground: '#ffffff',
        },
        destructive: {
          DEFAULT: '#FF453A',
          foreground: '#ffffff',
        },
        success: {
          DEFAULT: '#30D158',
          foreground: '#ffffff',
        },
        warning: {
          DEFAULT: '#FFD60A',
          foreground: '#000000',
        },
        muted: {
          DEFAULT: 'rgba(255, 255, 255, 0.05)',
          foreground: 'rgba(255, 255, 255, 0.6)',
        },
        accent: {
          DEFAULT: 'rgba(255, 255, 255, 0.1)',
          foreground: '#ffffff',
          purple: '#BF5AF2',
        },
        popover: {
          DEFAULT: 'rgba(30, 30, 46, 0.95)',
          foreground: '#ffffff',
        },
        card: {
          DEFAULT: 'rgba(30, 30, 46, 0.7)',
          foreground: '#ffffff',
        },
      },
      borderRadius: {
        lg: '1rem',
        md: '0.75rem',
        sm: '0.5rem',
      },
      backdropBlur: {
        xs: '2px',
        glass: '12px',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0, 0, 0, 0.37)',
        'glass-lg': '0 12px 48px rgba(0, 0, 0, 0.45)',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Display',
          'SF Pro Text',
          'Inter',
          'system-ui',
          'sans-serif',
        ],
        mono: [
          'SF Mono',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-in-from-top': {
          from: { transform: 'translateY(-10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-in-from-bottom': {
          from: { transform: 'translateY(10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-in-from-top': 'slide-in-from-top 0.3s ease-out',
        'slide-in-from-bottom': 'slide-in-from-bottom 0.3s ease-out',
      },
      transitionTimingFunction: {
        'macos': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config
