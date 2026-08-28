/**
 * Просмотр техкарты как пошаговой инструкции.
 * Старые карты без блоков / без фото / с длительностью 0 тоже открываются.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Col, Empty, Row, Space, Spin, Typography, message } from 'antd';
import {
  ArrowLeftOutlined, CameraOutlined, ClockCircleOutlined,
  EditOutlined, FileTextOutlined, ToolOutlined,
} from '@ant-design/icons';
import { Button } from '../../../components/ui';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import StepPhoto from './StepPhoto';
import {
  TechCard,
  apiFetch,
  formatCurrency,
  formatDuration,
  formatUnit,
} from './types';

const { Text } = Typography;

export default function TechCardViewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [card, setCard] = useState<TechCard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await apiFetch<TechCard>(`/api/tech-cards/${id}`);
        if (!cancelled) setCard(data);
      } catch (e: unknown) {
        if (!cancelled) {
          message.error(e instanceof Error ? e.message : 'Не удалось загрузить техкарту');
          navigate('/technology/tech-cards');
        }
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [id, navigate]);

  const blocks = useMemo(() => card?.blocks || [], [card]);
  const stepsCount = card?.blocks_count || blocks.length;
  const materialsCount = card?.items_count || 0;

  if (loading) {
    return <Spin />;
  }
  if (!card) return null;

  const title = card.name || card.service_name;

  return (
    <div className="tech-card-view">
      <div className="admin-section-head">
        <div>
          <h3>Технология / Техкарты</h3>
        </div>
        <Space wrap>
          <Button
            icon={<ArrowLeftOutlined />}
            look="ghost"
            onClick={() => navigate('/technology/tech-cards')}
          >
            К списку
          </Button>
          <Button
            type="primary"
            icon={<EditOutlined />}
            look="gold"
            onClick={() => navigate('/technology/tech-cards', { state: { editId: card.id } })}
          >
            Редактировать
          </Button>
        </Space>
      </div>

      <Card variant="admin" className="tech-card-view-head">
        <div className="tech-card-view-head-row">
          <div>
            <div className="tech-card-view-title">{title}</div>
            {card.name && card.name !== card.service_name ? (
              <Text className="text-titanium">{card.service_name}</Text>
            ) : null}
          </div>
          {card.is_active
            ? <Badge variant="success" size="sm">активна</Badge>
            : <Badge variant="neutral" size="sm">выкл</Badge>}
        </div>
        <div className="tech-card-view-price">{formatCurrency(card.service_price)}</div>
        {card.notes ? (
          <div className="tech-card-field">
            <div className="tech-card-field-label">Заметки</div>
            <Text className="text-titanium">{card.notes}</Text>
          </div>
        ) : null}
      </Card>

      <Row gutter={[14, 14]} className="tech-card-view-kpis">
        <Col xs={24} sm={8}>
          <Card variant="kpi">
            <div className="admin-kpi-icon"><FileTextOutlined /></div>
            <div className="admin-kpi-label">Шаги</div>
            <div className="admin-kpi-value">{stepsCount}</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="kpi">
            <div className="admin-kpi-icon"><ClockCircleOutlined /></div>
            <div className="admin-kpi-label">Длительность</div>
            <div className="admin-kpi-value">{formatDuration(card.total_duration_minutes)}</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="stats">
            <div className="admin-kpi-icon"><ToolOutlined /></div>
            <div className="admin-kpi-label">Материалы · {materialsCount}</div>
            <div className="admin-kpi-value text-gold-bold">{formatCurrency(card.estimated_cost)}</div>
          </Card>
        </Col>
      </Row>

      {blocks.length === 0 ? (
        <Empty description={<Text className="text-titanium">В техкарте пока нет шагов</Text>} />
      ) : (
        <>
          {blocks.map((block, idx) => (
            <Card key={block.id || idx} variant="admin" className="tech-card-step">
              <div className="tech-card-step-head">
                <div className="tech-card-step-title">
                  <span className="tech-card-step-index">{idx + 1}</span>
                  <span className="tech-card-step-name">{block.title || 'Без названия'}</span>
                </div>
              </div>

              <div className="tech-card-field">
                <div className="tech-card-field-label">
                  <FileTextOutlined /> Описание
                </div>
                {block.description?.trim() ? (
                  <Text className="text-gold tech-card-field-text">{block.description}</Text>
                ) : (
                  <Text className="text-titanium">Нет описания</Text>
                )}
              </div>

              {block.photo_url ? (
                <div className="tech-card-field">
                  <div className="tech-card-field-label">
                    <CameraOutlined /> Фото
                  </div>
                  <StepPhoto
                    src={block.photo_url}
                    alt={block.title || `Шаг ${idx + 1}`}
                    size="full"
                  />
                </div>
              ) : null}

              <div className="tech-card-field">
                <div className="tech-card-field-label">
                  <ToolOutlined /> Материалы
                </div>
                {block.items?.length ? (
                  <ul className="tech-card-materials">
                    {block.items.map((item, iIdx) => (
                      <li key={`${block.id || idx}-${item.material_id || iIdx}`}>
                        <Text className="text-gold">{item.material_name || 'Материал'}</Text>
                        <Text className="text-gold-bold">
                          {Number(item.quantity || 0).toLocaleString('ru-RU')} {formatUnit(item.material_unit)}
                        </Text>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Text className="text-titanium">Без материалов</Text>
                )}
              </div>

              <div className="tech-card-field">
                <div className="tech-card-field-label">
                  <ClockCircleOutlined /> Время
                </div>
                <Text className="text-gold-bold">{formatDuration(block.duration_minutes || 0)}</Text>
              </div>
            </Card>
          ))}

          <Card variant="stats" className="tech-card-total">
            <div className="admin-kpi-label">Общая длительность</div>
            <div className="admin-kpi-value text-gold-bold">
              {formatDuration(card.total_duration_minutes)}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
