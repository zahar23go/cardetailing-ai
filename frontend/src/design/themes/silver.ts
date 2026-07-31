import type { BrandTheme } from '../tokens';

/** Пресет Silver — заготовка под второй металл (имитация кастомизации) */
export const silverTheme: BrandTheme = {
  id: 'silver',
  label: 'Silver',
  preview: '/design-refs/gold-glow.png',

  colors: {
    bg: {
      page: '#070809',
      phone: '#000000',
      input: '#141618',
      elevated: '#16191C',
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#A8B0BA',
      onAccent: '#0B0D10',
      label: '#C5CDD6',
    },
    accent: {
      solid: '#C5CDD6',
      soft: '#E2E8EE',
      muted: 'rgba(197, 205, 214, 0.15)',
      border: 'rgba(197, 205, 214, 0.4)',
    },
    danger: '#E74C3C',
    success: '#0F5D46',
  },

  gradients: {
    goldButton:
      'linear-gradient(180deg, #E8EEF3 0%, #C5CDD6 40%, #9AA5B1 75%, #7A8694 100%)',
    hairline:
      'linear-gradient(90deg, transparent, rgba(197,205,214,0.4) 30%, rgba(226,232,238,0.7) 50%, rgba(197,205,214,0.4) 70%, transparent)',
    pageAtmosphere:
      'radial-gradient(ellipse 70% 50% at 50% 20%, #1a1e24 0%, transparent 55%), #070809',
  },

  shadows: {
    goldButton:
      '0 14px 32px rgba(150, 160, 175, 0.35), inset 0 1px 0 rgba(255,255,255,0.55)',
    phone: '0 40px 90px rgba(0,0,0,0.75)',
    inputFocus: '0 0 0 3px rgba(197, 205, 214, 0.18)',
  },

  fonts: {
    ui: '"Manrope", "Montserrat", -apple-system, BlinkMacSystemFont, sans-serif',
    display: '"Cinzel", "Times New Roman", serif',
  },

  radii: {
    sm: '10px',
    md: '14px',
    lg: '16px',
    xl: '20px',
    phone: '48px',
  },

  assets: {
    logoCar: '/images/header-car-logo.png',
    heroCar: '/images/login-car.png',
    aiOrb: '/images/ai-orb.png',
  },
};
