/**
 * Общий fetch и типы клиентского кабинета.
 */
export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type') && !(options?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: unknown }).detail;
    const msg = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ')
      : (typeof detail === 'string' ? detail : `Ошибка ${res.status}`);
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function formatCurrency(val: number) {
  return `${Number(val || 0).toLocaleString('ru-RU')} ₽`;
}

/** Услуги, которые ИИ назвал в ответе — для кнопки «Записаться на …». */
export function matchServicesFromText(text: string, services: Service[]): Service[] {
  const hay = (text || '').toLowerCase();
  if (!hay) return [];
  const ranked = [...services]
    .filter((s) => s.name && hay.includes(s.name.toLowerCase()))
    .sort((a, b) => b.name.length - a.name.length);
  const seen = new Set<number>();
  return ranked.filter((s) => {
    if (seen.has(s.id)) return false;
    seen.add(s.id);
    return true;
  }).slice(0, 3);
}

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'gold';

export const APPT_STATUS: Record<string, { label: string; variant: BadgeVariant }> = {
  pending: { label: 'ожидает', variant: 'warning' },
  confirmed: { label: 'подтверждена', variant: 'info' },
  in_progress: { label: 'в работе', variant: 'gold' },
  completed: { label: 'завершена', variant: 'success' },
  cancelled: { label: 'отменена', variant: 'neutral' },
};

export interface Service {
  id: number;
  name: string;
  description?: string | null;
  price: number;
  duration: number;
  category?: string | null;
}

export interface Car {
  id: number;
  make: string;
  model: string;
  year?: number | null;
  license_plate?: string | null;
  color?: string | null;
  notes?: string | null;
}

export interface Appointment {
  id: number;
  client_id: number;
  master_id: number | null;
  car_id: number;
  service_id: number;
  start_time: string;
  end_time: string;
  status: string;
  total_price: number;
  discount_applied: number;
  client_notes: string | null;
  service_name: string | null;
  master?: { id: number; full_name: string } | null;
  car?: { id: number; make: string; model: string; license_plate?: string };
  service?: { id: number; name: string; price: number };
}

export interface Master {
  id: number;
  full_name: string;
}

export interface DiscountRule {
  id: number;
  name: string;
  type: string;
  conditions?: Record<string, unknown> | null;
  discount_percent: number;
  slot_start?: string | null;
  slot_end?: string | null;
  service_id?: number | null;
  service_name?: string | null;
  client_id?: number | null;
  valid_until?: string | null;
  is_active: boolean;
}

export const DISCOUNT_TYPE_LABELS: Record<string, string> = {
  happy_hours: 'Happy Hours',
  service: 'На услугу',
  client: 'Персональная',
  segment: 'По сегменту',
  frequency: 'За частоту',
  win_back: 'Возврат',
  cashback: 'Кэшбек',
};
