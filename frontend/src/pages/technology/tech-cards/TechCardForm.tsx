/**
 * Форма создания / редактирования техкарты с блоками-шагами.
 */
import React, { useMemo, useState } from 'react';
import {
  Col, Input, InputNumber, Modal, Row, Select, Space, Typography, Upload, message,
} from 'antd';
import {
  ArrowDownOutlined, ArrowUpOutlined, DeleteOutlined, PictureOutlined, PlusOutlined,
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { Button } from '../../../components/ui';
import Card from '../../../components/Card';
import { DurationMark } from './Marks';
import StepPhoto from './StepPhoto';
import {
  DraftBlock,
  MaterialOption,
  TechCard,
  apiFetch,
  formatCurrency,
  formatUnit,
  newDraftBlock,
  newDraftItem,
} from './types';

const { Text } = Typography;
const { TextArea } = Input;

type Props = {
  open: boolean;
  editing: TechCard | null;
  materials: MaterialOption[];
  serviceOptions: { value: number; label: string }[];
  draftBlocks: DraftBlock[];
  serviceId?: number;
  cardName: string;
  cardNotes: string;
  saving: boolean;
  onClose: () => void;
  onServiceId: (v: number) => void;
  onCardName: (v: string) => void;
  onCardNotes: (v: string) => void;
  onBlocks: (next: DraftBlock[] | ((prev: DraftBlock[]) => DraftBlock[])) => void;
  onSave: () => void;
};

function patchBlock(blocks: DraftBlock[], idx: number, patch: Partial<DraftBlock>): DraftBlock[] {
  return blocks.map((b, i) => (i === idx ? { ...b, ...patch } : b));
}

export default function TechCardForm({
  open,
  editing,
  materials,
  serviceOptions,
  draftBlocks,
  serviceId,
  cardName,
  cardNotes,
  saving,
  onClose,
  onServiceId,
  onCardName,
  onCardNotes,
  onBlocks,
  onSave,
}: Props) {
  const [uploadingKey, setUploadingKey] = useState<string | null>(null);

  const materialMap = useMemo(() => {
    const m = new Map<number, MaterialOption>();
    materials.forEach((x) => m.set(x.id, x));
    return m;
  }, [materials]);

  const totalDuration = draftBlocks.reduce((s, b) => s + (Number(b.duration_minutes) || 0), 0);
  const draftCost = draftBlocks.reduce((sum, block) => (
    sum + block.items.reduce((s, row) => {
      if (!row.material_id) return s;
      const mat = materialMap.get(row.material_id);
      return s + (Number(row.quantity) || 0) * (Number(mat?.purchase_price) || 0);
    }, 0)
  ), 0);

  const uploadPhoto = (blockIdx: number): UploadProps['customRequest'] => (
    async (options) => {
      const file = options.file as File;
      const block = draftBlocks[blockIdx];
      setUploadingKey(block?.key || null);
      try {
        const fd = new FormData();
        fd.append('file', file);
        const data = await apiFetch<{ url: string }>('/api/tech-cards/upload-photo', {
          method: 'POST',
          body: fd,
        });
        onBlocks((prev) => patchBlock(prev, blockIdx, { photo_url: data.url }));
        options.onSuccess?.(data);
        message.success('Фото загружено');
      } catch (e: unknown) {
        const err = e instanceof Error ? e : new Error('Ошибка загрузки');
        options.onError?.(err);
        message.error(err.message);
      }
      setUploadingKey(null);
    }
  );

  return (
    <Modal
      title={(
        <Text className="text-gold-bold">
          {editing ? 'Редактировать техкарту' : 'Новая техкарта'}
        </Text>
      )}
      open={open}
      onCancel={onClose}
      footer={null}
      className="modal-command"
      width={920}
      destroyOnClose
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div>
          <span className="label-field">Услуга *</span>
          <Select
            size="large"
            className="input-luxury"
            style={{ width: '100%' }}
            placeholder="Выберите услугу"
            value={serviceId}
            disabled={!!editing}
            onChange={onServiceId}
            options={serviceOptions}
            showSearch
            optionFilterProp="label"
          />
        </div>
        <div>
          <span className="label-field">Название техкарты</span>
          <Input
            size="large"
            className="input-luxury"
            placeholder="По умолчанию — название услуги"
            value={cardName}
            onChange={(e) => onCardName(e.target.value)}
          />
        </div>
        <div>
          <span className="label-field">Заметки</span>
          <TextArea
            rows={2}
            className="input-luxury"
            value={cardNotes}
            onChange={(e) => onCardNotes(e.target.value)}
          />
        </div>

        <div className="tech-card-form-section">
          <Text className="text-gold-bold">Шаги инструкции</Text>
          <Button
            size="small"
            icon={<PlusOutlined />}
            look="ghost"
            onClick={() => onBlocks((p) => [...p, newDraftBlock(`Блок ${p.length + 1}`)])}
          >
            Добавить блок
          </Button>
        </div>

        {draftBlocks.map((block, bIdx) => (
          <Card key={block.key} variant="admin" className="tech-card-form-block">
            <div className="tech-card-form-section">
              <Text className="text-gold-bold">Блок {bIdx + 1}</Text>
              <Space>
                <Button
                  size="small"
                  icon={<ArrowUpOutlined />}
                  className="btn-action-gold"
                  disabled={bIdx === 0}
                  onClick={() => onBlocks((p) => {
                    const next = [...p];
                    [next[bIdx - 1], next[bIdx]] = [next[bIdx], next[bIdx - 1]];
                    return next;
                  })}
                />
                <Button
                  size="small"
                  icon={<ArrowDownOutlined />}
                  className="btn-action-gold"
                  disabled={bIdx === draftBlocks.length - 1}
                  onClick={() => onBlocks((p) => {
                    const next = [...p];
                    [next[bIdx + 1], next[bIdx]] = [next[bIdx], next[bIdx + 1]];
                    return next;
                  })}
                />
                <Button
                  size="small"
                  icon={<DeleteOutlined />}
                  className="btn-action-danger"
                  disabled={draftBlocks.length <= 1}
                  onClick={() => onBlocks((p) => p.filter((_, i) => i !== bIdx))}
                />
              </Space>
            </div>

            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div>
                <span className="label-field">Название блока *</span>
                <Input
                  className="input-luxury"
                  placeholder="Например, Подготовка шампуня"
                  value={block.title}
                  onChange={(e) => onBlocks((p) => patchBlock(p, bIdx, { title: e.target.value }))}
                />
              </div>
              <div>
                <span className="label-field">Описание / инструкция</span>
                <TextArea
                  rows={3}
                  className="input-luxury"
                  placeholder="Развести n гр шампуня в m гр воды, перемешать 20 секунд…"
                  value={block.description}
                  onChange={(e) => onBlocks((p) => patchBlock(p, bIdx, { description: e.target.value }))}
                />
              </div>
              <Row gutter={12}>
                <Col xs={24} sm={8}>
                  <span className="label-field">Длительность, мин</span>
                  <InputNumber
                    className="input-luxury"
                    style={{ width: '100%' }}
                    min={0}
                    value={block.duration_minutes}
                    onChange={(v) => onBlocks((p) => patchBlock(p, bIdx, { duration_minutes: Number(v) || 0 }))}
                  />
                </Col>
                <Col xs={24} sm={16}>
                  <span className="label-field">Фото шага</span>
                  <Space>
                    <Upload
                      accept="image/jpeg,image/png,image/webp"
                      showUploadList={false}
                      customRequest={uploadPhoto(bIdx)}
                    >
                      <Button
                        icon={<PictureOutlined />}
                        look="ghost"
                        loading={uploadingKey === block.key}
                      >
                        {block.photo_url ? 'Заменить фото' : 'Загрузить фото'}
                      </Button>
                    </Upload>
                    {block.photo_url ? (
                      <Button
                        size="small"
                        look="ghost"
                        onClick={() => onBlocks((p) => patchBlock(p, bIdx, { photo_url: null }))}
                      >
                        Убрать
                      </Button>
                    ) : null}
                  </Space>
                  {block.photo_url ? (
                    <div className="tech-card-form-photo">
                      <StepPhoto src={block.photo_url} alt={block.title} size="thumb" />
                    </div>
                  ) : null}
                </Col>
              </Row>

              <div className="tech-card-form-section tech-card-form-section--tight">
                <span className="label-field">Материалы шага</span>
                <Button
                  size="small"
                  icon={<PlusOutlined />}
                  look="ghost"
                  onClick={() => onBlocks((p) => patchBlock(p, bIdx, {
                    items: [...p[bIdx].items, newDraftItem()],
                  }))}
                >
                  Материал
                </Button>
              </div>
              {block.items.map((row, iIdx) => {
                const mat = row.material_id ? materialMap.get(row.material_id) : undefined;
                return (
                  <Row key={row.key} gutter={8} align="middle">
                    <Col span={13}>
                      <Select
                        className="input-luxury"
                        style={{ width: '100%' }}
                        placeholder="Материал со склада"
                        value={row.material_id}
                        showSearch
                        optionFilterProp="label"
                        allowClear
                        options={materials.map((m) => ({
                          value: m.id,
                          label: `${m.name}${m.sku ? ` (${m.sku})` : ''} · ${formatUnit(m.unit)}`,
                        }))}
                        onChange={(v) => onBlocks((p) => {
                          const items = p[bIdx].items.map((r, i) => (
                            i === iIdx ? { ...r, material_id: v } : r
                          ));
                          return patchBlock(p, bIdx, { items });
                        })}
                      />
                    </Col>
                    <Col span={7}>
                      <InputNumber
                        className="input-luxury"
                        style={{ width: '100%' }}
                        min={0.001}
                        step={0.1}
                        value={row.quantity}
                        addonAfter={formatUnit(mat?.unit)}
                        onChange={(v) => onBlocks((p) => {
                          const items = p[bIdx].items.map((r, i) => (
                            i === iIdx ? { ...r, quantity: Number(v) || 0 } : r
                          ));
                          return patchBlock(p, bIdx, { items });
                        })}
                      />
                    </Col>
                    <Col span={4}>
                      <Button
                        size="small"
                        icon={<DeleteOutlined />}
                        className="btn-action-danger"
                        onClick={() => onBlocks((p) => {
                          const items = p[bIdx].items.filter((_, i) => i !== iIdx);
                          return patchBlock(p, bIdx, {
                            items: items.length ? items : [newDraftItem()],
                          });
                        })}
                      />
                    </Col>
                  </Row>
                );
              })}
            </Space>
          </Card>
        ))}

        <div className="tech-card-form-total">
          <DurationMark minutes={totalDuration} />
          <Text className="text-gold-bold">
            Итого материалов: {formatCurrency(draftCost)}
          </Text>
        </div>

        <Button type="primary" size="large" look="gold" loading={saving} onClick={onSave}>
          {editing ? 'Сохранить' : 'Создать'}
        </Button>
      </Space>
    </Modal>
  );
}
