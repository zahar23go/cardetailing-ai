/** Режим поверхности UI: светлый (основной) и тёмный графит. */

export type SurfaceMode = 'light' | 'dark';

export const SURFACE_STORAGE_KEY = 'surfaceMode';
export const DEFAULT_SURFACE_MODE: SurfaceMode = 'light';

export interface SurfacePalette {
  label: string;
  description: string;
  page: string;
  sidebar: string;
  header: string;
  card: string;
  cardImportant: string;
  elevated: string;
  divider: string;
  textPrimary: string;
  textSecondary: string;
  shadowCard: string;
  btnSecondaryBg: string;
  btnSecondaryHover: string;
  btnSecondaryText: string;
}

export const surfacePalettes: Record<SurfaceMode, SurfacePalette> = {
  /** Основной: белый контент + тёмные chrome/карточки (как на скрине) */
  light: {
    label: 'Светлый',
    description: 'Белый контент, тёмные шапка/меню и карточки — как раньше',
    page: '#FFFFFF',
    sidebar: '#0B0D10',
    header: '#0B0D10',
    card: '#161B22',
    cardImportant: '#1A1D23',
    elevated: '#161B22',
    divider: '#2D333B',
    textPrimary: '#F0F2F5',
    textSecondary: '#9BA3B5',
    shadowCard: '0 8px 28px rgba(0, 0, 0, 0.22)',
    btnSecondaryBg: '#121214',
    btnSecondaryHover: '#1C1C20',
    btnSecondaryText: '#F0D9A0',
  },
  /** Второй: полный тёмный графит */
  dark: {
    label: 'Тёмный графит',
    description: 'Весь интерфейс в графите — luxury dark',
    page: '#1A1D23',
    sidebar: '#15181E',
    header: '#1E2128',
    card: '#282C34',
    cardImportant: '#2F3540',
    elevated: '#282C34',
    divider: '#3B4049',
    textPrimary: '#F0F2F5',
    textSecondary: '#9BA3B5',
    shadowCard: '0 6px 32px rgba(0, 0, 0, 0.5)',
    btnSecondaryBg: '#3B4049',
    btnSecondaryHover: '#4A505C',
    btnSecondaryText: '#F0F2F5',
  },
};

export function readStoredSurfaceMode(): SurfaceMode | null {
  if (typeof window === 'undefined') return null;
  const v = window.localStorage.getItem(SURFACE_STORAGE_KEY);
  if (v === 'light' || v === 'dark') return v;
  try {
    const raw = window.localStorage.getItem('brandOverrides');
    if (!raw) return null;
    const o = JSON.parse(raw) as { surfaceMode?: string };
    if (o.surfaceMode === 'light' || o.surfaceMode === 'dark') return o.surfaceMode;
  } catch {
    /* ignore */
  }
  return null;
}

export function storeSurfaceMode(mode: SurfaceMode) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(SURFACE_STORAGE_KEY, mode);
}

export function getSurfaceMode(mode?: SurfaceMode): SurfaceMode {
  return mode || readStoredSurfaceMode() || DEFAULT_SURFACE_MODE;
}
