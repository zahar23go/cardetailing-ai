import type { BrandTheme } from './tokens';

/** Пробрасывает токены бренда в CSS-переменные — единый стиль для Ant Design и старых .css */
export function applyBrandCssVars(brand: BrandTheme, root: HTMLElement = document.documentElement) {
  const c = brand.colors;
  root.style.setProperty('--color-graphite', c.bg.page);
  root.style.setProperty('--color-carbon', c.bg.elevated);
  root.style.setProperty('--color-elevated', c.bg.input);
  root.style.setProperty('--color-white', c.text.primary);
  root.style.setProperty('--color-titanium', c.text.secondary);
  root.style.setProperty('--color-gold', c.accent.solid);
  root.style.setProperty('--color-gold-hover', c.accent.soft);
  root.style.setProperty('--color-gold-shadow', c.accent.muted);
  root.style.setProperty('--color-success', c.success);
  root.style.setProperty('--brand-gold-button-bg', brand.gradients.goldButton);
  root.style.setProperty('--brand-gold-button-color', c.text.onAccent);
  root.style.setProperty('--brand-gold-button-shadow', brand.shadows.goldButton);
  root.style.setProperty('--brand-input-bg', c.bg.input);
  root.style.setProperty('--brand-input-border', c.accent.border);
  root.style.setProperty('--brand-label', c.text.label);
  root.style.setProperty('--radius-md', brand.radii.md);
  root.style.setProperty('--radius-lg', brand.radii.lg);
  root.style.setProperty('--radius-card', brand.radii.xl);
  root.style.setProperty('--font-family', brand.fonts.ui);
  root.style.setProperty('--font-display', brand.fonts.display);
  root.style.setProperty('--font-header', brand.fonts.ui);
  root.style.setProperty('--font-body', brand.fonts.ui);

  // legacy nd-*
  root.style.setProperty('--nd-bg', c.bg.page);
  root.style.setProperty('--nd-surface', c.bg.elevated);
  root.style.setProperty('--nd-elevated', c.bg.input);
  root.style.setProperty('--nd-primary', c.accent.solid);
  root.style.setProperty('--nd-primary-hover', c.accent.soft);
  root.style.setProperty('--nd-text', c.text.primary);
  root.style.setProperty('--nd-muted', c.text.secondary);
  root.style.setProperty('--nd-danger', c.danger);
}

export function buildStyledTheme(brand: BrandTheme) {
  return {
    colors: {
      bg: {
        primary: brand.colors.bg.page,
        secondary: brand.colors.bg.elevated,
        tertiary: brand.colors.bg.input,
        card: 'rgba(26, 30, 35, 0.72)',
        elevated: brand.colors.bg.elevated,
      },
      text: {
        primary: brand.colors.text.primary,
        secondary: brand.colors.text.secondary,
        tertiary: '#6B7280',
      },
      border: {
        primary: 'rgba(255, 255, 255, 0.08)',
        secondary: 'rgba(255, 255, 255, 0.05)',
        gold: brand.colors.accent.border,
      },
      accent: {
        primary: brand.colors.accent.solid,
        secondary: brand.colors.accent.soft,
        tertiary: '#E8D4B0',
        muted: brand.colors.accent.muted,
      },
      danger: brand.colors.danger,
      success: brand.colors.success,
    },
    fonts: {
      primary: brand.fonts.ui,
      display: brand.fonts.display,
    },
    radii: {
      sm: brand.radii.sm,
      md: brand.radii.md,
      lg: brand.radii.xl,
      xl: brand.radii.xl,
    },
    sizes: {
      bottomNavHeight: '84px',
      maxMobileWidth: '430px',
    },
    brand,
  } as const;
}

export type AppTheme = ReturnType<typeof buildStyledTheme>;
