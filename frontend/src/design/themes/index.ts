import type { BrandTheme, BrandThemeId } from '../tokens';
import { goldMetalTheme } from './goldMetal';
import { goldGlowTheme } from './goldGlow';
import { silverTheme } from './silver';

export const brandThemes: Record<BrandThemeId, BrandTheme> = {
  goldMetal: goldMetalTheme,
  goldGlow: goldGlowTheme,
  silver: silverTheme,
};

/** Дефолт для разработки */
export const ACTIVE_BRAND_THEME: BrandThemeId = 'goldGlow';

const STORAGE_KEY = 'brandTheme';

export function readStoredBrandId(): BrandThemeId | null {
  if (typeof window === 'undefined') return null;
  const v = window.localStorage.getItem(STORAGE_KEY) as BrandThemeId | null;
  if (v && v in brandThemes) return v;
  return null;
}

export function storeBrandId(id: BrandThemeId) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, id);
}

export function getBrandTheme(id?: BrandThemeId): BrandTheme {
  const key = id || readStoredBrandId() || ACTIVE_BRAND_THEME;
  return brandThemes[key] ?? goldGlowTheme;
}

export { goldMetalTheme, goldGlowTheme, silverTheme };
