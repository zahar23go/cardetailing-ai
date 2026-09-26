/* ============================================================
   Отзывы: импорт и ИИ-вердикт по качеству услуг
   ============================================================ */

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
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
    const msg = typeof detail === 'string' ? detail : `Ошибка ${res.status}`;
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface ReviewItem {
  id: number;
  source: string;
  external_id?: string | null;
  author?: string | null;
  rating?: number | null;
  text?: string | null;
  published_at?: string | null;
  created_at?: string | null;
}

export interface ReviewIn {
  source?: string;
  external_id?: string | null;
  author?: string | null;
  rating?: number | null;
  text?: string | null;
  published_at?: string | null;
}

export interface ReviewTheme {
  name: string;
  count: number;
  sentiment: string;
}

export interface ReviewVerdict {
  score?: number | null;
  sentiment?: string | null;
  summary?: string | null;
  strengths: string[];
  weaknesses: string[];
  themes: ReviewTheme[];
  recommendations: string[];
  reviews_count: number;
  average_rating?: number | null;
  source: string;
  created_at?: string | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export function getReviews(skip = 0, limit = 50, source?: string): Promise<Paginated<ReviewItem>> {
  const qs = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (source) qs.set('source', source);
  return apiFetch<Paginated<ReviewItem>>(`/api/reviews?${qs.toString()}`);
}

/** Контракт массового импорта (вставка вручную или внешний сборщик). */
export function importReviews(reviews: ReviewIn[]): Promise<{ imported: number; skipped: number; total: number }> {
  return apiFetch('/api/reviews/import', {
    method: 'POST',
    body: JSON.stringify({ reviews }),
  });
}

export function createReview(review: ReviewIn): Promise<ReviewItem> {
  return apiFetch<ReviewItem>('/api/reviews', {
    method: 'POST',
    body: JSON.stringify(review),
  });
}

export function deleteReview(id: number): Promise<unknown> {
  return apiFetch(`/api/reviews/${id}`, { method: 'DELETE' });
}

export function analyzeReviews(): Promise<ReviewVerdict> {
  return apiFetch<ReviewVerdict>('/api/reviews/analyze', { method: 'POST' });
}

export function getVerdict(): Promise<ReviewVerdict> {
  return apiFetch<ReviewVerdict>('/api/reviews/verdict');
}

export interface ReviewSummary {
  average_rating?: number | null;
  count: number;
  items: ReviewItem[];
}

/** Публичный рейтинг и отзывы студии (клиентский кабинет). */
export function getPublicReviews(): Promise<ReviewSummary> {
  return apiFetch<ReviewSummary>('/api/reviews/public');
}
