/**
 * Первый запуск салона — USM владельца, шаг 1.2.
 */
import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { useBrand } from '../../design';
import { GoldButton, GhostGoldButton, GoldField } from '../../design/components/BrandControls';
import { storeBrandId, type BrandTheme, type BrandThemeId } from '../../design';

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

const Shell = styled.div`
  min-height: 100vh;
  min-height: 100dvh;
  padding: 28px 16px 48px;
  font-family: ${({ theme }) => theme.fonts.primary};
  background: ${({ theme }) => theme.brand.gradients.pageAtmosphere};
  color: ${({ theme }) => theme.colors.text.primary};
`;

const Wrap = styled.div`
  max-width: 560px;
  margin: 0 auto;
`;

const Kicker = styled.div`
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.brand.colors.accent.solid};
  margin-bottom: 8px;
`;

const Title = styled.h1`
  margin: 0 0 8px;
  font-family: ${({ theme }) => theme.fonts.display};
  font-size: 22px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.brand.colors.accent.solid};
`;

const Lead = styled.p`
  margin: 0 0 20px;
  color: ${({ theme }) => theme.colors.text.secondary};
  font-size: 14px;
  line-height: 1.45;
`;

const Steps = styled.div`
  display: flex;
  gap: 6px;
  margin-bottom: 18px;
`;

const Dot = styled.span<{ $on?: boolean }>`
  flex: 1;
  height: 4px;
  border-radius: 4px;
  background: ${({ $on, theme }) =>
    $on ? theme.brand.colors.accent.solid : theme.brand.colors.accent.border};
`;

const Card = styled.div`
  border: 1px solid ${({ theme }) => theme.brand.colors.accent.border};
  background: ${({ theme }) => theme.brand.colors.bg.elevated};
  border-radius: ${({ theme }) => theme.radii.lg};
  padding: 18px;
`;

const Row = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
`;

const Preset = styled.button<{ $on?: boolean }>`
  text-align: left;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  font-family: inherit;
  color: inherit;
  border: 1px solid
    ${({ $on, theme }) =>
      $on ? theme.brand.colors.accent.solid : theme.brand.colors.accent.border};
  background: ${({ theme }) => theme.brand.colors.bg.phone};
`;

const Actions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
`;

const STEPS = [
  'Бренд',
  'Боксы',
  'Услуги',
  'Мастера',
  'Склад',
  'Старт',
] as const;

const PRESETS: { id: BrandThemeId; label: string }[] = [
  { id: 'goldMetal', label: 'Gold Metal — металл, как на входе' },
  { id: 'goldGlow', label: 'Gold Glow — свечение' },
];

type Status = {
  completed: boolean;
  needs_wizard: boolean;
  salon_name: string;
  boxes: number;
  services: number;
  masters: number;
  materials: number;
};

function Field({
  theme,
  label,
  value,
  onChange,
  placeholder,
}: {
  theme: BrandTheme;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <GoldField $theme={theme}>
      <span>{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </GoldField>
  );
}

export default function OwnerOnboardingPage() {
  const navigate = useNavigate();
  const { brand, brandId, setBrandId } = useBrand();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [salon, setSalon] = useState('');
  const [boxes, setBoxes] = useState(['Бокс №1', 'Бокс №2', 'Бокс №3']);
  const [services, setServices] = useState([
    { name: 'Мойка кузова', price: '1800', duration: '15' },
    { name: 'Полировка кузова', price: '12000', duration: '120' },
    { name: 'Керамическое покрытие 9H', price: '28000', duration: '120' },
  ]);
  const [masters, setMasters] = useState([
    { full_name: 'Сергей', phone: '79001111111' },
    { full_name: 'Максим', phone: '79001111112' },
    { full_name: 'Анна', phone: '79001111113' },
  ]);
  const [matName, setMatName] = useState('Полироль');
  const [matQty, setMatQty] = useState('800');
  const [matMin, setMatMin] = useState('200');
  const [matPrice, setMatPrice] = useState('1.8');

  useEffect(() => {
    apiFetch<Status>('/api/onboarding')
      .then((s) => {
        setStatus(s);
        if (s.salon_name) setSalon(s.salon_name);
      })
      .catch(() => undefined);
    apiFetch<{ id?: string; tenant_id?: string }>('/api/me')
      .then((me) => {
        if (me.tenant_id) localStorage.setItem('onboarding-tenant', me.tenant_id);
      })
      .catch(() => undefined);
  }, []);

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const saveBrand = async () => {
    setBusy(true);
    try {
      storeBrandId(brandId);
      const tenantId = localStorage.getItem('onboarding-tenant');
      if (tenantId && salon.trim()) {
        await apiFetch(`/api/tenants/${tenantId}`, {
          method: 'PUT',
          body: JSON.stringify({ name: salon.trim() }),
        });
      }
      next();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось сохранить бренд');
    }
    setBusy(false);
  };

  const saveBoxes = async () => {
    setBusy(true);
    try {
      const existing = await apiFetch<{ name: string }[]>('/api/boxes');
      const have = new Set((existing || []).map((b) => b.name));
      for (let i = 0; i < boxes.length; i += 1) {
        const name = boxes[i].trim();
        if (!name || have.has(name)) continue;
        await apiFetch('/api/boxes', {
          method: 'POST',
          body: JSON.stringify({ name, sort_order: i, color: '#C8A977' }),
        });
      }
      next();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось создать боксы');
    }
    setBusy(false);
  };

  const saveServices = async () => {
    setBusy(true);
    try {
      const existing = await apiFetch<{ items: { name: string }[] }>('/api/services?limit=200');
      const have = new Set((existing.items || []).map((s) => s.name));
      for (const s of services) {
        const name = s.name.trim();
        if (!name || have.has(name)) continue;
        await apiFetch('/api/services', {
          method: 'POST',
          body: JSON.stringify({
            name,
            price: Number(s.price) || 0,
            duration: Number(s.duration) || 60,
            category: name.toLowerCase().includes('полир')
              ? 'Полировка'
              : name.toLowerCase().includes('керамик')
                ? 'Защита'
                : 'Мойка',
          }),
        });
      }
      next();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось создать услуги');
    }
    setBusy(false);
  };

  const saveMasters = async () => {
    setBusy(true);
    try {
      for (const m of masters) {
        if (!m.full_name.trim() || !m.phone.trim()) continue;
        try {
          await apiFetch('/api/users', {
            method: 'POST',
            body: JSON.stringify({
              full_name: m.full_name.trim(),
              phone: m.phone.trim(),
              password: 'password123',
              role: 'master',
            }),
          });
        } catch {
          /* уже есть */
        }
      }
      next();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось добавить мастеров');
    }
    setBusy(false);
  };

  const saveStock = async () => {
    setBusy(true);
    try {
      if (matName.trim()) {
        await apiFetch('/api/materials', {
          method: 'POST',
          body: JSON.stringify({
            name: matName.trim(),
            category: 'chemistry',
            unit: 'ml',
            quantity: Number(matQty) || 0,
            min_quantity: Number(matMin) || 0,
            purchase_price: Number(matPrice) || 0,
          }),
        });
      }
      next();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось добавить материал');
    }
    setBusy(false);
  };

  const loadPack = async () => {
    setBusy(true);
    try {
      const stats = await apiFetch<{ created: number; updated: number; materials: number }>(
        '/api/onboarding/demo-pack',
        { method: 'POST' },
      );
      message.success(
        `Техкарты: +${stats.created}, обновлено ${stats.updated}. Склад: ${stats.materials} позиций`,
      );
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось загрузить пакет');
    }
    setBusy(false);
  };

  const finish = async () => {
    setBusy(true);
    try {
      await apiFetch('/api/onboarding/complete', { method: 'POST' });
      message.success('Салон готов. Открываю Command Center');
      navigate('/dashboard');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось завершить');
    }
    setBusy(false);
  };

  return (
    <Shell>
      <Wrap>
        <Kicker>Первый запуск · 15 минут</Kicker>
        <Title>Настройка салона</Title>
        <Lead>
          Логотип бренда остаётся золотым контуром спорткара. Вы задаёте название, цвета,
          боксы, услуги, мастеров и склад — дальше работа идёт из Command Center.
        </Lead>
        <Steps>
          {STEPS.map((label, i) => (
            <Dot key={label} $on={i <= step} title={label} />
          ))}
        </Steps>
        <Card>
          {step === 0 && (
            <>
              <Kicker>Шаг 1 · Бренд</Kicker>
              <Row>
                <Field
                  theme={brand}
                  label="Название салона"
                  placeholder="Детейлинг на трёх боксах"
                  value={salon}
                  onChange={setSalon}
                />
                {PRESETS.map((p) => (
                  <Preset
                    key={p.id}
                    type="button"
                    $on={brandId === p.id}
                    onClick={() => setBrandId(p.id)}
                  >
                    {p.label}
                  </Preset>
                ))}
              </Row>
              <Actions>
                <GoldButton $theme={brand} type="button" disabled={busy} onClick={saveBrand}>
                  Дальше
                </GoldButton>
                <GhostGoldButton $theme={brand} type="button" onClick={() => navigate('/dashboard')}>
                  Пропустить
                </GhostGoldButton>
              </Actions>
            </>
          )}
          {step === 1 && (
            <>
              <Kicker>Шаг 2 · Боксы</Kicker>
              <Row>
                {boxes.map((name, i) => (
                  <Field
                    key={i}
                    theme={brand}
                    label={`Бокс ${i + 1}`}
                    placeholder={`Бокс №${i + 1}`}
                    value={name}
                    onChange={(v) => {
                      const nextBoxes = [...boxes];
                      nextBoxes[i] = v;
                      setBoxes(nextBoxes);
                    }}
                  />
                ))}
              </Row>
              <Actions>
                <GhostGoldButton $theme={brand} type="button" onClick={back}>Назад</GhostGoldButton>
                <GoldButton $theme={brand} type="button" disabled={busy} onClick={saveBoxes}>
                  Сохранить боксы
                </GoldButton>
              </Actions>
            </>
          )}
          {step === 2 && (
            <>
              <Kicker>Шаг 3 · Услуги</Kicker>
              <Row>
                {services.map((s, i) => (
                  <div key={i} style={{ display: 'grid', gap: 8 }}>
                    <Field
                      theme={brand}
                      label="Услуга"
                      value={s.name}
                      onChange={(v) => {
                        const nextSvc = [...services];
                        nextSvc[i] = { ...s, name: v };
                        setServices(nextSvc);
                      }}
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                      <Field
                        theme={brand}
                        label="Цена, ₽"
                        value={s.price}
                        onChange={(v) => {
                          const nextSvc = [...services];
                          nextSvc[i] = { ...s, price: v };
                          setServices(nextSvc);
                        }}
                      />
                      <Field
                        theme={brand}
                        label="Минуты"
                        value={s.duration}
                        onChange={(v) => {
                          const nextSvc = [...services];
                          nextSvc[i] = { ...s, duration: v };
                          setServices(nextSvc);
                        }}
                      />
                    </div>
                  </div>
                ))}
              </Row>
              <Actions>
                <GhostGoldButton $theme={brand} type="button" onClick={back}>Назад</GhostGoldButton>
                <GoldButton $theme={brand} type="button" disabled={busy} onClick={saveServices}>
                  Сохранить услуги
                </GoldButton>
              </Actions>
            </>
          )}
          {step === 3 && (
            <>
              <Kicker>Шаг 4 · Мастера</Kicker>
              <Lead>Пароль для входа мастера: password123</Lead>
              <Row>
                {masters.map((m, i) => (
                  <div key={i} style={{ display: 'grid', gap: 8 }}>
                    <Field
                      theme={brand}
                      label="Имя"
                      value={m.full_name}
                      onChange={(v) => {
                        const nextM = [...masters];
                        nextM[i] = { ...m, full_name: v };
                        setMasters(nextM);
                      }}
                    />
                    <Field
                      theme={brand}
                      label="Телефон"
                      value={m.phone}
                      onChange={(v) => {
                        const nextM = [...masters];
                        nextM[i] = { ...m, phone: v };
                        setMasters(nextM);
                      }}
                    />
                  </div>
                ))}
              </Row>
              <Actions>
                <GhostGoldButton $theme={brand} type="button" onClick={back}>Назад</GhostGoldButton>
                <GoldButton $theme={brand} type="button" disabled={busy} onClick={saveMasters}>
                  Сохранить мастеров
                </GoldButton>
              </Actions>
            </>
          )}
          {step === 4 && (
            <>
              <Kicker>Шаг 5 · Склад</Kicker>
              <Row>
                <Field theme={brand} label="Материал" value={matName} onChange={setMatName} />
                <Field theme={brand} label="Остаток, мл" value={matQty} onChange={setMatQty} />
                <Field theme={brand} label="Порог заказа, мл" value={matMin} onChange={setMatMin} />
                <Field theme={brand} label="Закуп, ₽ за мл" value={matPrice} onChange={setMatPrice} />
              </Row>
              <Actions>
                <GhostGoldButton $theme={brand} type="button" onClick={back}>Назад</GhostGoldButton>
                <GhostGoldButton $theme={brand} type="button" disabled={busy} onClick={loadPack}>
                  Загрузить 6 техкарт
                </GhostGoldButton>
                <GoldButton $theme={brand} type="button" disabled={busy} onClick={saveStock}>
                  Дальше
                </GoldButton>
              </Actions>
            </>
          )}
          {step === 5 && (
            <>
              <Kicker>Шаг 6 · Готово</Kicker>
              <Lead>
                {status
                  ? `Сейчас в салоне: ${status.boxes} боксов, ${status.services} услуг, ${status.masters} мастеров.`
                  : 'Всё готово? Начать работу.'}
              </Lead>
              <Actions>
                <GhostGoldButton $theme={brand} type="button" onClick={back}>Назад</GhostGoldButton>
                <GoldButton $theme={brand} type="button" disabled={busy} onClick={finish}>
                  Начать работу
                </GoldButton>
              </Actions>
            </>
          )}
        </Card>
      </Wrap>
    </Shell>
  );
}
