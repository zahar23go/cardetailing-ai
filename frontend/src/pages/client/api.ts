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

function normalizeText(value: string) {
  return (value || '')
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/[^a-zа-я0-9]+/gi, ' ')
    .trim();
}

const SERVICE_HINTS: { re: RegExp; needles: string[] }[] = [
  { re: /полир|керамик|покрыт|лак/, needles: ['полир', 'керамик'] },
  { re: /мойк|двухфаз|экспресс|wash/, needles: ['мойк'] },
  { re: /химчист|салон|interior|кожа/, needles: ['химчист', 'салон'] },
];

/** Услуги, которые ИИ назвал в ответе — для кнопки «Записаться на …». */
export function matchServicesFromText(text: string, services: Service[]): Service[] {
  const hay = normalizeText(text);
  if (!hay || !services.length) return [];
  const seen = new Set<number>();
  const add = (list: Service[], item: Service) => {
    if (seen.has(item.id)) return;
    seen.add(item.id);
    list.push(item);
  };

  const ranked: Service[] = [];
  const sorted = [...services]
    .filter((s) => s.name)
    .sort((a, b) => b.name.length - a.name.length);

  for (const s of sorted) {
    const name = normalizeText(s.name);
    if (name && hay.includes(name)) add(ranked, s);
  }

  for (const s of sorted) {
    const tokens = normalizeText(s.name).split(' ').filter((t) => t.length >= 4);
    if (tokens.some((t) => hay.includes(t))) add(ranked, s);
  }

  for (const s of sorted) {
    const cat = normalizeText(s.category || '');
    if (cat && hay.includes(cat)) add(ranked, s);
  }

  for (const hint of SERVICE_HINTS) {
    if (!hint.re.test(hay)) continue;
    for (const s of sorted) {
      const blob = `${normalizeText(s.name)} ${normalizeText(s.category || '')}`;
      if (hint.needles.some((n) => blob.includes(n))) add(ranked, s);
    }
  }

  return ranked.slice(0, 3);
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
  master_brief?: string | null;
  box_id?: number | null;
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

export function tzOffsetMinutes() {
  return -new Date().getTimezoneOffset();
}

export interface DetailerFinding {
  tag: string;
  area: string;
  title: string;
  detail: string;
}

export interface DetailerOffer {
  service_id: number;
  name: string;
  price: number;
  duration: number;
  category?: string | null;
  reason?: string | null;
}

export interface DetailerSlot {
  start_time?: string | null;
  end_time?: string | null;
  label?: string | null;
  time?: string | null;
  date?: string | null;
  box_id?: number | null;
  box_name?: string | null;
  free_boxes?: number;
  duration?: number | null;
  available?: boolean | null;
}

export interface DetailerInspect {
  id: number;
  tags: string[];
  findings: DetailerFinding[];
  primary: DetailerOffer | null;
  upsells: DetailerOffer[];
  slots: DetailerSlot[];
  master_brief: string;
  photo_count: number;
}

export const DETAILER_TAGS: { id: string; label: string }[] = [
  { id: 'chips', label: 'Сколы / риски' },
  { id: 'dull', label: 'Тусклый лак' },
  { id: 'lights', label: 'Мутные фары' },
  { id: 'interior', label: 'Салон / кожа' },
  { id: 'bitumen', label: 'Битум / металлик' },
  { id: 'wash', label: 'Грязный кузов' },
];
