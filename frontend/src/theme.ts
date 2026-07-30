export const theme = {
  colors: {
    bg: {
      primary: '#0B0D10',
      secondary: '#13161A',
      tertiary: '#1A1E23',
      card: 'rgba(26, 30, 35, 0.72)',
      elevated: '#1A1E23',
    },

    text: {
      primary: '#FFFFFF',
      secondary: '#AAB2BF',
      tertiary: '#6B7280',
    },

    border: {
      primary: 'rgba(255, 255, 255, 0.08)',
      secondary: 'rgba(255, 255, 255, 0.05)',
      gold: 'rgba(200, 169, 119, 0.35)',
    },

    accent: {
      primary: '#C8A977',
      secondary: '#D5B98D',
      tertiary: '#E8D4B0',
      muted: 'rgba(200, 169, 119, 0.15)',
    },

    danger: '#E74C3C',
    success: '#0F5D46',
  },

  fonts: {
    primary: '"Manrope", "Montserrat", -apple-system, BlinkMacSystemFont, sans-serif',
    display: '"Cinzel", "Times New Roman", serif',
  },

  radii: {
    sm: '10px',
    md: '14px',
    lg: '20px',
    xl: '24px',
  },

  sizes: {
    bottomNavHeight: '84px',
    maxMobileWidth: '430px',
  },
} as const;

export type AppTheme = typeof theme;
