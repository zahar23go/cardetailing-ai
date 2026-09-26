/* ============================================================
   CarCondition — состояние авто для мастера: тип краски,
   сколы/трещины, особые требования + комментарий.
   Просмотр всегда; редактирование — если задан onSave.
   ============================================================ */

import React, { useEffect, useState } from 'react';
import { Checkbox, Select, Typography, message } from 'antd';
import { AlertOutlined, WarningOutlined } from '@ant-design/icons';
import { Button, Modal, Input } from './ui';
import Badge from './Badge';
import {
  getConditionCatalog,
  type CarCondition as CarConditionData,
  type ConditionCatalog,
  type ConditionOption,
} from '../api/carCondition';

const { Text } = Typography;
const { TextArea } = Input;

export type CarConditionValue = {
  paint_type?: string | null;
  glass_defects?: string[] | null;
  care_requirements?: string[] | null;
  /** Профиль Car отдаёт `condition_notes`; снимок визита — `notes`. */
  notes?: string | null;
  condition_notes?: string | null;
};

interface CarConditionProps {
  value?: CarConditionValue | null;
  editable?: boolean;
  onSave?: (data: CarConditionData) => Promise<void>;
  title?: string;
  emptyHint?: string;
}

const EMPTY: CarConditionData = {
  paint_type: null,
  glass_defects: [],
  care_requirements: [],
  notes: null,
};

export default function CarCondition({
  value,
  editable = false,
  onSave,
  title = 'Состояние авто',
  emptyHint,
}: CarConditionProps) {
  const [catalog, setCatalog] = useState<ConditionCatalog | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<CarConditionData>(EMPTY);

  useEffect(() => {
    let alive = true;
    getConditionCatalog()
      .then((c) => { if (alive) setCatalog(c); })
      .catch(() => undefined);
    return () => { alive = false; };
  }, []);

  const labelOf = (list: ConditionOption[] | undefined, id: string) =>
    list?.find((o) => o.id === id)?.label || id;

  const paintLabel = value?.paint_type ? labelOf(catalog?.paint_types, value.paint_type) : null;
  const glass = value?.glass_defects || [];
  const care = value?.care_requirements || [];
  const notes = value?.condition_notes ?? value?.notes ?? '';
  const empty = !paintLabel && glass.length === 0 && care.length === 0 && !notes;

  const openModal = () => {
    setDraft({
      paint_type: value?.paint_type ?? null,
      glass_defects: [...(value?.glass_defects || [])],
      care_requirements: [...(value?.care_requirements || [])],
      notes: value?.condition_notes ?? value?.notes ?? '',
    });
    setOpen(true);
  };

  const save = async () => {
    if (!onSave) return;
    setSaving(true);
    try {
      await onSave(draft);
      setOpen(false);
      message.success('Состояние авто сохранено');
    } catch (e) {
      message.error((e as Error).message || 'Не удалось сохранить');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className={[
        'car-condition',
        empty && editable ? 'car-condition--empty' : null,
        !editable ? 'car-condition--readonly' : null,
      ].filter(Boolean).join(' ')}
    >
      <div className="car-condition-head">
        <span className="car-condition-title">
          <AlertOutlined /> {title}
        </span>
        {editable && onSave && (
          <Button
            size="small"
            type={empty ? 'primary' : 'default'}
            onClick={openModal}
          >
            {empty ? 'Заполнить' : 'Изменить'}
          </Button>
        )}
      </div>

      {empty ? (
        <span className={`car-condition-empty${editable ? '' : ' car-condition-empty--muted'}`}>
          {editable && <WarningOutlined />}{' '}
          {emptyHint
            || (editable
              ? 'Не заполнено — укажите тип краски, сколы и требования'
              : 'Не заполнено')}
        </span>
      ) : (
        <div className="car-condition-chips">
          {paintLabel && <Badge variant="gold" size="sm">{paintLabel}</Badge>}
          {glass.map((id) => (
            <Badge key={id} variant="danger" size="sm">{labelOf(catalog?.glass_defects, id)}</Badge>
          ))}
          {care.map((id) => (
            <Badge key={id} variant="info" size="sm">{labelOf(catalog?.care_requirements, id)}</Badge>
          ))}
        </div>
      )}

      {notes && <Text className="car-condition-notes">{notes}</Text>}

      {editable && onSave && (
        <Modal
          title={title}
          open={open}
          onCancel={() => setOpen(false)}
          onOk={save}
          confirmLoading={saving}
          okText="Сохранить"
          cancelText="Отмена"
        >
          <div className="car-condition-field">
            <Text className="text-titanium">Тип краски</Text>
            <Select
              allowClear
              placeholder="Не выбрано"
              value={draft.paint_type ?? undefined}
              onChange={(v) => setDraft((d) => ({ ...d, paint_type: v ?? null }))}
              options={(catalog?.paint_types || []).map((o) => ({ value: o.id, label: o.label }))}
            />
          </div>

          <div className="car-condition-field">
            <Text className="text-titanium">Стекло (лобовое)</Text>
            <Checkbox.Group
              value={draft.glass_defects}
              onChange={(v) => setDraft((d) => ({ ...d, glass_defects: v as string[] }))}
              options={(catalog?.glass_defects || []).map((o) => ({ value: o.id, label: o.label }))}
            />
          </div>

          <div className="car-condition-field">
            <Text className="text-titanium">Особые требования</Text>
            <Checkbox.Group
              value={draft.care_requirements}
              onChange={(v) => setDraft((d) => ({ ...d, care_requirements: v as string[] }))}
              options={(catalog?.care_requirements || []).map((o) => ({ value: o.id, label: o.label }))}
            />
          </div>

          <div className="car-condition-field">
            <Text className="text-titanium">Комментарий</Text>
            <TextArea
              rows={3}
              value={draft.notes ?? ''}
              onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
              placeholder="Например: скол на лобовом слева, нужна бескислотная мойка"
            />
          </div>
        </Modal>
      )}
    </div>
  );
}
