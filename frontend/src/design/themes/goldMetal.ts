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
      page: '#1A1D23',
      phone: '#000000',
      input: '#282C34',
      elevated: '#282C34',
    },
    text: {
      primary: '#F0F2F5',
      secondary: '#9BA3B5',
      onAccent: '#1A1D23',
      label: '#D4AF37',
    },
    accent: {
      solid: '#D4AF37',
      soft: '#E5C04A',
      muted: 'rgba(212, 175, 55, 0.18)',
      border: 'rgba(212, 175, 55, 0.4)',
    },
    danger: '#E74C3C',
    success: '#0F5D46',
  },

  gradients: {
    goldButton: '#D4AF37',
    hairline:
      'linear-gradient(90deg, transparent, rgba(212,175,55,0.45) 30%, rgba(229,192,74,0.75) 50%, rgba(212,175,55,0.45) 70%, transparent)',
    pageAtmosphere: '#1A1D23',
  },

  shadows: {
    goldButton: '0 8px 24px rgba(212, 175, 55, 0.35)',
    phone: '0 40px 90px rgba(0,0,0,0.75), 0 0 0 1px rgba(255,255,255,0.08)',
    inputFocus: '0 0 0 3px rgba(212, 175, 55, 0.18)',
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
