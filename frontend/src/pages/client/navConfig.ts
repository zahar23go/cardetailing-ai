export type ClientTabKey =
  | 'home'
  | 'booking'
  | 'portfolio'
  | 'chat'
  | 'discounts'
  | 'settings';

export const CLIENT_NAV: { key: ClientTabKey; path: string; label: string; icon: string; module?: string }[] = [
  { key: 'home', path: '/client', label: 'Главная', icon: 'home' },
  { key: 'booking', path: '/client/booking', label: 'Запись', icon: 'calendar', module: 'appointments' },
  { key: 'portfolio', path: '/client/portfolio', label: 'Портфолио', icon: 'camera', module: 'photos' },
  { key: 'chat', path: '/client/chat', label: 'Детейлер', icon: 'chat', module: 'ai' },
  { key: 'discounts', path: '/client/discounts', label: 'Скидки', icon: 'gift', module: 'discounts' },
  { key: 'settings', path: '/client/settings', label: 'Профиль', icon: 'user' },
];

export function clientTabFromPath(pathname: string): ClientTabKey {
  const found = CLIENT_NAV.find((n) => n.path !== '/client' && pathname.startsWith(n.path));
  return found?.key || 'home';
}
