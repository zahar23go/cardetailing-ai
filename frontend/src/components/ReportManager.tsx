/* ============================================================
   ReportManager — отчёты по выручке (стиль Command Center)
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Card, Row, Col, Select, Button, Space, Spin, Table, Tag, Empty,
} from 'antd';
import {
  DownloadOutlined, ReloadOutlined,
} from '@ant-design/icons';

const { Text } = Typography;
const { Option } = Select;
const API_BASE = '';

interface PeriodComp {
  period: string; current_revenue: number; previous_revenue: number;
  current_count: number; previous_count: number; change_percent: number;
}
interface ServiceSummary {
  service_id: number; service_name: string; category?: string;
  total_revenue: number; total_count: number; avg_price: number;
}
interface MasterSummary {
  master_id: number; master_name: string;
  total_revenue: number; completed_count: number; avg_revenue: number;
}
interface Detail {
  date: string; service_name: string; master_name: string; client_name: string;
  total_price: number; material_cost: number; profit: number;
}
interface ReportData {
  total_revenue: number; total_profit: number;
  period_comparison: PeriodComp[];
  by_service: ServiceSummary[];
  by_master: MasterSummary[];
  details: Detail[];
}

const PERIOD_PLAQUE: Record<string, string> = {
  day: 'Отчёт за день · выручка, прибыль и разбивка',
  week: 'Отчёт за неделю · выручка, прибыль и разбивка',
  month: 'Отчёт за месяц · выручка, прибыль и разбивка',
  year: 'Отчёт за год · выручка, прибыль и разбивка',
};

async function apiFetch<T>(path: string): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!res.ok) throw new Error(`Ошибка ${res.status}`);
  return res.json();
}

export default function ReportManager() {
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState('month');

  const fetchReport = async (p = period) => {
    setLoading(true);
    try {
      const result = await apiFetch<ReportData>(`/api/reports/revenue?period=${p}`);
      setData(result);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { fetchReport(); }, []);

  const downloadCSV = () => {
    const token = localStorage.getItem('token');
    const url = `${API_BASE}/api/reports/revenue/csv?period=${period}`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url2 = URL.createObjectURL(blob);
        const a2 = document.createElement('a');
        a2.href = url2;
        a2.download = `revenue_report_${period}.csv`;
        a2.click();
        URL.revokeObjectURL(url2);
      });
  };

  const comparison = data?.period_comparison?.[0];
  const change = comparison?.change_percent || 0;
  const changeTone = change >= 0 ? 'ok' : 'danger';

  return (
    <div className="reports-module">
      <div className="admin-section-head reports-head">
        <div>
          <div className="admin-overview-kicker">Аналитика</div>
          <h3>Отчёты по выручке</h3>
          <p className="reports-lead">{PERIOD_PLAQUE[period] || PERIOD_PLAQUE.month}</p>
        </div>
        <div className="reports-toolbar">
          <Select
            value={period}
            onChange={(v) => { setPeriod(v); fetchReport(v); }}
            className="appt-filter-select"
            style={{ minWidth: 150 }}
          >
            <Option value="day">За день</Option>
            <Option value="week">За неделю</Option>
            <Option value="month">За месяц</Option>
            <Option value="year">За год</Option>
          </Select>
          <Button
            icon={<ReloadOutlined />}
            className="btn-gold-secondary"
            onClick={() => fetchReport()}
          >
            Обновить
          </Button>
          <Button
            icon={<DownloadOutlined />}
            className="btn-gold"
            onClick={downloadCSV}
          >
            CSV
          </Button>
        </div>
      </div>

      <Spin spinning={loading}>
        {!data && !loading ? (
          <Empty description={<span className="text-titanium">Нет данных за период</span>} />
        ) : data ? (
          <>
            <Row gutter={[12, 12]} className="appt-stats-row">
              <Col xs={12} sm={6}>
                <Card className="admin-kpi-card" bordered={false}>
                  <div className="admin-kpi-label">Выручка</div>
                  <div className="admin-kpi-value">{data.total_revenue.toLocaleString()} ₽</div>
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="admin-kpi-card tone-ok" bordered={false}>
                  <div className="admin-kpi-label">Прибыль</div>
                  <div className="admin-kpi-value">{data.total_profit.toLocaleString()} ₽</div>
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className={`admin-kpi-card tone-${changeTone}`} bordered={false}>
                  <div className="admin-kpi-label">К предыдущему</div>
                  <div className="admin-kpi-value">
                    {change >= 0 ? '+' : ''}{change.toFixed(1)}%
                  </div>
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="admin-kpi-card" bordered={false}>
                  <div className="admin-kpi-label">Заказов</div>
                  <div className="admin-kpi-value">{data.details.length}</div>
                </Card>
              </Col>
            </Row>

            <Card className="admin-panel-card" bordered={false} style={{ marginBottom: 16 }}>
              <Text className="admin-panel-title">По услугам</Text>
              <Table
                className="reports-table"
                dataSource={data.by_service}
                rowKey="service_id"
                pagination={false}
                size="small"
                locale={{ emptyText: <Empty description={<span className="text-titanium">Нет услуг</span>} /> }}
                columns={[
                  {
                    title: 'Услуга',
                    dataIndex: 'service_name',
                    render: (v, r) => (
                      <Space size={8} wrap>
                        <Text className="text-white text-13">{v}</Text>
                        {r.category && <Tag className="tag-category">{r.category}</Tag>}
                      </Space>
                    ),
                  },
                  {
                    title: 'Выручка',
                    dataIndex: 'total_revenue',
                    render: (v) => <Text className="text-gold-bold">{Number(v).toLocaleString()} ₽</Text>,
                  },
                  {
                    title: 'Кол-во',
                    dataIndex: 'total_count',
                    render: (v) => <Text className="text-white text-13">{v}</Text>,
                  },
                  {
                    title: 'Средний чек',
                    dataIndex: 'avg_price',
                    render: (v) => <Text className="text-titanium">{Number(v).toLocaleString()} ₽</Text>,
                  },
                ]}
              />
            </Card>

            <Card className="admin-panel-card" bordered={false}>
              <Text className="admin-panel-title">По мастерам</Text>
              <Table
                className="reports-table"
                dataSource={data.by_master}
                rowKey="master_id"
                pagination={false}
                size="small"
                locale={{ emptyText: <Empty description={<span className="text-titanium">Нет данных</span>} /> }}
                columns={[
                  {
                    title: 'Мастер',
                    dataIndex: 'master_name',
                    render: (v) => <Text className="text-white text-13">{v}</Text>,
                  },
                  {
                    title: 'Выручка',
                    dataIndex: 'total_revenue',
                    render: (v) => <Text className="text-gold-bold">{Number(v).toLocaleString()} ₽</Text>,
                  },
                  {
                    title: 'Работ',
                    dataIndex: 'completed_count',
                    render: (v) => <Text className="text-white text-13">{v}</Text>,
                  },
                  {
                    title: 'Средний',
                    dataIndex: 'avg_revenue',
                    render: (v) => <Text className="text-titanium">{Number(v).toLocaleString()} ₽</Text>,
                  },
                ]}
              />
            </Card>
          </>
        ) : null}
      </Spin>
    </div>
  );
}
