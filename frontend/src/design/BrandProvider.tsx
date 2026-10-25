import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ThemeProvider } from 'styled-components';
import { ConfigProvider, theme as antdTheme } from 'antd';
import type { BrandTheme, BrandThemeId } from './tokens';
import { brandThemes, getBrandTheme, storeBrandId } from './themes';
import { applyBrandCssVars, buildStyledTheme, type AppTheme } from './applyBrand';
import type { SurfaceMode } from './surface';
import {
  DEFAULT_SURFACE_MODE,
  getSurfaceMode,
  storeSurfaceMode,
  surfacePalettes,
} from './surface';

/** White Label салона, как его отдаёт GET /api/branding. */
export interface ServerBranding {
  accent_solid?: string | null;
  radius_md?: string | null;
  font_ui?: string | null;
  base_theme?: BrandThemeId | null;
  surface_mode?: SurfaceMode | null;
  logo_url?: string | null;
  name?: string | null;
}

/** Кэш последнего брендинга с сервера: только чтобы не мигать до ответа /api/me. */
export const BRANDING_CACHE_KEY = 'serverBranding';

function readCachedBranding(): ServerBranding | null {
  try {
    const raw = localStorage.getItem(BRANDING_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as ServerBranding) : null;
  } catch {
    return null;
  }
}

interface BrandContextValue {
  brand: BrandTheme;
  brandId: BrandThemeId;
  setBrandId: (id: BrandThemeId) => void;
  themes: typeof brandThemes;
  surfaceMode: SurfaceMode;
  setSurfaceMode: (mode: SurfaceMode) => void;
  surfaces: typeof surfacePalettes;
  serverBranding: ServerBranding | null;
  applyRemoteBranding: (branding?: ServerBranding | null) => void;
}

const BrandContext = createContext<BrandContextValue | null>(null);

export function BrandProvider({ children }: { children: React.ReactNode }) {
  const [serverBranding, setServerBranding] = useState<ServerBranding | null>(() => readCachedBranding());
  const [brandId, setBrandIdState] = useState<BrandThemeId>(
    () => serverBranding?.base_theme || getBrandTheme().id,
  );
  const [surfaceMode, setSurfaceModeState] = useState<SurfaceMode>(
    () => serverBranding?.surface_mode || getSurfaceMode(),
  );
  const brand = useMemo(() => getBrandTheme(brandId), [brandId]);
  const surface = surfacePalettes[surfaceMode];
  const styledTheme: AppTheme = useMemo(
    () => buildStyledTheme(brand, surfaceMode),
    [brand, surfaceMode],
  );

  useEffect(() => {
    applyBrandCssVars(brand, surfaceMode);
    if (serverBranding?.accent_solid) {
      document.documentElement.style.setProperty('--color-gold', serverBranding.accent_solid);
      document.documentElement.style.setProperty('--nd-primary', serverBranding.accent_solid);
    }
    if (serverBranding?.radius_md) {
      document.documentElement.style.setProperty('--radius-md', serverBranding.radius_md);
      document.documentElement.style.setProperty('--radius-lg', serverBranding.radius_md);
    }
    if (serverBranding?.font_ui) {
      document.documentElement.style.setProperty('--font-family', serverBranding.font_ui);
      document.documentElement.style.setProperty('--font-body', serverBranding.font_ui);
    }
  }, [brand, surfaceMode, serverBranding]);

  const setBrandId = useCallback((id: BrandThemeId) => {
    storeBrandId(id);
    setBrandIdState(id);
  }, []);

  const setSurfaceMode = useCallback((mode: SurfaceMode) => {
    storeSurfaceMode(mode);
    setSurfaceModeState(mode);
  }, []);

  /** Применить брендинг салона с сервера (после /api/me, логина или сохранения). */
  const applyRemoteBranding = useCallback((remote?: ServerBranding | null) => {
    if (!remote) return;
    setServerBranding(remote);
    try {
      localStorage.setItem(BRANDING_CACHE_KEY, JSON.stringify(remote));
    } catch {
      /* ignore */
    }
    if (remote.base_theme) {
      storeBrandId(remote.base_theme);
      setBrandIdState(remote.base_theme);
    }
    if (remote.surface_mode) {
      storeSurfaceMode(remote.surface_mode);
      setSurfaceModeState(remote.surface_mode);
    }
  }, []);

  const value = useMemo(
    () => ({
      brand,
      brandId,
      setBrandId,
      themes: brandThemes,
      surfaceMode,
      setSurfaceMode,
      surfaces: surfacePalettes,
      serverBranding,
      applyRemoteBranding,
    }),
    [brand, brandId, setBrandId, surfaceMode, setSurfaceMode, serverBranding, applyRemoteBranding],
  );

  const algorithm = antdTheme.darkAlgorithm;

  return (
    <BrandContext.Provider value={value}>
      <ThemeProvider theme={styledTheme}>
        <ConfigProvider
          theme={{
            algorithm,
            token: {
              colorPrimary: brand.colors.accent.solid,
              colorBgBase: surface.page,
              colorBgLayout: surface.page,
              colorBgContainer: surface.card,
              colorBgElevated: surface.elevated,
              colorBgSpotlight: surface.card,
              colorTextLightSolid: brand.colors.accent.solid,
              colorBorder: surface.divider,
              colorBorderSecondary: surface.divider,
              colorText: surface.textPrimary,
              colorTextSecondary: surface.textSecondary,
              borderRadius: parseInt(brand.radii.md, 10) || 14,
              fontFamily: brand.fonts.ui,
            },
          }}
        >
          {children}
        </ConfigProvider>
      </ThemeProvider>
    </BrandContext.Provider>
  );
}

export function useBrand() {
  const ctx = useContext(BrandContext);
  if (!ctx) throw new Error('useBrand must be used within BrandProvider');
  return ctx;
}

export { DEFAULT_SURFACE_MODE };
