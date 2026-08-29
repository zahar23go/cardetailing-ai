export type PwaBrand = {
  name: string;
  short_name: string;
  icon: string;
  theme_color: string;
  background_color: string;
  white_label: boolean;
};

export const DEFAULT_PWA: PwaBrand = {
  name: 'CAR DETAILING AI',
  short_name: 'Detailing AI',
  icon: '/icons/icon-192x192.png',
  theme_color: '#C8A977',
  background_color: '#0B0D10',
  white_label: false,
};

export function hidePwaSplash() {
  const el = document.getElementById('pwa-splash');
  if (!el) return;
  el.classList.add('is-hidden');
  window.setTimeout(() => el.remove(), 400);
}

export function applyPwaBrand(pwa?: PwaBrand | null, tenantId?: string) {
  const brand = pwa || DEFAULT_PWA;
  document.title = brand.name;
  const theme = document.querySelector('meta[name="theme-color"]');
  if (theme) theme.setAttribute('content', brand.theme_color || DEFAULT_PWA.theme_color);
  const appleTitle = document.querySelector('meta[name="apple-mobile-web-app-title"]');
  if (appleTitle) appleTitle.setAttribute('content', brand.short_name || brand.name);
  const appleIcon = document.querySelector('link[rel="apple-touch-icon"]');
  if (appleIcon) appleIcon.setAttribute('href', brand.icon || DEFAULT_PWA.icon);
  const fav = document.querySelector('link[rel="icon"]');
  if (fav) fav.setAttribute('href', brand.icon || DEFAULT_PWA.icon);
  const manifest = document.querySelector('link[rel="manifest"]');
  if (manifest) {
    const href =
      brand.white_label && tenantId
        ? `/api/pwa/manifest?tenant=${encodeURIComponent(tenantId)}`
        : '/manifest.json';
    manifest.setAttribute('href', href);
  }
}

export function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => undefined);
  });
}

export const APPT_OFFLINE_KEY = 'pwa-offline-appointments';
