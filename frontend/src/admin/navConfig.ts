/**
 * Иерархия админ-меню + маппинг URL ↔ ключи навигации.
 */

export type AdminTabKey =
  | 'overview'
  | 'appointments'
  | 'calendar'
  | 'boxes'
  | 'users'
  | 'services'
  | 'financier'
  | 'finances'
  | 'analytics'
  | 'discounts'
  | 'reports'
  | 'notifications'
  | 'service-analytics'
  | 'warehouse'
  | 'tech-cards'
  | 'inventory'
  | 'tech-analytics'
  | 'tariffs';

export type PlanNavFeatures = {
  financier?: boolean;
  branding?: boolean;
};

export type NavLeaf = {
  type: 'leaf';
  key: AdminTabKey | 'branding';
  path: string;
  label: string;
  /** иконка задаётся в Sidebar */
  icon?: string;
  /** домен ENABLED_MODULES / плана; нет поля = core */
  module?: string;
  feature?: 'financier' | 'branding';
};

export type NavGroup = {
  type: 'group';
  id: string;
  label: string;
  icon?: string;
  children: NavLeaf[];
};

export type NavEntry = NavLeaf | NavGroup;

/** Канонические пути → ключ вкладки (branding — отдельная страница) */
export const PATH_TO_TAB: Record<string, AdminTabKey | 'branding'> = {
  '/dashboard': 'overview',
  '/analytics/ai-financier': 'financier',
  '/analytics/finances': 'finances',
  '/analytics/analytics': 'analytics',
  '/analytics/reports': 'reports',
  '/analytics/service-analytics': 'service-analytics',
  '/upload/records': 'appointments',
  '/upload/calendar': 'calendar',
  '/upload/boxes': 'boxes',
  '/crm/users': 'users',
  '/crm/services': 'services',
  '/discounts': 'discounts',
  '/technology/warehouse': 'warehouse',
  '/technology/tech-cards': 'tech-cards',
  '/technology/inventory': 'inventory',
  '/technology/analytics': 'tech-analytics',
  '/settings/notifications': 'notifications',
  '/settings/branding': 'branding',
  '/settings/tariffs': 'tariffs',
};

export const TAB_TO_PATH: Record<AdminTabKey | 'branding', string> = {
  overview: '/dashboard',
  financier: '/analytics/ai-financier',
  finances: '/analytics/finances',
  analytics: '/analytics/analytics',
  reports: '/analytics/reports',
  'service-analytics': '/analytics/service-analytics',
  appointments: '/upload/records',
  calendar: '/upload/calendar',
  boxes: '/upload/boxes',
  users: '/crm/users',
  services: '/crm/services',
  discounts: '/discounts',
  warehouse: '/technology/warehouse',
  'tech-cards': '/technology/tech-cards',
  inventory: '/technology/inventory',
  'tech-analytics': '/technology/analytics',
  notifications: '/settings/notifications',
  branding: '/settings/branding',
  tariffs: '/settings/tariffs',
};

/** Старые пути / алиасы → новые */
export const LEGACY_REDIRECTS: Record<string, string> = {
  '/': '/dashboard',
  '/overview': '/dashboard',
  '/branding': '/settings/branding',
  '/ai-financier': '/analytics/ai-financier',
  '/analytics': '/analytics/analytics',
  '/analytics/metrics': '/analytics/analytics',
  '/upload': '/upload/records',
  '/crm': '/crm/users',
  '/settings': '/settings/notifications',
  // legacy flat names
  '/financier': '/analytics/ai-financier',
  '/finances': '/analytics/finances',
  '/reports': '/analytics/reports',
  '/records': '/upload/records',
  '/appointments': '/upload/records',
  '/calendar': '/upload/calendar',
  '/boxes': '/upload/boxes',
  '/users': '/crm/users',
  '/services': '/crm/services',
  '/notifications': '/settings/notifications',
  '/warehouse': '/technology/warehouse',
  '/technology': '/technology/warehouse',
};

export const NAV_STORAGE_KEY = 'admin-nav-open';

export const ADMIN_NAV: NavEntry[] = [
  {
    type: 'leaf',
    key: 'overview',
    path: '/dashboard',
    label: 'Главная / Обзор',
    icon: 'home',
  },
  {
    type: 'group',
    id: 'analytics',
    label: 'Аналитика',
    icon: 'analytics',
    children: [
      { type: 'leaf', key: 'financier', path: '/analytics/ai-financier', label: 'ИИ Финансист', icon: 'financier', module: 'ai', feature: 'financier' },
      { type: 'leaf', key: 'finances', path: '/analytics/finances', label: 'Финансы', icon: 'finances', module: 'expenses' },
      { type: 'leaf', key: 'analytics', path: '/analytics/analytics', label: 'Аналитика', icon: 'metrics', module: 'analytics' },
      { type: 'leaf', key: 'reports', path: '/analytics/reports', label: 'Отчёты', icon: 'reports', module: 'analytics' },
    ],
  },
  {
    type: 'group',
    id: 'upload',
    label: 'Загрузка',
    icon: 'upload',
    children: [
      { type: 'leaf', key: 'appointments', path: '/upload/records', label: 'Записи', icon: 'records', module: 'appointments' },
      { type: 'leaf', key: 'boxes', path: '/upload/boxes', label: 'Боксы', icon: 'boxes', module: 'appointments' },
      { type: 'leaf', key: 'calendar', path: '/upload/calendar', label: 'Календарь', icon: 'calendar', module: 'appointments' },
    ],
  },
  {
    type: 'group',
    id: 'crm',
    label: 'CRM',
    icon: 'crm',
    children: [
      { type: 'leaf', key: 'users', path: '/crm/users', label: 'Пользователи', icon: 'users' },
      { type: 'leaf', key: 'services', path: '/crm/services', label: 'Услуги', icon: 'services', module: 'services' },
    ],
  },
  {
    type: 'leaf',
    key: 'discounts',
    path: '/discounts',
    label: 'Скидки',
    icon: 'discounts',
    module: 'discounts',
  },
  {
    type: 'group',
    id: 'technology',
    label: 'Технология',
    icon: 'technology',
    children: [
      { type: 'leaf', key: 'warehouse', path: '/technology/warehouse', label: 'Склад', icon: 'warehouse', module: 'materials' },
      { type: 'leaf', key: 'tech-cards', path: '/technology/tech-cards', label: 'Техкарты', icon: 'tech-cards', module: 'tech_cards' },
      { type: 'leaf', key: 'inventory', path: '/technology/inventory', label: 'Учёт', icon: 'inventory', module: 'inventory' },
      { type: 'leaf', key: 'tech-analytics', path: '/technology/analytics', label: 'Аналитика', icon: 'tech-analytics', module: 'tech_analytics' },
    ],
  },
  {
    type: 'group',
    id: 'settings',
    label: 'Настройки',
    icon: 'settings',
    children: [
      { type: 'leaf', key: 'notifications', path: '/settings/notifications', label: 'Уведомления', icon: 'notifications', module: 'notifications' },
      { type: 'leaf', key: 'branding', path: '/settings/branding', label: 'Брендинг', icon: 'branding', feature: 'branding' },
      { type: 'leaf', key: 'tariffs', path: '/settings/tariffs', label: 'Тарифы', icon: 'tariffs' },
    ],
  },
];

export function tabFromPath(pathname: string): AdminTabKey | 'branding' | null {
  if (PATH_TO_TAB[pathname]) return PATH_TO_TAB[pathname];
  if (pathname.startsWith('/technology/tech-cards/')) return 'tech-cards';
  return null;
}

export function pathFromTab(key: string): string | null {
  return (TAB_TO_PATH as Record<string, string>)[key] ?? null;
}

export function filterAdminNav(
  nav: NavEntry[],
  enabled?: string[],
  features?: PlanNavFeatures,
): NavEntry[] {
  const allowed = (leaf: NavLeaf) => {
    if (leaf.feature === 'financier' && features && features.financier === false) return false;
    if (leaf.feature === 'branding' && features && features.branding === false) return false;
    const mod = leaf.module || 'core';
    if (!enabled || enabled.length === 0) return true;
    if (mod === 'core') return true;
    return enabled.includes(mod);
  };
  const out: NavEntry[] = [];
  for (const entry of nav) {
    if (entry.type === 'leaf') {
      if (allowed(entry)) out.push(entry);
      continue;
    }
    const children = entry.children.filter(allowed);
    if (children.length) out.push({ ...entry, children });
  }
  return out;
}

export function groupIdForPath(pathname: string): string | null {
  for (const entry of ADMIN_NAV) {
    if (entry.type !== 'group') continue;
    if (entry.children.some((c) => c.path === pathname || pathname.startsWith(`${c.path}/`))) {
      return entry.id;
    }
  }
  return null;
}
