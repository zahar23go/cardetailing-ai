/* ============================================================
   Photo API — функции для работы с фотографиями
   ============================================================ */

const API_BASE = '';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка ${res.status}`);
  }
  return res.json();
}

/* ============================================================
   TYPES
   ============================================================ */
export interface Photo {
  id: number;
  entity_type: string;
  url: string;
  thumbnail_url?: string;
  title?: string;
  is_primary?: boolean;
  sort_order?: number;
  file_size?: number;
  mime_type?: string;
  created_at?: string;
}

/* ============================================================
   PHOTO API
   ============================================================ */

/** Загрузить фото автомобиля */
export async function uploadCarPhoto(carId: number, file: File): Promise<Photo> {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch<Photo>(`/api/upload/car/${carId}`, {
    method: 'POST',
    body: formData,
  });
}

/** Загрузить фото выполненной работы */
export async function uploadAppointmentPhoto(appointmentId: number, file: File): Promise<Photo> {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch<Photo>(`/api/upload/appointment/${appointmentId}`, {
    method: 'POST',
    body: formData,
  });
}

/** Загрузить фото в портфолио мастера */
export async function uploadPortfolioPhoto(file: File, title?: string): Promise<Photo> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  return apiFetch<Photo>('/api/upload/portfolio', {
    method: 'POST',
    body: formData,
  });
}

/** Получить список фото для сущности */
export async function getPhotos(entityType: string, entityId: number): Promise<Photo[]> {
  return apiFetch<Photo[]>(`/api/photos/${entityType}/${entityId}`);
}

/** Удалить фото */
export async function deletePhoto(photoId: number): Promise<void> {
  await apiFetch(`/api/photos/${photoId}`, { method: 'DELETE' });
}

/** Сделать фото основным */
export async function setPrimaryPhoto(photoId: number): Promise<void> {
  await apiFetch(`/api/photos/${photoId}/primary`, { method: 'PUT' });
}

/** Изменить порядок фото */
export async function reorderPhoto(photoId: number, sortOrder: number): Promise<void> {
  await apiFetch(`/api/photos/${photoId}/order`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sort_order: sortOrder }),
  });
}
