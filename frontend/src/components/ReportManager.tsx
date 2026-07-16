/* ============================================================
   ReportManager — отчёты, экспорт, сравнение периодов
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Card, Row, Col, Select, Button, Space, Spin, Statistic, Table, Tag,
} from 'antd';
import {
  DownloadOutlined, ReloadOutlined, BarChartOutlined,
} from '@ant-design/icons';

const { Text } = Typography;
const { Option } = Select;
const API_BASE = '';

interface PeriodComp {
  period: string; current_revenue: number; previous_revenue: number;
  current_count: number; previous_count: number; change_percent: number;
}
interface ServiceSummary { service_id: number; service_name: string; category?: string; total_revenue: number; total_count: number; avg_price: number }
interface MasterSummary { master_id: number; master_name: string; total_revenue: number; completed_count: number; avg_revenue: number }
interface Detail { date: string; service_name: string; master_name: string; client_name: string; total_price: number; material_cost: number; profit: number }
interface ReportData { total_revenue: number; total_profit: number; period_comparison: PeriodComp[]; by_service: ServiceSummary[]; by_master: MasterSummary[]; details: Detail[] }

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
    const a = document.createElement('a');
    a.href = url;
    a.setAttribute('Authorization', `Bearer ${token}`);
    // Use fetch to download with auth header
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
  const changeColor = (comparison?.change_percent || 0) >= 0 ? '#4ECB71' : '#ff4d4f';

  return (
    <Space direction="vertical" size="large" className="w-full">
      {/* Header */}
      <div className="flex-space-between">
        <Text className="title-gold text-18">Отчёты по выручке</Text>
        <Space>
          <Select value={period} onChange={(v) => { setPeriod(v); fetchReport(v); }} style={{ width: 140 }}>
            <Option value="day">За день</Option>
            <Option value="week">За неделю</Option>
            <Option value="month">За месяц</Option>
            <Option value="year">За год</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={() => fetchReport()} className="btn-logout" />
          <Button icon={<DownloadOutlined />} onClick={downloadCSV} className="btn-action-gold">
            CSV
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {data && (
          <>
            {/* KPI */}
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" style={{ textAlign: 'center' }}>
                  <Statistic
                    title={<Text className="text-titanium text-12">Выручка</Text>}
                    value={data.total_revenue}
                    suffix="₽"
                    valueStyle={{ color: '#C8A977', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" style={{ textAlign: 'center' }}>
                  <Statistic
                    title={<Text className="text-titanium text-12">Прибыль</Text>}
                    value={data.total_profit}
                    suffix="₽"
                    valueStyle={{ color: '#4ECB71', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" style={{ textAlign: 'center' }}>
                  <Statistic
                    title={<Text className="text-titanium text-12">К предыдущему</Text>}
                    value={comparison?.change_percent || 0}
                    suffix="%"
                    precision={1}
                    valueStyle={{ color: changeColor, fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card className="card-kpi" style={{ textAlign: 'center' }}>
                  <Statistic
                    title={<Text className="text-titanium text-12">Заказов</Text>}
                    value={data.details.length}
                    valueStyle={{ color: '#FFFFFF', fontSize: '22px', fontWeight: 700 }}
                  />
                </Card>
              </Col>
            </Row>

            {/* По услугам */}
            <Card className="card-luxury">
              <Text className="title-gold text-16 d-block mb-8">По услугам</Text>
              <Table
                dataSource={data.by_service}
                rowKey="service_id"
                pagination={false}
                size="small"
                columns={[
                  { title: <Text className="text-titanium text-12">Услуга</Text>, dataIndex: 'service_name',
                    render: (v, r) => <><Text className="text-white text-13">{v}</Text>{r.category && <Tag className="tag-category">{r.category}</Tag>}</> },
                  { title: <Text className="text-titanium text-12">Выручка</Text>, dataIndex: 'total_revenue',
                    render: (v) => <Text className="text-gold-bold">{v.toLocaleString()} ₽</Text> },
                  { title: <Text className="text-titanium text-12">Кол-во</Text>, dataIndex: 'total_count',
                    render: (v) => <Text className="text-white text-13">{v}</Text> },
                  { title: <Text className="text-titanium text-12">Средний чек</Text>, dataIndex: 'avg_price',
                    render: (v) => <Text className="text-titanium">{v.toLocaleString()} ₽</Text> },
                ]}
              />
            </Card>

            {/* По мастерам */}
            <Card className="card-luxury">
              <Text className="title-gold text-16 d-block mb-8">По мастерам</Text>
              <Table
                dataSource={data.by_master}
                rowKey="master_id"
                pagination={false}
                size="small"
                columns={[
                  { title: <Text className="text-titanium text-12">Мастер</Text>, dataIndex: 'master_name',
                    render: (v) => <Text className="text-white text-13">🔧 {v}</Text> },
                  { title: <Text className="text-titanium text-12">Выручка</Text>, dataIndex: 'total_revenue',
                    render: (v) => <Text className="text-gold-bold">{v.toLocaleString()} ₽</Text> },
                  { title: <Text className="text-titanium text-12">Работ</Text>, dataIndex: 'completed_count',
                    render: (v) => <Text className="text-white text-13">{v}</Text> },
                  { title: <Text className="text-titanium text-12">Средний</Text>, dataIndex: 'avg_revenue',
                    render: (v) => <Text className="text-titanium">{v.toLocaleString()} ₽</Text> },
                ]}
              />
            </Card>
          </>
        )}
      </Spin>
    </Space>
  );
}
