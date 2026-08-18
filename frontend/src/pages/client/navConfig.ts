export type ClientTabKey =
  | 'home'
  | 'booking'
  | 'portfolio'
  | 'chat'
  | 'discounts'
  | 'settings';

export const CLIENT_NAV: { key: ClientTabKey; path: string; label: string; icon: string }[] = [
  { key: 'home', path: '/client', label: 'Главная', icon: 'home' },
  { key: 'booking', path: '/client/booking', label: 'Запись', icon: 'calendar' },
  { key: 'portfolio', path: '/client/portfolio', label: 'Портфолио', icon: 'camera' },
  { key: 'chat', path: '/client/chat', label: 'Чат с ИИ', icon: 'chat' },
  { key: 'discounts', path: '/client/discounts', label: 'Скидки', icon: 'gift' },
  { key: 'settings', path: '/client/settings', label: 'Профиль', icon: 'user' },
];

export function clientTabFromPath(pathname: string): ClientTabKey {
  const found = CLIENT_NAV.find((n) => n.path !== '/client' && pathname.startsWith(n.path));
  return found?.key || 'home';
}
