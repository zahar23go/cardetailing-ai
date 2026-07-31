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

interface BrandContextValue {
  brand: BrandTheme;
  brandId: BrandThemeId;
  setBrandId: (id: BrandThemeId) => void;
  themes: typeof brandThemes;
  surfaceMode: SurfaceMode;
  setSurfaceMode: (mode: SurfaceMode) => void;
  surfaces: typeof surfacePalettes;
}

const BrandContext = createContext<BrandContextValue | null>(null);

export function BrandProvider({ children }: { children: React.ReactNode }) {
  const [brandId, setBrandIdState] = useState<BrandThemeId>(() => getBrandTheme().id);
  const [surfaceMode, setSurfaceModeState] = useState<SurfaceMode>(() => getSurfaceMode());
  const brand = useMemo(() => getBrandTheme(brandId), [brandId]);
  const surface = surfacePalettes[surfaceMode];
  const styledTheme: AppTheme = useMemo(
    () => buildStyledTheme(brand, surfaceMode),
    [brand, surfaceMode],
  );

  useEffect(() => {
    applyBrandCssVars(brand, surfaceMode);
    try {
      const raw = localStorage.getItem('brandOverrides');
      if (!raw) return;
      const o = JSON.parse(raw) as {
        accentSolid?: string;
        radiusMd?: string;
        fontUi?: string;
        surfaceMode?: SurfaceMode;
      };
      if (o.accentSolid) {
        document.documentElement.style.setProperty('--color-gold', o.accentSolid);
        document.documentElement.style.setProperty('--nd-primary', o.accentSolid);
      }
      if (o.radiusMd) document.documentElement.style.setProperty('--radius-md', o.radiusMd);
      if (o.fontUi) document.documentElement.style.setProperty('--font-family', o.fontUi);
    } catch {
      /* ignore */
    }
  }, [brand, surfaceMode]);

  const setBrandId = useCallback((id: BrandThemeId) => {
    storeBrandId(id);
    setBrandIdState(id);
  }, []);

  const setSurfaceMode = useCallback((mode: SurfaceMode) => {
    storeSurfaceMode(mode);
    setSurfaceModeState(mode);
    try {
      const raw = localStorage.getItem('brandOverrides');
      const prev = raw ? JSON.parse(raw) : {};
      localStorage.setItem('brandOverrides', JSON.stringify({ ...prev, surfaceMode: mode }));
    } catch {
      /* ignore */
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
    }),
    [brand, brandId, setBrandId, surfaceMode, setSurfaceMode],
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
