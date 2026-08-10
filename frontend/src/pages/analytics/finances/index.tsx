/**
 * Финансы — /analytics/finances
 * P&L + ExpensesModule. Локальный state, без OwnerDashboard.
 */
import React, { useEffect, useState } from 'react';
import {
  Typography, Card, Row, Col, Statistic, Table, Tag, Spin,
} from 'antd';
import { DollarOutlined } from '@ant-design/icons';
import ExpensesModule from '../../../components/ExpensesModule';

const { Text } = Typography;

const API_BASE = '';

interface ServiceMargin {
  service_id: number;
  service_name: string;
  category?: string;
  total_revenue: number;
  total_material_cost: number;
  gross_profit: number;
  margin_percent: number;
  appointment_count: number;
}

interface PLReport {
  total_revenue: number;
  completed_appointments: number;
  avg_check: number;
  total_material_cost: number;
  total_expenses: number;
  expenses_by_category: Record<string, number>;
  gross_profit: number;
  gross_margin_percent: number;
  net_profit: number;
  net_margin_percent: number;
  service_margins: ServiceMargin[];
  period: string;
}

async function apiFetch<T>(path: string): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка ${res.status}`);
  }
  return res.json();
}

export default function FinancesPage() {
  const [plReport, setPlReport] = useState<PLReport | null>(null);
  const [plLoading, setPlLoading] = useState(false);

  useEffect(() => {
    setPlLoading(true);
    apiFetch<PLReport>('/api/analytics/pl')
      .then(setPlReport)
      .catch(() => {})
      .finally(() => setPlLoading(false));
  }, []);

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">P&amp;L</div>
          <h3>Финансы салона</h3>
        </div>
      </div>

      <Spin spinning={plLoading}>
        {plReport && (
          <>
            <Row gutter={[16, 16]} className="mb-12">
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Выручка (месяц)</Text>}
                    value={plReport.total_revenue}
                    prefix={<DollarOutlined className="text-gold" />}
                    precision={0}
                    suffix={<Text className="text-titanium text-12">₽</Text>}
                    valueStyle={{ color: '#C8A977', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Расходы (материалы)</Text>}
                    value={plReport.total_material_cost}
                    precision={0}
                    suffix={<Text className="text-titanium text-12">₽</Text>}
                    valueStyle={{ color: '#AAB2BF', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Постоянные расходы</Text>}
                    value={plReport.total_expenses}
                    precision={0}
                    suffix={<Text className="text-titanium text-12">₽</Text>}
                    valueStyle={{ color: '#ff4d4f', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Чистая прибыль</Text>}
                    value={plReport.net_profit}
                    precision={0}
                    suffix={<Text className="text-titanium text-12">₽</Text>}
                    valueStyle={{
                      color: plReport.net_profit >= 0 ? '#4ECB71' : '#ff4d4f',
                      fontSize: '22px',
                      fontWeight: 700,
                    }}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]} className="mb-12">
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Средний чек</Text>}
                    value={plReport.avg_check}
                    precision={0}
                    suffix={<Text className="text-titanium text-12">₽</Text>}
                    valueStyle={{ color: '#C8A977', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Валовая маржа</Text>}
                    value={plReport.gross_margin_percent}
                    precision={1}
                    suffix={<Text className="text-titanium text-12">%</Text>}
                    valueStyle={{ color: '#4ECB71', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Чистая маржа</Text>}
                    value={plReport.net_margin_percent}
                    precision={1}
                    suffix={<Text className="text-titanium text-12">%</Text>}
                    valueStyle={{
                      color: plReport.net_margin_percent >= 0 ? '#4ECB71' : '#ff4d4f',
                      fontSize: '22px',
                      fontWeight: 700,
                    }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" size="small">
                  <Statistic
                    title={<Text className="text-titanium text-12">Завершено записей</Text>}
                    value={plReport.completed_appointments}
                    valueStyle={{ color: '#FFFFFF', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
            </Row>

            <Card className="card-luxury" style={{ marginBottom: '16px' }}>
              <Text className="title-gold text-16 d-block mb-8">Маржинальность по услугам</Text>
              {plReport.service_margins.length === 0 ? (
                <Text className="text-titanium text-13">Нет данных за месяц</Text>
              ) : (
                <Table
                  dataSource={plReport.service_margins}
                  rowKey="service_id"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: <Text className="text-titanium text-12">Услуга</Text>,
                      dataIndex: 'service_name',
                      key: 'name',
                      render: (v, r) => (
                        <div>
                          <Text className="text-white text-13">{v}</Text>
                          {r.category && (
                            <Tag className="tag-category" style={{ marginLeft: 6 }}>{r.category}</Tag>
                          )}
                        </div>
                      ),
                    },
                    {
                      title: <Text className="text-titanium text-12">Записей</Text>,
                      dataIndex: 'appointment_count',
                      key: 'cnt',
                      width: 70,
                      render: (v) => <Text className="text-white text-13">{v}</Text>,
                    },
                    {
                      title: <Text className="text-titanium text-12">Выручка</Text>,
                      dataIndex: 'total_revenue',
                      key: 'rev',
                      width: 100,
                      render: (v) => (
                        <Text className="text-gold-bold text-13">{v.toLocaleString()} ₽</Text>
                      ),
                    },
                    {
                      title: <Text className="text-titanium text-12">Материалы</Text>,
                      dataIndex: 'total_material_cost',
                      key: 'mat',
                      width: 90,
                      render: (v) => (
                        <Text className="text-titanium text-13">{v.toLocaleString()} ₽</Text>
                      ),
                    },
                    {
                      title: <Text className="text-titanium text-12">Маржа</Text>,
                      dataIndex: 'margin_percent',
                      key: 'margin',
                      width: 80,
                      render: (v) => (
                        <Text
                          className="text-13"
                          style={{
                            color: v >= 50 ? '#4ECB71' : v >= 30 ? '#C8A977' : '#ff4d4f',
                            fontWeight: 600,
                          }}
                        >
                          {v}%
                        </Text>
                      ),
                    },
                  ]}
                  components={{
                    header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                    body: {
                      row: (p: any) => <tr {...p} className="table-body-row" />,
                      cell: (p: any) => <td {...p} className="table-body-cell" />,
                    },
                  }}
                />
              )}
            </Card>
          </>
        )}

        <div style={{ marginTop: 16 }}>
          <ExpensesModule />
        </div>
      </Spin>
    </>
  );
}
