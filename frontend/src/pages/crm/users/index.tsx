/**
 * Пользователи — /crm/users
 * Клиенты (RFM) / мастера / админы + карточка клиента. Без state OwnerDashboard.
 */
import React, { useEffect, useState } from 'react';
import {
  Typography, Card, Row, Col, Statistic, Table, Button, Tag, Space, Tabs,
  message, Modal, Popconfirm, Empty, Spin, Tooltip,
} from 'antd';
import { PhoneOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { Text } = Typography;
const { TabPane } = Tabs;

const API_BASE = '';

interface UserRow {
  id: number;
  phone: string;
  full_name: string;
  role: string;
  created_at?: string;
}

interface RfmClient {
  id: number;
  full_name: string;
  phone: string;
  role?: string;
  recency_days: number;
  frequency: number;
  monetary: number;
  segment: string;
  last_visit: string | null;
  created_at: string | null;
}

interface SegmentCount {
  segment: string;
  count: number;
  total_revenue: number;
  percent: number;
}

interface RfmResponse {
  clients: RfmClient[];
  segments: SegmentCount[];
  total: number;
}

const ROLE_LABELS: Record<string, string> = {
  client: '👤 Клиент',
  master: '🔧 Мастер',
  admin: '👑 Владелец',
  super_admin: '⭐ Супер-админ',
};

const SEG_COLORS: Record<string, string> = {
  vip: '#C8A977',
  loyal: '#4ECB71',
  regular: '#AAB2BF',
  new: '#69B1FF',
  sleeping: '#B76A29',
  lost: '#ff4d4f',
};

const SEG_LABELS: Record<string, string> = {
  vip: 'VIP',
  loyal: 'Лояльные',
  regular: 'Постоянные',
  new: 'Новые',
  sleeping: 'Спящие',
  lost: 'Ушедшие',
};

const SEG_TAG_COLORS: Record<string, string> = {
  vip: 'gold',
  loyal: 'green',
  regular: 'default',
  new: 'blue',
  sleeping: 'orange',
  lost: 'red',
};

const SEG_TAG_LABELS: Record<string, string> = {
  vip: 'VIP',
  loyal: 'Лояльный',
  regular: 'Постоянный',
  new: 'Новый',
  sleeping: 'Спящий',
  lost: 'Ушедший',
};

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

const formatCurrency = (val: number) => `${val.toLocaleString()} ₽`;

export default function UsersPage() {
  const [roleTab, setRoleTab] = useState('clients');
  const [clients, setClients] = useState<RfmClient[]>([]);
  const [segments, setSegments] = useState<SegmentCount[]>([]);
  const [segmentFilter, setSegmentFilter] = useState('');
  const [clientsLoading, setClientsLoading] = useState(false);

  const [allUsers, setAllUsers] = useState<UserRow[]>([]);
  const [staffLoading, setStaffLoading] = useState(false);

  const [clientModal, setClientModal] = useState(false);
  const [clientDetail, setClientDetail] = useState<any>(null);
  const [clientLoading, setClientLoading] = useState(false);
  const [clientPoints, setClientPoints] = useState<{
    balance: number;
    total_earned: number;
    total_spent: number;
  } | null>(null);

  const fetchClients = async (segment?: string) => {
    setClientsLoading(true);
    try {
      const path = segment
        ? `/api/users/segments?segment=${segment}`
        : '/api/users/segments';
      const data = await apiFetch<RfmResponse>(path);
      setClients(data.clients);
      setSegments(data.segments);
    } catch {
      message.error('Ошибка загрузки пользователей');
    }
    setClientsLoading(false);
  };

  const fetchStaff = async () => {
    setStaffLoading(true);
    try {
      const data = await apiFetch<{ items: UserRow[]; total: number }>('/api/users?limit=500');
      setAllUsers(data.items);
    } catch { /* ignore */ }
    setStaffLoading(false);
  };

  useEffect(() => {
    fetchClients();
    fetchStaff();
  }, []);

  const handleSegmentFilter = (value: string) => {
    setSegmentFilter(value);
    fetchClients(value || undefined);
  };

  const handleDeleteUser = async (userId: number, userName: string) => {
    try {
      await apiFetch(`/api/users/${userId}`, { method: 'DELETE' });
      message.success(`✅ Пользователь «${userName}» удалён`);
      fetchClients(segmentFilter || undefined);
      fetchStaff();
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления пользователя');
    }
  };

  const openClientDetail = async (clientId: number) => {
    setClientLoading(true);
    setClientModal(true);
    setClientPoints(null);
    try {
      const [data, pointsData] = await Promise.all([
        apiFetch<any>(`/api/users/${clientId}`),
        apiFetch<{ items: { balance: number; total_earned: number; total_spent: number }[] }>(
          `/api/loyalty/points?client_id=${clientId}`,
        ),
      ]);
      setClientDetail(data);
      if (pointsData.items && pointsData.items.length > 0) {
        setClientPoints(pointsData.items[0]);
      }
    } catch {
      message.error('Ошибка загрузки данных клиента');
      setClientModal(false);
    }
    setClientLoading(false);
  };

  const masters = allUsers.filter((u) => u.role === 'master');
  const admins = allUsers.filter((u) => u.role === 'admin' || u.role === 'super_admin');

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Команда и клиенты</div>
          <h3>Пользователи</h3>
        </div>
      </div>

      <Tabs
        activeKey={roleTab}
        onChange={setRoleTab}
        className="admin-inner-tabs"
        tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: '16px' }}
        size="small"
      >
        <TabPane tab="👤 Клиенты" key="clients">
          <Spin spinning={clientsLoading}>
            {segments.length > 0 && (
              <Row gutter={[8, 8]} className="mb-12">
                {segments.map((sc) => (
                  <Col xs={12} sm={8} md={4} key={sc.segment}>
                    <Card
                      size="small"
                      className="card-kpi"
                      style={{
                        cursor: 'pointer',
                        borderColor: segmentFilter === sc.segment ? SEG_COLORS[sc.segment] : undefined,
                      }}
                      onClick={() =>
                        handleSegmentFilter(segmentFilter === sc.segment ? '' : sc.segment)
                      }
                    >
                      <Statistic
                        title={
                          <Text className="text-titanium text-11">
                            {SEG_LABELS[sc.segment] || sc.segment}
                          </Text>
                        }
                        value={sc.count}
                        suffix={<Text className="text-titanium text-11">({sc.percent}%)</Text>}
                        valueStyle={{
                          color: SEG_COLORS[sc.segment] || '#AAB2BF',
                          fontSize: '20px',
                          fontWeight: 700,
                        }}
                      />
                    </Card>
                  </Col>
                ))}
              </Row>
            )}

            {clients.length === 0 && !clientsLoading ? (
              <Empty description={<Text className="text-titanium">Нет клиентов</Text>} />
            ) : (
              <Table
                dataSource={clients}
                rowKey="id"
                pagination={{ pageSize: 20, size: 'small' }}
                columns={[
                  {
                    title: <Text className="text-gold">Имя</Text>,
                    dataIndex: 'full_name',
                    key: 'full_name',
                    render: (val) => <Text className="text-white text-medium">{val}</Text>,
                  },
                  {
                    title: <Text className="text-gold">Телефон</Text>,
                    dataIndex: 'phone',
                    key: 'phone',
                    render: (val) => (
                      <Text className="text-titanium"><PhoneOutlined /> {val}</Text>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Сегмент</Text>,
                    dataIndex: 'segment',
                    key: 'segment',
                    width: 120,
                    render: (val: string) => (
                      <Tag color={SEG_TAG_COLORS[val] || 'default'} className="tag-status">
                        {SEG_TAG_LABELS[val] || val}
                      </Tag>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Визиты</Text>,
                    dataIndex: 'frequency',
                    key: 'frequency',
                    width: 70,
                    render: (val) => <Text className="text-white text-13">{val}</Text>,
                  },
                  {
                    title: <Text className="text-gold">Сумма</Text>,
                    dataIndex: 'monetary',
                    key: 'monetary',
                    width: 100,
                    render: (val) => (
                      <Text className="text-gold-bold text-13">{val.toLocaleString()} ₽</Text>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Дата рег.</Text>,
                    dataIndex: 'created_at',
                    key: 'created_at',
                    render: (val) => (
                      <Text className="text-titanium">
                        {val ? dayjs(val).format('DD.MM.YYYY') : '—'}
                      </Text>
                    ),
                  },
                  {
                    title: '',
                    key: 'actions',
                    width: 80,
                    render: (_, record) => (
                      <Space size="small">
                        <Tooltip title="История клиента">
                          <Button
                            size="small"
                            onClick={() => openClientDetail(record.id)}
                            className="btn-action-gold"
                          >
                            📋
                          </Button>
                        </Tooltip>
                        <Popconfirm
                          title={`Удалить клиента «${record.full_name}»?`}
                          description="Будут удалены все автомобили и записи."
                          onConfirm={() => handleDeleteUser(record.id, record.full_name)}
                          okText="Да, удалить"
                          cancelText="Отмена"
                          okButtonProps={{ danger: true }}
                        >
                          <Tooltip title="Удалить клиента">
                            <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                          </Tooltip>
                        </Popconfirm>
                      </Space>
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
          </Spin>
        </TabPane>

        <TabPane tab="🔧 Мастера" key="masters">
          <Spin spinning={staffLoading}>
            {masters.length === 0 ? (
              <Empty description={<Text className="text-titanium">Нет мастеров</Text>} />
            ) : (
              <Table
                dataSource={masters}
                rowKey="id"
                pagination={{ pageSize: 20, size: 'small' }}
                columns={[
                  {
                    title: <Text className="text-gold">Имя</Text>,
                    dataIndex: 'full_name',
                    key: 'full_name',
                    render: (val) => <Text className="text-white text-medium">{val}</Text>,
                  },
                  {
                    title: <Text className="text-gold">Телефон</Text>,
                    dataIndex: 'phone',
                    key: 'phone',
                    render: (val) => (
                      <Text className="text-titanium"><PhoneOutlined /> {val}</Text>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Роль</Text>,
                    dataIndex: 'role',
                    key: 'role',
                    width: 140,
                    render: (val: string) => (
                      <Tag color="cyan" className="tag-status">{ROLE_LABELS[val] || val}</Tag>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Дата рег.</Text>,
                    dataIndex: 'created_at',
                    key: 'created_at',
                    render: (val) => (
                      <Text className="text-titanium">
                        {val ? dayjs(val).format('DD.MM.YYYY') : '—'}
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
          </Spin>
        </TabPane>

        <TabPane tab="👑 Админы" key="admins">
          <Spin spinning={staffLoading}>
            {admins.length === 0 ? (
              <Empty description={<Text className="text-titanium">Нет администраторов</Text>} />
            ) : (
              <Table
                dataSource={admins}
                rowKey="id"
                pagination={{ pageSize: 20, size: 'small' }}
                columns={[
                  {
                    title: <Text className="text-gold">Имя</Text>,
                    dataIndex: 'full_name',
                    key: 'full_name',
                    render: (val) => <Text className="text-white text-medium">{val}</Text>,
                  },
                  {
                    title: <Text className="text-gold">Телефон</Text>,
                    dataIndex: 'phone',
                    key: 'phone',
                    render: (val) => (
                      <Text className="text-titanium"><PhoneOutlined /> {val}</Text>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Роль</Text>,
                    dataIndex: 'role',
                    key: 'role',
                    width: 160,
                    render: (val: string) => (
                      <Tag color="gold" className="tag-status">{ROLE_LABELS[val] || val}</Tag>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Дата рег.</Text>,
                    dataIndex: 'created_at',
                    key: 'created_at',
                    render: (val) => (
                      <Text className="text-titanium">
                        {val ? dayjs(val).format('DD.MM.YYYY') : '—'}
                      </Text>
                    ),
                  },
                  {
                    title: '',
                    key: 'actions',
                    width: 80,
                    render: (_, record) => (
                      <Space size="small">
                        <Popconfirm
                          title={`Удалить пользователя «${record.full_name}»?`}
                          description="Будут удалены все связанные данные."
                          onConfirm={() => handleDeleteUser(record.id, record.full_name)}
                          okText="Да, удалить"
                          cancelText="Отмена"
                          okButtonProps={{ danger: true }}
                        >
                          <Tooltip title="Удалить">
                            <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                          </Tooltip>
                        </Popconfirm>
                      </Space>
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
          </Spin>
        </TabPane>
      </Tabs>

      <Modal
        title={<Text className="text-gold-bold">📋 Карточка клиента</Text>}
        open={clientModal}
        onCancel={() => { setClientModal(false); setClientDetail(null); setClientPoints(null); }}
        footer={null}
        width={520}
        className="modal-command"
      >
        <Spin spinning={clientLoading}>
          {clientDetail && (
            <Space direction="vertical" size="middle">
              <Card size="small" className="card-detail">
                <Space direction="vertical" size={4}>
                  <Text className="text-white text-18-bold">{clientDetail.full_name}</Text>
                  <Text className="text-titanium">📱 {clientDetail.phone}</Text>
                  <Text className="text-titanium">
                    📅 Регистрация: {dayjs(clientDetail.created_at).format('DD.MM.YYYY')}
                  </Text>
                </Space>
              </Card>

              <Row gutter={16}>
                <Col span={8}>
                  <Card size="small" className="card-detail">
                    <Text className="text-gold-bold text-24">{clientDetail.appointments_count}</Text>
                    <Text className="text-titanium d-block text-12">Визитов</Text>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" className="card-detail">
                    <Text className="text-gold-bold text-24">
                      {formatCurrency(clientDetail.total_spent)}
                    </Text>
                    <Text className="text-titanium d-block text-12">Потрачено</Text>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" className="card-detail">
                    <Text className="text-gold-bold text-24">
                      {clientDetail.last_visit ? dayjs(clientDetail.last_visit).format('DD.MM') : '—'}
                    </Text>
                    <Text className="text-titanium d-block text-12">Последний</Text>
                  </Card>
                </Col>
              </Row>

              <Card size="small" className="card-luxury" style={{ marginTop: '8px' }}>
                <Text className="title-gold text-14 d-block mb-8">🏅 Баллы лояльности</Text>
                {clientPoints ? (
                  <Row gutter={[12, 12]}>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-gold-bold text-24">{clientPoints.balance}</Text>
                        <Text className="text-titanium d-block text-11">Баллы</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-white-bold text-24">{clientPoints.total_earned}</Text>
                        <Text className="text-titanium d-block text-11">Заработано</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-white-bold text-24">{clientPoints.total_spent}</Text>
                        <Text className="text-titanium d-block text-11">Потрачено</Text>
                      </div>
                    </Col>
                  </Row>
                ) : (
                  <Text className="text-titanium text-12">Нет данных о баллах</Text>
                )}
              </Card>

              {clientDetail.last_visit && (
                <Text className="text-small text-center d-block">
                  🕐 Последний визит: {dayjs(clientDetail.last_visit).format('DD.MM.YYYY HH:mm')}
                </Text>
              )}
            </Space>
          )}
        </Spin>
      </Modal>
    </>
  );
}
