import type { BrandTheme } from './tokens';
import type { SurfaceMode, SurfacePalette } from './surface';
import { getSurfaceMode, surfacePalettes } from './surface';

/** Пробрасывает токены бренда + режим поверхности в CSS-переменные */
export function applyBrandCssVars(
  brand: BrandTheme,
  surfaceMode?: SurfaceMode,
  root: HTMLElement = document.documentElement,
) {
  const mode = getSurfaceMode(surfaceMode);
  const surface = surfacePalettes[mode];
  const c = brand.colors;

  root.setAttribute('data-surface', mode);

  // Поверхность (фон / карточки / текст)
  root.style.setProperty('--color-graphite', surface.page);
  root.style.setProperty('--color-carbon', surface.card);
  root.style.setProperty('--color-elevated', surface.elevated);
  root.style.setProperty('--color-white', surface.textPrimary);
  root.style.setProperty('--color-titanium', surface.textSecondary);
  root.style.setProperty('--color-divider', surface.divider);
  root.style.setProperty('--color-sidebar', surface.sidebar);
  root.style.setProperty('--color-header', surface.header);
  root.style.setProperty('--color-card-important', surface.cardImportant);
  root.style.setProperty('--shadow-card', surface.shadowCard);
  root.style.setProperty('--btn-secondary-bg', surface.btnSecondaryBg);
  root.style.setProperty('--btn-secondary-hover', surface.btnSecondaryHover);
  root.style.setProperty('--btn-secondary-text', surface.btnSecondaryText);

  // Акцент бренда (золото и т.п. — общее для обоих режимов)
  root.style.setProperty('--color-gold', c.accent.solid);
  root.style.setProperty('--color-gold-hover', c.accent.soft);
  root.style.setProperty('--color-gold-shadow', c.accent.muted);
  root.style.setProperty('--color-success', c.success);
  root.style.setProperty('--brand-gold-button-bg', brand.gradients.goldButton);
  root.style.setProperty('--brand-gold-button-color', c.text.onAccent);
  root.style.setProperty('--brand-gold-button-shadow', brand.shadows.goldButton);
  root.style.setProperty('--brand-input-bg', surface.elevated);
  root.style.setProperty('--brand-input-border', surface.divider);
  root.style.setProperty('--brand-label', c.text.label);
  root.style.setProperty('--radius-md', brand.radii.md);
  root.style.setProperty('--radius-lg', brand.radii.lg);
  root.style.setProperty('--radius-card', brand.radii.xl);
  root.style.setProperty('--font-family', brand.fonts.ui);
  root.style.setProperty('--font-display', brand.fonts.display);
  root.style.setProperty('--font-header', brand.fonts.ui);
  root.style.setProperty('--font-body', brand.fonts.ui);

  // legacy nd-*
  root.style.setProperty('--nd-bg', surface.page);
  root.style.setProperty('--nd-surface', surface.card);
  root.style.setProperty('--nd-elevated', surface.elevated);
  root.style.setProperty('--nd-sidebar', surface.sidebar);
  root.style.setProperty('--nd-border', surface.divider);
  root.style.setProperty('--nd-primary', c.accent.solid);
  root.style.setProperty('--nd-primary-hover', c.accent.soft);
  root.style.setProperty('--nd-text', surface.textPrimary);
  root.style.setProperty('--nd-muted', surface.textSecondary);
  root.style.setProperty('--nd-danger', c.danger);
}

export function buildStyledTheme(brand: BrandTheme, surfaceMode?: SurfaceMode) {
  const mode = getSurfaceMode(surfaceMode);
  const surface: SurfacePalette = surfacePalettes[mode];

  return {
    colors: {
      bg: {
        primary: surface.page,
        secondary: surface.card,
        tertiary: surface.elevated,
        card: surface.card,
        elevated: surface.elevated,
      },
      text: {
        primary: surface.textPrimary,
        secondary: surface.textSecondary,
        tertiary: '#6B7280',
      },
      border: {
        primary: surface.divider,
        secondary: surface.divider,
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
    surfaceMode: mode,
    surface,
    brand,
  } as const;
}

export type AppTheme = ReturnType<typeof buildStyledTheme>;
