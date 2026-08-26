export interface ServiceOption {
  id: number;
  name: string;
  price: number;
}

export interface MaterialOption {
  id: number;
  name: string;
  unit: string;
  sku?: string | null;
  purchase_price: number;
  quantity: number;
}

export interface TechCardItem {
  id?: number;
  material_id: number;
  material_name?: string;
  material_unit?: string;
  purchase_price?: number;
  stock_quantity?: number;
  quantity: number;
  line_cost?: number;
  notes?: string | null;
  is_low_stock?: boolean;
}

export interface TechCardBlock {
  id: number;
  sort_order: number;
  title: string;
  description?: string | null;
  duration_minutes: number;
  photo_url?: string | null;
  items: TechCardItem[];
  items_count: number;
  estimated_cost: number;
}

export interface TechCard {
  id: number;
  service_id: number;
  service_name: string;
  service_price: number;
  name?: string | null;
  notes?: string | null;
  is_active: boolean;
  items: TechCardItem[];
  items_count: number;
  estimated_cost: number;
  blocks: TechCardBlock[];
  blocks_count: number;
  total_duration_minutes: number;
}

export type DraftItem = {
  key: string;
  material_id?: number;
  quantity: number;
};

export type DraftBlock = {
  key: string;
  title: string;
  description: string;
  duration_minutes: number;
  photo_url?: string | null;
  items: DraftItem[];
};

export const API_BASE = '';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type') && !(options?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
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

export function formatDuration(minutes: number) {
  const m = Math.max(0, Number(minutes) || 0);
  if (m < 60) return `${m} мин`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest ? `${h} ч ${rest} мин` : `${h} ч`;
}

const UNIT_LABELS: Record<string, string> = {
  pcs: 'шт',
  ml: 'мл',
  l: 'л',
  g: 'г',
  kg: 'кг',
  m: 'м',
  pack: 'упак.',
};

export function formatUnit(unit?: string | null) {
  if (!unit) return '';
  return UNIT_LABELS[unit] || unit;
}

export function newDraftItem(): DraftItem {
  return { key: `${Date.now()}-${Math.random()}`, quantity: 1 };
}

export function newDraftBlock(title = ''): DraftBlock {
  return {
    key: `${Date.now()}-${Math.random()}`,
    title,
    description: '',
    duration_minutes: 1,
    photo_url: null,
    items: [newDraftItem()],
  };
}

export function cardToDraftBlocks(card: TechCard): DraftBlock[] {
  const source = card.blocks?.length
    ? card.blocks
    : [{
        id: 0,
        sort_order: 0,
        title: 'Материалы',
        description: card.notes || '',
        duration_minutes: 0,
        photo_url: null,
        items: card.items || [],
        items_count: card.items?.length || 0,
        estimated_cost: card.estimated_cost,
      }];
  return source.map((b, idx) => ({
    key: `b-${b.id || idx}-${idx}`,
    title: b.title,
    description: b.description || '',
    duration_minutes: Number(b.duration_minutes) || 0,
    photo_url: b.photo_url || null,
    items: b.items?.length
      ? b.items.map((i) => ({
          key: `i-${i.id || i.material_id}-${idx}`,
          material_id: i.material_id,
          quantity: Number(i.quantity) || 1,
        }))
      : [newDraftItem()],
  }));
}
