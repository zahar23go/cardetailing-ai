/* ============================================================
   History API
   ============================================================ */

const API_BASE = '';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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

export interface HistoryEntry {
  id: number;
  appointment_id: number;
  change_type: string;
  field_name?: string;
  old_value?: string;
  new_value?: string;
  changed_by?: { id: number; full_name: string };
  created_at?: string;
}

export interface HistoryResponse {
  items: HistoryEntry[];
  total: number;
  skip: number;
  limit: number;
}

export async function getHistory(
  appointmentId: number,
  skip = 0,
  limit = 50,
  changeType?: string,
): Promise<HistoryResponse> {
  let path = `/api/appointments/${appointmentId}/history?skip=${skip}&limit=${limit}`;
  if (changeType) path += `&change_type=${changeType}`;
  return apiFetch<HistoryResponse>(path);
}

export async function getHistoryItem(
  appointmentId: number,
  historyId: number,
): Promise<HistoryEntry> {
  return apiFetch<HistoryEntry>(`/api/appointments/${appointmentId}/history/${historyId}`);
}
