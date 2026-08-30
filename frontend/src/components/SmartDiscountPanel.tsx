/**
 * Win-back кандидаты и погодные акции — сводка на странице скидок.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card, Space, Spin, Tag, Typography, message } from 'antd';
import { CloudOutlined, ReloadOutlined, SendOutlined, UserSwitchOutlined } from '@ant-design/icons';
import { Button } from './ui';

const { Text } = Typography;

interface SmartWeather {
  city: string;
  date: string;
  t_max: number | null;
  t_min: number | null;
  precip_mm: number | null;
  kind: string | null;
  kind_label: string | null;
  available: boolean;
}

interface WeatherMatch {
  id: number;
  name: string;
  discount_percent: number;
  weather: string | null;
  will_apply: boolean;
}

interface WinBackClient {
  id: number;
  full_name: string;
  phone: string;
  days_since: number;
  last_visit: string | null;
}

interface SmartData {
  weather: SmartWeather;
  weather_matches: WeatherMatch[];
  win_back: {
    min_absent_days: number | null;
    rule_name: string | null;
    clients: WinBackClient[];
  };
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(path, {
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

export default function SmartDiscountPanel() {
  const [data, setData] = useState<SmartData | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiFetch<SmartData>('/api/discounts/smart'));
    } catch {
      setData(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const broadcast = async () => {
    setSending(true);
    try {
      const res = await apiFetch<{ sent: number; message: string }>(
        '/api/discounts/broadcast-win-back',
        { method: 'POST' },
      );
      message.success(res.message);
    } catch (e: any) {
      message.error(e.message || 'Не удалось отправить');
    }
    setSending(false);
  };

  const w = data?.weather;
  const clients = data?.win_back.clients || [];

  return (
    <Card className="card-luxury" style={{ marginBottom: 16 }}>
      <div className="toolbar-right mb-12" style={{ justifyContent: 'space-between' }}>
        <Space>
          <CloudOutlined className="text-gold" />
          <Text className="title-gold text-16">Умные акции</Text>
        </Space>
        <Button
          look="ghost"
          size="small"
          icon={<ReloadOutlined />}
          onClick={load}
          loading={loading}
          style={{ width: 'auto' }}
        >
          Обновить
        </Button>
      </div>

      <Spin spinning={loading}>
        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
          <div>
            <Text className="text-titanium text-12 d-block mb-8">Погода сегодня</Text>
            {w?.available ? (
              <>
                <Text className="text-white text-13 d-block">
                  {w.city}: {w.kind_label || 'обычная'} · {w.t_min}…{w.t_max}° · {w.precip_mm} мм
                </Text>
                {(data?.weather_matches || []).length === 0 ? (
                  <Text className="text-titanium text-12 d-block" style={{ marginTop: 6 }}>
                    Нет погодных правил. Создайте тип «Погода».
                  </Text>
                ) : (
                  <Space wrap style={{ marginTop: 8 }}>
                    {data!.weather_matches.map((r) => (
                      <Tag key={r.id} color={r.will_apply ? 'green' : 'default'}>
                        {r.name} −{r.discount_percent}% {r.will_apply ? 'сработает' : 'нет'}
                      </Tag>
                    ))}
                  </Space>
                )}
              </>
            ) : (
              <Text className="text-titanium text-12">Прогноз недоступен — погодные акции не применятся.</Text>
            )}
          </div>

          <div>
            <Text className="text-titanium text-12 d-block mb-8">
              Возврат клиентов
              {data?.win_back.min_absent_days != null
                ? ` · не были ${data.win_back.min_absent_days}+ дней`
                : ''}
            </Text>
            {data?.win_back.min_absent_days == null ? (
              <Text className="text-titanium text-12">Нет активного правила «Возврат клиентов».</Text>
            ) : clients.length === 0 ? (
              <Text className="text-titanium text-12">Сейчас никто не подходит под правило.</Text>
            ) : (
              <>
                <Space wrap style={{ marginBottom: 8 }}>
                  {clients.slice(0, 6).map((c) => (
                    <Tag key={c.id} icon={<UserSwitchOutlined />}>
                      {c.full_name} · {c.days_since} дн.
                    </Tag>
                  ))}
                  {clients.length > 6 ? (
                    <Tag>+{clients.length - 6}</Tag>
                  ) : null}
                </Space>
                <Button
                  look="gold"
                  size="small"
                  icon={<SendOutlined />}
                  loading={sending}
                  onClick={broadcast}
                  style={{ width: 'auto' }}
                >
                  Написать им
                </Button>
              </>
            )}
          </div>
        </div>
      </Spin>
    </Card>
  );
}
