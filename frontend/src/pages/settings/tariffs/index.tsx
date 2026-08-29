/**
 * Тарифы — /settings/tariffs
 * Каталог Базовый / Про / Бизнес. Назначение — только супер-админ.
 */
import React, { useCallback, useEffect, useState } from 'react';
import styled from 'styled-components';
import { message, Select, Spin, Table } from 'antd';
import { GoldButton, GhostGoldButton } from '../../../design';

const API_BASE = '';

export const PLAN_UPDATED_EVENT = 'tenant-plan-updated';

type PlanId = 'basic' | 'pro' | 'business';

type PlanCard = {
  id: PlanId;
  label: string;
  price: number;
  appointment_limit: number | null;
  blurb: string;
  features: { financier?: boolean; branding?: boolean };
};

type TenantRow = {
  id: string;
  name: string;
  subdomain: string;
  plan?: string;
};

type Me = {
  role?: string;
  tenant_id?: string;
  plan?: string;
  plan_label?: string;
  appointment_limit?: number | null;
  appointments_this_month?: number;
};

const Wrap = styled.div`
  max-width: 1080px;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin: 16px 0 28px;
`;

const Card = styled.div<{ $active?: boolean }>`
  text-align: left;
  border: 1px solid
    ${({ theme, $active }) =>
      $active ? theme.brand.colors.accent.solid : theme.brand.colors.accent.border};
  background: ${({ theme }) => theme.brand.colors.bg.elevated};
  border-radius: ${({ theme }) => theme.radii.lg};
  padding: 18px 16px;
  color: inherit;
  box-shadow: ${({ $active, theme }) =>
    $active ? `0 0 0 2px ${theme.brand.colors.accent.muted}` : 'none'};
`;

const Name = styled.div`
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 13px;
  color: ${({ theme }) => theme.brand.colors.accent.solid};
`;

const Price = styled.div`
  margin-top: 8px;
  font-size: 22px;
  font-weight: 700;
`;

const Meta = styled.p`
  margin: 8px 0 14px;
  font-size: 13px;
  line-height: 1.45;
  color: ${({ theme }) => theme.colors.text.secondary};
`;

const SectionTitle = styled.h3`
  margin: 8px 0 12px;
  font-size: 22px;
  font-family: var(--font-display, Cinzel, Georgia, serif);
  letter-spacing: 0.04em;
  color: ${({ theme }) => theme.brand.colors.accent.solid};
`;

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function formatPrice(n: number): string {
  return `${new Intl.NumberFormat('ru-RU').format(n)} ₽ / мес`;
}

function planLabel(id?: string): string {
  if (id === 'basic') return 'Базовый';
  if (id === 'pro') return 'Про';
  if (id === 'business') return 'Бизнес';
  return id || '—';
}

export default function TariffsPage() {
  const [plans, setPlans] = useState<PlanCard[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const isSuper = me?.role === 'super_admin';
  const currentPlan = me?.plan;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [plansRes, meRes] = await Promise.all([
        fetch(`${API_BASE}/api/plans`, { headers: authHeaders() }),
        fetch(`${API_BASE}/api/me`, { headers: authHeaders() }),
      ]);
      if (plansRes.ok) setPlans(await plansRes.json());
      let profile: Me | null = null;
      if (meRes.ok) {
        profile = await meRes.json();
        setMe(profile);
      }
      if (profile?.role === 'super_admin') {
        const tRes = await fetch(`${API_BASE}/api/tenants?limit=200`, { headers: authHeaders() });
        if (tRes.ok) {
          const body = await tRes.json();
          const items: TenantRow[] = body.items || body || [];
          setTenants(items);
          setSelectedId((prev) => prev || profile?.tenant_id || items[0]?.id);
        }
      }
    } catch {
      message.error('Не удалось загрузить тарифы');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const assign = async (planId: PlanId) => {
    if (!isSuper) return;
    const tenantId = selectedId;
    if (!tenantId) {
      message.warning('Выберите салон');
      return;
    }
    setBusy(planId);
    try {
      const res = await fetch(`${API_BASE}/api/tenants/${tenantId}/plan`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify({ plan: planId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        message.error(typeof data.detail === 'string' ? data.detail : 'Не удалось сменить тариф');
        return;
      }
      setTenants((rows) => rows.map((t) => (t.id === tenantId ? { ...t, plan: planId } : t)));
      message.success(`Тариф «${planLabel(planId)}» назначен`);
      window.dispatchEvent(new Event(PLAN_UPDATED_EVENT));
      if (tenantId === me?.tenant_id) {
        await load();
      }
    } catch {
      message.error('Нет связи с сервером');
    } finally {
      setBusy(null);
    }
  };

  if (loading && !plans.length) {
    return <Spin />;
  }

  const selected = tenants.find((t) => t.id === selectedId);
  const highlightId = isSuper ? selected?.plan : currentPlan;

  return (
    <Wrap>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Настройки</div>
          <h3>Тарифы</h3>
          {isSuper ? (
            <p className="text-titanium" style={{ marginTop: 4 }}>
              Назначьте план салону. Меню и доступ сразу следуют тарифу.
            </p>
          ) : (
            <p className="text-titanium" style={{ marginTop: 4 }}>
              Текущий тариф салона: <strong>{me?.plan_label || planLabel(currentPlan)}</strong>
              {me?.appointment_limit
                ? ` · записей в этом месяце: ${me.appointments_this_month ?? 0} из ${me.appointment_limit}`
                : ' · без лимита записей'}
            </p>
          )}
        </div>
      </div>

      <Grid>
        {plans.map((p) => {
          const active = p.id === highlightId;
          return (
            <Card key={p.id} $active={active}>
              <Name>{p.label}{active ? ' · текущий' : ''}</Name>
              <Price>{formatPrice(p.price)}</Price>
              <Meta>
                {p.appointment_limit
                  ? `До ${p.appointment_limit} записей в месяц. `
                  : 'Записи без лимита. '}
                {p.blurb}
              </Meta>
              {isSuper ? (
                <GoldButton
                  disabled={busy !== null || (selected?.plan === p.id)}
                  onClick={() => assign(p.id)}
                >
                  {busy === p.id ? 'Назначаю…' : selected?.plan === p.id ? 'Назначен' : 'Назначить'}
                </GoldButton>
              ) : (
                active ? <GhostGoldButton disabled>Ваш тариф</GhostGoldButton> : null
              )}
            </Card>
          );
        })}
      </Grid>

      {isSuper && (
        <>
          <SectionTitle>Салоны</SectionTitle>
          <Select
            style={{ minWidth: 280, marginBottom: 16 }}
            placeholder="Салон"
            value={selectedId}
            onChange={(v) => setSelectedId(v)}
            options={tenants.map((t) => ({
              value: t.id,
              label: `${t.name} · ${planLabel(t.plan)}`,
            }))}
          />
          <Table
            size="small"
            rowKey="id"
            pagination={false}
            dataSource={tenants}
            onRow={(row) => ({
              onClick: () => setSelectedId(row.id),
              style: { cursor: 'pointer' },
            })}
            rowClassName={(row) => (row.id === selectedId ? 'ant-table-row-selected' : '')}
            columns={[
              { title: 'Салон', dataIndex: 'name' },
              { title: 'Поддомен', dataIndex: 'subdomain' },
              {
                title: 'Тариф',
                dataIndex: 'plan',
                render: (v: string) => planLabel(v),
              },
            ]}
          />
        </>
      )}
    </Wrap>
  );
}
