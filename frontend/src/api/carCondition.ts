/* ============================================================
   Состояние авто: тип краски, сколы, требования (для мастера)
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

export interface ConditionOption {
  id: string;
  label: string;
}

export interface ConditionCatalog {
  paint_types: ConditionOption[];
  glass_defects: ConditionOption[];
  care_requirements: ConditionOption[];
}

export interface CarCondition {
  paint_type: string | null;
  glass_defects: string[];
  care_requirements: string[];
  notes: string | null;
}

export function getConditionCatalog(): Promise<ConditionCatalog> {
  return apiFetch<ConditionCatalog>('/api/cars/condition-catalog');
}

/** Постоянный профиль авто. */
export function saveCarCondition(carId: number, data: CarCondition): Promise<unknown> {
  return apiFetch(`/api/cars/${carId}/condition`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/** Снимок состояния на конкретный визит. */
export function saveAppointmentCarCondition(
  appointmentId: number,
  data: CarCondition,
): Promise<unknown> {
  return apiFetch(`/api/appointments/${appointmentId}/car-condition`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}
