/**
 * Закрытие заезда: чек-лист техкарты, факт vs норма, списание склада.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Checkbox, Spin, Typography, message } from 'antd';
import { Button, Input, Modal } from './ui';

const { Text } = Typography;

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

export interface CloseStep {
  block_id: number | null;
  sort_order: number;
  title: string;
  done: boolean;
  materials?: { material_id: number; quantity: number }[];
}

export interface CloseMaterial {
  material_id: number;
  name: string;
  unit: string;
  norm_qty: number;
  actual_qty: number;
  stock?: number;
  unit_cost: number;
  applied_qty?: number;
  line_cost?: number;
  shortage?: number;
  delta_percent?: number;
}

export interface ClosePreview {
  appointment_id: number;
  service_id: number;
  service_name: string;
  box_id?: number | null;
  box_name?: string | null;
  price: number;
  discount: number;
  catalog_material_cost: number;
  estimated_material_cost: number;
  estimated_gross_profit: number;
  material_cost?: number;
  gross_profit?: number;
  commission_percent?: number;
  commission_amount?: number;
  has_tech_card: boolean;
  already_closed: boolean;
  steps: CloseStep[];
  materials: CloseMaterial[];
}

interface CloseVisitModalProps {
  open: boolean;
  appointmentId: number | null;
  role: 'admin' | 'master';
  onCancel: () => void;
  onClosed: () => void;
}

function previewPath(role: 'admin' | 'master', id: number) {
  return role === 'master'
    ? `/api/masters/me/appointments/${id}/close-preview`
    : `/api/appointments/${id}/close-preview`;
}

function closePath(role: 'admin' | 'master', id: number) {
  return role === 'master'
    ? `/api/masters/me/appointments/${id}/close`
    : `/api/appointments/${id}/close`;
}

function money(v: number) {
  return `${Number(v || 0).toLocaleString('ru-RU')} ₽`;
}

export default function CloseVisitModal({
  open,
  appointmentId,
  role,
  onCancel,
  onClosed,
}: CloseVisitModalProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState<ClosePreview | null>(null);
  const [steps, setSteps] = useState<CloseStep[]>([]);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [edited, setEdited] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (!open || !appointmentId) {
      setPreview(null);
      setSteps([]);
      setQty({});
      setEdited({});
      return;
    }
    let cancelled = false;
    setLoading(true);
    apiFetch<ClosePreview>(previewPath(role, appointmentId))
      .then((data) => {
        if (cancelled) return;
        setPreview(data);
        setSteps((data.steps || []).map((s) => ({ ...s, done: s.done !== false })));
        const next: Record<number, number> = {};
        (data.materials || []).forEach((m) => {
          next[m.material_id] = Number(m.actual_qty ?? m.norm_qty ?? 0);
        });
        setQty(next);
        setEdited({});
      })
      .catch((e: Error) => {
        if (!cancelled) message.error(e.message || 'Не удалось загрузить чек');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, appointmentId, role]);

  const materials = useMemo(() => {
    if (!preview) return [];
    const hasBlocks = steps.some((s) => s.block_id != null);
    return (preview.materials || []).map((m) => {
      let norm = Number(m.norm_qty || 0);
      if (hasBlocks) {
        norm = 0;
        steps.forEach((s) => {
          if (!s.done) return;
          (s.materials || []).forEach((sm) => {
            if (sm.material_id === m.material_id) norm += Number(sm.quantity || 0);
          });
        });
      }
      const actual = edited[m.material_id] ? Number(qty[m.material_id] ?? norm) : norm;
      const stock = Number(m.stock ?? 0);
      const unitCost = Number(m.unit_cost || 0);
      return {
        ...m,
        norm_qty: Math.round(norm * 1000) / 1000,
        actual_qty: actual,
        shortage: Math.max(0, actual - stock),
        line_est: Math.round(Math.min(actual, stock) * unitCost * 100) / 100,
      };
    });
  }, [preview, steps, qty, edited]);

  const estimatedCost = useMemo(() => {
    if (!preview) return 0;
    if (!materials.length) return Number(preview.catalog_material_cost || 0);
    return Math.round(materials.reduce((sum, m) => sum + m.line_est, 0) * 100) / 100;
  }, [preview, materials]);

  const toggleStep = (blockId: number | null, done: boolean) => {
    setSteps((prev) => prev.map((s) => (s.block_id === blockId ? { ...s, done } : s)));
  };

  const handleClose = async () => {
    if (!appointmentId || !preview) return;
    setSaving(true);
    try {
      await apiFetch(closePath(role, appointmentId), {
        method: 'POST',
        body: JSON.stringify({
          steps: steps.map((s) => ({ block_id: s.block_id, done: s.done })),
          materials: materials.map((m) => ({
            material_id: m.material_id,
            actual_qty: Number(m.actual_qty || 0),
          })),
        }),
      });
      message.success('Заезд закрыт, чек зафиксирован');
      onClosed();
    } catch (e: any) {
      message.error(e.message || 'Не удалось закрыть заезд');
    }
    setSaving(false);
  };

  const already = Boolean(preview?.already_closed);
  const shortageCount = materials.filter((m) => m.shortage > 0).length;

  return (
    <Modal
      open={open}
      onCancel={onCancel}
      title={already ? 'Чек закрытия' : 'Закрытие заезда'}
      width={640}
      footer={
        already
          ? [
              <Button key="ok" look="gold" onClick={onCancel}>
                Закрыто
              </Button>,
            ]
          : [
              <Button key="cancel" look="ghost" onClick={onCancel}>
                Отмена
              </Button>,
              <Button key="ok" look="gold" loading={saving} onClick={handleClose}>
                Закрыть заезд
              </Button>,
            ]
      }
    >
      <Spin spinning={loading}>
        {preview && (
          <div>
            <Text className="text-white text-14 d-block">
              {preview.service_name}
              {preview.box_name ? ` · ${preview.box_name}` : ''}
            </Text>
            <Text className="text-titanium text-12 d-block mb-8">
              Цена {money(preview.price)}
              {preview.discount ? ` · скидка ${money(preview.discount)}` : ''}
              {!preview.has_tech_card ? ' · техкарта не привязана, себестоимость из каталога' : ''}
            </Text>

            {steps.length > 0 && (
              <div className="mb-12">
                <Text className="title-gold text-13 d-block mb-8">Шаги техкарты</Text>
                {steps.map((s) => (
                  <div key={s.block_id ?? s.sort_order} style={{ marginBottom: 6 }}>
                    <Checkbox
                      checked={s.done}
                      disabled={already}
                      onChange={(e) => toggleStep(s.block_id, e.target.checked)}
                    >
                      <Text className="text-white text-13">{s.title}</Text>
                    </Checkbox>
                  </div>
                ))}
              </div>
            )}

            {materials.length > 0 && (
              <div className="mb-12">
                <Text className="title-gold text-13 d-block mb-8">Материалы: норма / факт</Text>
                {materials.map((m) => (
                  <div
                    key={m.material_id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 88px 88px',
                      gap: 8,
                      alignItems: 'center',
                      marginBottom: 8,
                    }}
                  >
                    <div>
                      <Text className="text-white text-13 d-block">{m.name}</Text>
                      <Text className="text-titanium text-12">
                        Норма {m.norm_qty} {m.unit}
                        {m.stock != null ? ` · склад ${m.stock}` : ''}
                        {m.shortage > 0 ? ` · нехватка ${m.shortage}` : ''}
                      </Text>
                    </div>
                    <Text className="text-titanium text-12">норма {m.norm_qty}</Text>
                    <Input
                      type="number"
                      min={0}
                      step="0.001"
                      disabled={already}
                      value={m.actual_qty}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        setQty((prev) => ({ ...prev, [m.material_id]: Number.isFinite(v) ? v : 0 }));
                        setEdited((prev) => ({ ...prev, [m.material_id]: true }));
                      }}
                    />
                  </div>
                ))}
              </div>
            )}

            {shortageCount > 0 && !already && (
              <Text className="text-13 d-block mb-8" style={{ color: '#C8A977' }}>
                На складе не хватает {shortageCount} поз. Заезд всё равно закроется, спишется фактический остаток.
              </Text>
            )}

            <Text className="text-gold-bold text-14 d-block">
              Химия {money(already ? Number(preview.material_cost ?? estimatedCost) : estimatedCost)}
              {' · '}
              Маржа {money((preview.price || 0) - (already ? Number(preview.material_cost ?? estimatedCost) : estimatedCost))}
            </Text>
            {(preview.commission_percent || preview.commission_amount) ? (
              <Text className="text-13 d-block" style={{ marginTop: 4 }}>
                Комиссия мастера {preview.commission_percent || 0}% · {money(preview.commission_amount || 0)}
              </Text>
            ) : null}
            <Text className="text-titanium text-12 d-block">
              Каталог услуги: {money(preview.catalog_material_cost)}
            </Text>
          </div>
        )}
      </Spin>
    </Modal>
  );
}
