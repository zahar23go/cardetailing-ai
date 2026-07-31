import type { BrandTheme } from '../tokens';

/**
 * Пресет A — «Gold Metal»
 * Референс: /design-refs/gold-metal.png
 * Кнопка: металлический горизонтальный градиент, тёмный текст на золоте.
 */
export const goldMetalTheme: BrandTheme = {
  id: 'goldMetal',
  label: 'Gold Metal',
  preview: '/design-refs/gold-metal.png',

  colors: {
    bg: {
      page: '#050505',
      phone: '#000000',
      input: '#121214',
      elevated: '#141312',
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#AAB2BF',
      onAccent: '#1A1408',
      label: '#D4A84B',
    },
    accent: {
      solid: '#D4A84B',
      soft: '#E0BC5A',
      muted: 'rgba(212, 168, 75, 0.15)',
      border: 'rgba(212, 168, 75, 0.35)',
    },
    danger: '#E74C3C',
    success: '#0F5D46',
  },

  gradients: {
    goldButton:
      'linear-gradient(90deg, #8F6A22 0%, #C49A3C 18%, #F0D9A0 48%, #E0BC5A 62%, #B8892E 82%, #8F6A22 100%)',
    hairline:
      'linear-gradient(90deg, transparent, rgba(212,168,75,0.45) 30%, rgba(240,217,160,0.75) 50%, rgba(212,168,75,0.45) 70%, transparent)',
    pageAtmosphere:
      'radial-gradient(ellipse 70% 50% at 50% 20%, #2a2218 0%, transparent 55%), #050505',
  },

  shadows: {
    goldButton:
      '0 14px 32px rgba(184, 137, 46, 0.4), inset 0 1px 0 rgba(255,255,255,0.45), inset 0 -2px 0 rgba(0,0,0,0.2)',
    phone: '0 40px 90px rgba(0,0,0,0.75), 0 0 0 1px rgba(255,255,255,0.08)',
    inputFocus: '0 0 0 3px rgba(212, 168, 75, 0.16)',
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
    logoCar: '/images/logo-formula-sport.png',
    heroCar: '/images/login-car.png',
    aiOrb: '/images/ai-orb.png',
  },
};
