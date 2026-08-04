/**
 * Иерархия админ-меню + маппинг URL ↔ ключи вкладок OwnerDashboard.
 */

export type AdminTabKey =
  | 'overview'
  | 'appointments'
  | 'calendar'
  | 'users'
  | 'services'
  | 'financier'
  | 'finances'
  | 'analytics'
  | 'discounts'
  | 'reports'
  | 'notifications'
  | 'service-analytics';

export type NavLeaf = {
  type: 'leaf';
  key: AdminTabKey | 'branding';
  path: string;
  label: string;
  /** иконка задаётся в Sidebar */
  icon?: string;
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
  '/overview': 'overview',
  '/analytics/ai-financier': 'financier',
  '/analytics/finances': 'finances',
  '/analytics/metrics': 'analytics',
  '/analytics/reports': 'reports',
  '/analytics/service-analytics': 'service-analytics',
  '/upload/records': 'appointments',
  '/upload/calendar': 'calendar',
  '/crm/users': 'users',
  '/crm/services': 'services',
  '/discounts': 'discounts',
  '/settings/notifications': 'notifications',
  '/settings/branding': 'branding',
};

export const TAB_TO_PATH: Record<AdminTabKey | 'branding', string> = {
  overview: '/overview',
  financier: '/analytics/ai-financier',
  finances: '/analytics/finances',
  analytics: '/analytics/metrics',
  reports: '/analytics/reports',
  'service-analytics': '/analytics/service-analytics',
  appointments: '/upload/records',
  calendar: '/upload/calendar',
  users: '/crm/users',
  services: '/crm/services',
  discounts: '/discounts',
  notifications: '/settings/notifications',
  branding: '/settings/branding',
};

/** Старые пути / алиасы → новые */
export const LEGACY_REDIRECTS: Record<string, string> = {
  '/': '/overview',
  '/branding': '/settings/branding',
  '/analytics': '/analytics/metrics',
  '/upload': '/upload/records',
  '/crm': '/crm/users',
  '/settings': '/settings/notifications',
  // legacy flat names (если появятся в закладках)
  '/financier': '/analytics/ai-financier',
  '/finances': '/analytics/finances',
  '/reports': '/analytics/reports',
  '/appointments': '/upload/records',
  '/calendar': '/upload/calendar',
  '/users': '/crm/users',
  '/services': '/crm/services',
  '/notifications': '/settings/notifications',
};

export const NAV_STORAGE_KEY = 'admin-nav-open';

export const ADMIN_NAV: NavEntry[] = [
  {
    type: 'leaf',
    key: 'overview',
    path: '/overview',
    label: 'Главная / Обзор',
    icon: 'home',
  },
  {
    type: 'group',
    id: 'analytics',
    label: 'Аналитика',
    icon: 'analytics',
    children: [
      { type: 'leaf', key: 'financier', path: '/analytics/ai-financier', label: 'ИИ Финансист', icon: 'financier' },
      { type: 'leaf', key: 'finances', path: '/analytics/finances', label: 'Финансы', icon: 'finances' },
      { type: 'leaf', key: 'analytics', path: '/analytics/metrics', label: 'Аналитика', icon: 'metrics' },
      { type: 'leaf', key: 'reports', path: '/analytics/reports', label: 'Отчёты', icon: 'reports' },
      { type: 'leaf', key: 'service-analytics', path: '/analytics/service-analytics', label: 'Аналитика услуг', icon: 'metrics' },
    ],
  },
  {
    type: 'group',
    id: 'upload',
    label: 'Загрузка',
    icon: 'upload',
    children: [
      { type: 'leaf', key: 'appointments', path: '/upload/records', label: 'Записи', icon: 'records' },
      { type: 'leaf', key: 'calendar', path: '/upload/calendar', label: 'Календарь', icon: 'calendar' },
    ],
  },
  {
    type: 'group',
    id: 'crm',
    label: 'CRM',
    icon: 'crm',
    children: [
      { type: 'leaf', key: 'users', path: '/crm/users', label: 'Пользователи', icon: 'users' },
      { type: 'leaf', key: 'services', path: '/crm/services', label: 'Услуги', icon: 'services' },
    ],
  },
  {
    type: 'leaf',
    key: 'discounts',
    path: '/discounts',
    label: 'Скидки',
    icon: 'discounts',
  },
  {
    type: 'group',
    id: 'settings',
    label: 'Настройки',
    icon: 'settings',
    children: [
      { type: 'leaf', key: 'notifications', path: '/settings/notifications', label: 'Уведомления', icon: 'notifications' },
      { type: 'leaf', key: 'branding', path: '/settings/branding', label: 'Брендинг', icon: 'branding' },
    ],
  },
];

export function tabFromPath(pathname: string): AdminTabKey | 'branding' | null {
  return PATH_TO_TAB[pathname] ?? null;
}

export function pathFromTab(key: string): string | null {
  return (TAB_TO_PATH as Record<string, string>)[key] ?? null;
}

export function groupIdForPath(pathname: string): string | null {
  for (const entry of ADMIN_NAV) {
    if (entry.type === 'group' && entry.children.some((c) => c.path === pathname)) {
      return entry.id;
    }
  }
  return null;
}
