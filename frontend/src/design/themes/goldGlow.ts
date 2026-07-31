import type { BrandTheme } from '../tokens';

/**
 * Пресет B — «Gold Glow»
 * Референс: /design-refs/gold-glow.png
 * Кнопка: вертикальный металлический градиент, светлый текст, мягкое золотое свечение.
 */
export const goldGlowTheme: BrandTheme = {
  id: 'goldGlow',
  label: 'Gold Glow',
  preview: '/design-refs/gold-glow.png',

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
      onAccent: '#FFFFFF',
      label: '#D4A84B',
    },
    accent: {
      solid: '#D4A84B',
      soft: '#E0BC5A',
      muted: 'rgba(212, 168, 75, 0.15)',
      border: 'rgba(212, 168, 75, 0.4)',
    },
    danger: '#E74C3C',
    success: '#0F5D46',
  },

  gradients: {
    goldButton:
      'linear-gradient(180deg, #C49A3C 0%, #E0BC5A 32%, #D4A84B 55%, #B8892E 82%, #8F6A22 100%)',
    hairline:
      'linear-gradient(90deg, transparent, rgba(212,168,75,0.35) 30%, rgba(240,217,160,0.55) 50%, rgba(212,168,75,0.35) 70%, transparent)',
    pageAtmosphere:
      'radial-gradient(ellipse 80% 55% at 50% 18%, #2a2218 0%, transparent 55%), linear-gradient(180deg, #0c0b0a 0%, #050505 45%, #000 100%)',
  },

  shadows: {
    goldButton:
      '0 16px 36px rgba(184, 137, 46, 0.55), 0 0 0 1px rgba(240, 217, 160, 0.25), inset 0 1px 0 rgba(255,255,255,0.45)',
    phone: '0 30px 80px rgba(0,0,0,0.85), 0 0 0 1px rgba(212,168,75,0.08)',
    inputFocus: '0 0 0 3px rgba(212, 168, 75, 0.18), 0 8px 24px rgba(0,0,0,0.35)',
  },

  fonts: {
    ui: '"Manrope", "Montserrat", -apple-system, BlinkMacSystemFont, sans-serif',
    display: '"Cinzel", "Times New Roman", serif',
  },

  radii: {
    sm: '10px',
    md: '14px',
    lg: '16px',
    xl: '24px',
    phone: '48px',
  },

  assets: {
    logoCar: '/images/header-car-logo.png',
    heroCar: '/images/login-car.png',
    aiOrb: '/images/ai-orb.png',
  },
};
