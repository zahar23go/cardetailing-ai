import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ThemeProvider } from 'styled-components';
import { ConfigProvider } from 'antd';
import type { BrandTheme, BrandThemeId } from './tokens';
import { brandThemes, getBrandTheme, storeBrandId } from './themes';
import { applyBrandCssVars, buildStyledTheme, type AppTheme } from './applyBrand';

interface BrandContextValue {
  brand: BrandTheme;
  brandId: BrandThemeId;
  setBrandId: (id: BrandThemeId) => void;
  themes: typeof brandThemes;
}

const BrandContext = createContext<BrandContextValue | null>(null);

export function BrandProvider({ children }: { children: React.ReactNode }) {
  const [brandId, setBrandIdState] = useState<BrandThemeId>(() => getBrandTheme().id);
  const brand = useMemo(() => getBrandTheme(brandId), [brandId]);
  const styledTheme: AppTheme = useMemo(() => buildStyledTheme(brand), [brand]);

  useEffect(() => {
    applyBrandCssVars(brand);
    // Применяем ручные overrides с страницы брендинга (релиз / клиент)
    try {
      const raw = localStorage.getItem('brandOverrides');
      if (!raw) return;
      const o = JSON.parse(raw) as { accentSolid?: string; radiusMd?: string; fontUi?: string };
      if (o.accentSolid) {
        document.documentElement.style.setProperty('--color-gold', o.accentSolid);
        document.documentElement.style.setProperty('--nd-primary', o.accentSolid);
      }
      if (o.radiusMd) document.documentElement.style.setProperty('--radius-md', o.radiusMd);
      if (o.fontUi) document.documentElement.style.setProperty('--font-family', o.fontUi);
    } catch {
      /* ignore */
    }
  }, [brand]);

  const setBrandId = useCallback((id: BrandThemeId) => {
    storeBrandId(id);
    setBrandIdState(id);
  }, []);

  const value = useMemo(
    () => ({ brand, brandId, setBrandId, themes: brandThemes }),
    [brand, brandId, setBrandId],
  );

  return (
    <BrandContext.Provider value={value}>
      <ThemeProvider theme={styledTheme}>
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: brand.colors.accent.solid,
              colorBgContainer: brand.colors.bg.elevated,
              colorBgElevated: brand.colors.bg.elevated,
              colorText: brand.colors.text.primary,
              colorTextSecondary: brand.colors.text.secondary,
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
