export type { BrandTheme, BrandThemeId } from './tokens';
export type { SurfaceMode, SurfacePalette } from './surface';
export {
  brandThemes,
  getBrandTheme,
  ACTIVE_BRAND_THEME,
  goldMetalTheme,
  goldGlowTheme,
  silverTheme,
  storeBrandId,
  readStoredBrandId,
} from './themes';
export {
  surfacePalettes,
  getSurfaceMode,
  storeSurfaceMode,
  readStoredSurfaceMode,
  DEFAULT_SURFACE_MODE,
} from './surface';
export {
  GoldButton,
  GhostGoldButton,
  GoldField,
  SilverButton,
} from './components/BrandControls';
export { GoldCarLogo } from './components/GoldCarLogo';
export { BrandProvider, useBrand } from './BrandProvider';
export { applyBrandCssVars, buildStyledTheme } from './applyBrand';
export type { AppTheme } from './applyBrand';
