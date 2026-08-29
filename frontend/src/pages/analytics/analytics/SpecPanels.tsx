/**
 * П1.1: когорты, treemap услуг, загрузка мастеров и боксов.
 */
import React from 'react';
import { Card, Col, Empty, Progress, Row, Table, Typography } from 'antd';
import { ResponsiveContainer, Treemap, Tooltip as RechartsTooltip } from 'recharts';

const { Text } = Typography;

export type CohortRow = {
  cohort: string;
  size: number;
  cells: { offset: number; clients: number; rate: number }[];
};

export type TreemapNode = { name: string; value: number; count: number };
export type LoadRow = {
  id: number;
  name: string;
  busy_minutes: number;
  capacity_minutes: number;
  occupancy_pct: number;
  appointments: number;
};

export type SpecData = {
  cohorts: CohortRow[];
  treemap: TreemapNode[];
  masters: LoadRow[];
  boxes: LoadRow[];
  period_days: number;
};

const TILES = ['#C8A977', '#D4AF37', '#E0BC5A', '#A67C2D', '#F0D9A0', '#8B6914'];

function hoursLabel(mins: number) {
  const h = mins / 60;
  return `${h.toFixed(1)} ч`;
}

function TreemapCell(props: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  value?: number;
  index?: number;
}) {
  const { x = 0, y = 0, width = 0, height = 0, name = '', value = 0, index = 0 } = props;
  if (width < 8 || height < 8) return null;
  const fill = TILES[index % TILES.length];
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#0B0D10" strokeWidth={1} />
      {width > 56 && height > 28 ? (
        <>
          <text x={x + 8} y={y + 18} fill="#1A1D23" fontSize={11} fontWeight={700}>
            {name.length > 18 ? `${name.slice(0, 16)}…` : name}
          </text>
          <text x={x + 8} y={y + 34} fill="#1A1D23" fontSize={10}>
            {Number(value).toLocaleString('ru-RU')} ₽
          </text>
        </>
      ) : null}
    </g>
  );
}

function LoadList({ title, rows, empty }: { title: string; rows: LoadRow[]; empty: string }) {
  return (
    <Card className="card-luxury" size="small">
      <Text className="title-gold text-16">{title}</Text>
      {rows.length === 0 ? (
        <Empty description={<Text className="text-titanium">{empty}</Text>} />
      ) : (
        rows.map((r) => (
          <div key={r.id} style={{ marginTop: 12 }}>
            <div className="flex-space-between" style={{ marginBottom: 4 }}>
              <Text className="text-white-bold text-13">{r.name}</Text>
              <Text className="text-titanium text-12">
                {r.occupancy_pct}% · {hoursLabel(r.busy_minutes)} / {hoursLabel(r.capacity_minutes)} · {r.appointments} зап.
              </Text>
            </div>
            <Progress
              percent={Math.min(100, r.occupancy_pct)}
              showInfo={false}
              strokeColor="#C8A977"
              trailColor="rgba(255,255,255,0.08)"
            />
          </div>
        ))
      )}
    </Card>
  );
}

export default function SpecPanels({ data }: { data: SpecData | null }) {
  if (!data) return null;
  const offsets = [0, 1, 2, 3, 4, 5];
  const tree = data.treemap.map((n, i) => ({ ...n, fill: TILES[i % TILES.length] }));

  return (
    <Row gutter={[16, 16]} className="mb-12">
      <Col xs={24}>
        <Card className="card-luxury">
          <Text className="title-gold text-16">Когорты клиентов</Text>
          <p className="text-titanium" style={{ margin: '6px 0 12px' }}>
            Месяц первого визита и доля тех, кто вернулся в следующие месяцы (M0 — сам месяц прихода).
          </p>
          {data.cohorts.every((c) => c.size === 0) ? (
            <Empty description={<Text className="text-titanium">Пока нет завершённых визитов для когорт</Text>} />
          ) : (
            <Table
              size="small"
              pagination={false}
              rowKey="cohort"
              dataSource={data.cohorts}
              columns={[
                { title: 'Когорта', dataIndex: 'cohort', width: 110 },
                { title: 'Клиентов', dataIndex: 'size', width: 90 },
                ...offsets.map((off) => ({
                  title: `M${off}`,
                  key: `m${off}`,
                  render: (_: unknown, row: CohortRow) => {
                    const cell = row.cells.find((c) => c.offset === off);
                    if (!cell || row.size === 0) return '—';
                    return `${cell.rate}%`;
                  },
                })),
              ]}
            />
          )}
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card className="card-luxury">
          <Text className="title-gold text-16">Услуги · treemap</Text>
          <p className="text-titanium" style={{ margin: '6px 0 12px' }}>
            Выручка за 90 дней. Площадь блока — доля услуги.
          </p>
          {tree.length === 0 ? (
            <Empty description={<Text className="text-titanium">Нет выручки за 90 дней</Text>} />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <Treemap data={tree} dataKey="value" aspectRatio={4 / 3} stroke="#0B0D10" content={<TreemapCell />}>
                <RechartsTooltip
                  formatter={(v: number, _n, item) => {
                    const p = item?.payload as TreemapNode | undefined;
                    return [`${Number(v).toLocaleString('ru-RU')} ₽ · ${p?.count ?? 0} зап.`, p?.name || 'Услуга'];
                  }}
                />
              </Treemap>
            </ResponsiveContainer>
          )}
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <LoadList
          title={`Загрузка мастеров · ${data.period_days} дн.`}
          rows={data.masters}
          empty="Нет мастеров"
        />
        <div style={{ height: 16 }} />
        <LoadList
          title={`Загрузка боксов · ${data.period_days} дн.`}
          rows={data.boxes}
          empty="Нет боксов"
        />
      </Col>
    </Row>
  );
}
