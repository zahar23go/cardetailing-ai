/**
 * Соответствие экранов доменам бэкенда (ENABLED_MODULES).
 * core всегда включён.
 */

export const ALL_MODULES = [
  'core',
  'services',
  'appointments',
  'cars',
  'photos',
  'materials',
  'tech_cards',
  'inventory',
  'tech_analytics',
  'expenses',
  'analytics',
  'ai',
  'reviews',
  'discounts',
  'notifications',
  'payments',
] as const;

export type AppModuleName = (typeof ALL_MODULES)[number];

const PATH_PREFIX_MODULE: { prefix: string; module: AppModuleName }[] = [
  { prefix: '/analytics/ai-financier', module: 'ai' },
  { prefix: '/analytics/finances', module: 'expenses' },
  { prefix: '/analytics/analytics', module: 'analytics' },
  { prefix: '/analytics/reports', module: 'analytics' },
  { prefix: '/analytics/service-analytics', module: 'analytics' },
  { prefix: '/reviews', module: 'reviews' },
  { prefix: '/upload/records', module: 'appointments' },
  { prefix: '/upload/boxes', module: 'appointments' },
  { prefix: '/upload/calendar', module: 'appointments' },
  { prefix: '/crm/services', module: 'services' },
  { prefix: '/crm/users', module: 'core' },
  { prefix: '/discounts', module: 'discounts' },
  { prefix: '/technology/warehouse', module: 'materials' },
  { prefix: '/technology/tech-cards', module: 'tech_cards' },
  { prefix: '/technology/inventory', module: 'inventory' },
  { prefix: '/technology/analytics', module: 'tech_analytics' },
  { prefix: '/settings/notifications', module: 'notifications' },
  { prefix: '/settings/branding', module: 'core' },
  { prefix: '/settings/tariffs', module: 'core' },
  { prefix: '/dashboard', module: 'core' },
  { prefix: '/client/booking', module: 'appointments' },
  { prefix: '/client/portfolio', module: 'photos' },
  { prefix: '/client/reviews', module: 'reviews' },
  { prefix: '/client/chat', module: 'ai' },
  { prefix: '/client/discounts', module: 'discounts' },
  { prefix: '/client/settings', module: 'core' },
  { prefix: '/client', module: 'core' },
  { prefix: '/master/portfolio', module: 'photos' },
];

export function moduleForPath(pathname: string): AppModuleName {
  const found = PATH_PREFIX_MODULE.find(
    (row) => pathname === row.prefix || pathname.startsWith(`${row.prefix}/`),
  );
  return found?.module ?? 'core';
}

export function isModuleEnabled(enabled: string[] | undefined, name: AppModuleName): boolean {
  if (!enabled || enabled.length === 0) return true;
  if (name === 'core') return true;
  return enabled.includes(name);
}

export function isPathEnabled(
  enabled: string[] | undefined,
  pathname: string,
  features?: { financier?: boolean; branding?: boolean },
): boolean {
  if (pathname.startsWith('/analytics/ai-financier')) {
    if (features && features.financier === false) return false;
  }
  if (pathname.startsWith('/settings/branding') || pathname === '/branding') {
    if (features && features.branding === false) return false;
  }
  return isModuleEnabled(enabled, moduleForPath(pathname));
}
