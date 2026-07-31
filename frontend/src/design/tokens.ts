/**
 * Единая схема токенов бренда.
 * На релизе / на странице брендинга меняются значения — страницы не трогаем.
 */
export type BrandThemeId = 'goldMetal' | 'goldGlow' | 'silver' /* зарезервировано */;

export interface BrandTheme {
  id: BrandThemeId;
  /** Человекочитаемое имя пресета */
  label: string;
  /** Референс-скрин в /public/design-refs */
  preview: string;

  colors: {
    bg: {
      page: string;
      phone: string;
      input: string;
      elevated: string;
    };
    text: {
      primary: string;
      secondary: string;
      onAccent: string; // текст на GoldButton
      label: string;
    };
    accent: {
      solid: string;
      soft: string;
      muted: string;
      border: string;
    };
    danger: string;
    success: string;
  };

  gradients: {
    /** Основная заливка GoldButton */
    goldButton: string;
    hairline: string;
    pageAtmosphere: string;
  };

  shadows: {
    goldButton: string;
    phone: string;
    inputFocus: string;
  };

  fonts: {
    ui: string;
    display: string;
  };

  radii: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
    phone: string;
  };

  assets: {
    logoCar: string;
    heroCar: string;
    aiOrb: string;
  };
}
