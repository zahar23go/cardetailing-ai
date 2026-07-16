/* ============================================================
   Notifications API
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

/* ============================================================
   TYPES
   ============================================================ */
export interface Notification {
  id: number;
  type: string;
  channel: string;
  title: string;
  message: string;
  is_read: boolean;
  related_entity_type?: string;
  related_entity_id?: number;
  created_at?: string;
}

export interface NotificationSettings {
  telegram_enabled: boolean;
  telegram_chat_id?: string;
  sms_enabled: boolean;
  sms_phone?: string;
  notify_appointment_reminder: boolean;
  notify_status_change: boolean;
  notify_promo: boolean;
  remind_hours_before: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/* ============================================================
   API
   ============================================================ */

export async function getNotifications(
  skip = 0,
  limit = 50,
  unreadOnly = false,
): Promise<PaginatedResponse<Notification>> {
  const params = `?skip=${skip}&limit=${limit}${unreadOnly ? '&unread_only=true' : ''}`;
  return apiFetch<PaginatedResponse<Notification>>(`/api/notifications${params}`);
}

export async function getUnreadCount(): Promise<{ count: number }> {
  return apiFetch<{ count: number }>('/api/notifications/unread-count');
}

export async function markAsRead(notificationId: number): Promise<void> {
  await apiFetch(`/api/notifications/${notificationId}/read`, { method: 'PUT' });
}

export async function markAllAsRead(): Promise<{ message: string; count: number }> {
  return apiFetch<{ message: string; count: number }>('/api/notifications/read-all', { method: 'PUT' });
}

export async function getNotificationSettings(): Promise<NotificationSettings> {
  return apiFetch<NotificationSettings>('/api/notifications/settings');
}

export async function updateNotificationSettings(
  data: Partial<NotificationSettings>,
): Promise<NotificationSettings> {
  return apiFetch<NotificationSettings>('/api/notifications/settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function connectTelegram(code: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/api/telegram/connect', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export async function disconnectTelegram(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/api/telegram/disconnect', { method: 'POST' });
}
