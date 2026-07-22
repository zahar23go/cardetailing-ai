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
  description?: string;
  service_id?: number;
  service_name?: string;
  uploaded_by_id?: number;
  uploader_name?: string;
  is_primary?: boolean;
  sort_order?: number;
  file_size?: number;
  mime_type?: string;
  created_at?: string;
}

export interface PortfolioService {
  service_id: number;
  service_name: string;
  photo_count: number;
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

/** Загрузить фото в портфолио мастера (с привязкой к услуге) */
export async function uploadPortfolioPhoto(
  file: File,
  title?: string,
  serviceId?: number,
  description?: string,
): Promise<Photo> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  if (serviceId !== undefined) formData.append('service_id', String(serviceId));
  if (description) formData.append('description', description);
  return apiFetch<Photo>('/api/upload/portfolio', {
    method: 'POST',
    body: formData,
  });
}

/** Получить список фото для сущности */
export async function getPhotos(entityType: string, entityId: number): Promise<Photo[]> {
  return apiFetch<Photo[]>(`/api/photos/${entityType}/${entityId}`);
}

/** Получить все портфолио-фото салона (с фильтром по услуге) */
export async function getAllPortfolio(serviceId?: number): Promise<Photo[]> {
  let path = '/api/portfolio';
  if (serviceId !== undefined) path += `?service_id=${serviceId}`;
  return apiFetch<Photo[]>(path);
}

/** Получить список услуг, по которым есть фото в портфолио */
export async function getPortfolioServices(): Promise<PortfolioService[]> {
  return apiFetch<PortfolioService[]>('/api/portfolio/services');
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
