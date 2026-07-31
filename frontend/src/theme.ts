/**
 * Совместимость: старый `import { theme } from './theme'`.
 * Живой бренд идёт через BrandProvider; этот объект — стартовый снимок.
 */
import { getBrandTheme } from './design';
import { buildStyledTheme } from './design/applyBrand';

export const theme = buildStyledTheme(getBrandTheme());
export type { AppTheme } from './design/applyBrand';
