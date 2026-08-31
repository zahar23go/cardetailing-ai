/**
 * Пользователи — /crm/users
 * Клиенты (RFM) / мастера / админы + карточка клиента. Без state OwnerDashboard.
 */
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  Tabs,
  message,
  Popconfirm,
  Empty,
  Spin,
  Tooltip,
  Select,
  InputNumber,
} from 'antd';
import { Button, Modal } from '../../../components/ui';
import { PhoneOutlined, DeleteOutlined, ToolOutlined } from '@ant-design/icons';
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
  commission_percent?: number;
}

interface ServiceOption {
  id: number;
  name: string;
}

interface SkillItem {
  service_id: number;
  service_name: string;
  has_tech_card: boolean;
  commission_percent: number;
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
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab');
  const roleTab = tabFromUrl === 'masters' || tabFromUrl === 'admins' ? tabFromUrl : 'clients';
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

  const [skillModal, setSkillModal] = useState(false);
  const [skillMaster, setSkillMaster] = useState<UserRow | null>(null);
  const [skillLoading, setSkillLoading] = useState(false);
  const [skillSaving, setSkillSaving] = useState(false);
  const [skillPercent, setSkillPercent] = useState(0);
  const [skillServiceIds, setSkillServiceIds] = useState<number[]>([]);
  const [allServices, setAllServices] = useState<ServiceOption[]>([]);
  const [skillHasCard, setSkillHasCard] = useState<Record<number, boolean>>({});

  const setRoleTab = (key: string) => {
    if (key === 'clients') {
      setSearchParams({}, { replace: true });
      return;
    }
    setSearchParams({ tab: key }, { replace: true });
  };

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
    } catch {
      message.error('Не удалось загрузить мастеров и админов');
    }
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

  const openSkills = async (row: UserRow) => {
    setSkillMaster(row);
    setSkillModal(true);
    setSkillLoading(true);
    try {
      const [skills, svc] = await Promise.all([
        apiFetch<{ commission_percent: number; items: SkillItem[] }>(`/api/masters/${row.id}/skills`),
        apiFetch<{ items: ServiceOption[] }>('/api/services?skip=0&limit=200'),
      ]);
      setAllServices(svc.items || []);
      setSkillPercent(skills.commission_percent || 0);
      setSkillServiceIds((skills.items || []).map((i) => i.service_id));
      const cards: Record<number, boolean> = {};
      for (const i of skills.items || []) cards[i.service_id] = i.has_tech_card;
      setSkillHasCard(cards);
    } catch (e: any) {
      message.error(e.message || 'Не удалось загрузить навыки');
      setSkillModal(false);
    }
    setSkillLoading(false);
  };

  const saveSkills = async () => {
    if (!skillMaster) return;
    setSkillSaving(true);
    try {
      await apiFetch(`/api/masters/${skillMaster.id}/skills`, {
        method: 'PUT',
        body: JSON.stringify({
          commission_percent: skillPercent,
          items: skillServiceIds.map((id) => ({
            service_id: id,
            commission_percent: skillPercent,
          })),
        }),
      });
      message.success('Услуги и комиссия сохранены');
      setSkillModal(false);
      fetchStaff();
    } catch (e: any) {
      message.error(e.message || 'Не удалось сохранить');
    }
    setSkillSaving(false);
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
        <Button look="ghost" onClick={() => setRoleTab('masters')}>
          Мастера · навыки и комиссия
        </Button>
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
            <Text className="text-titanium d-block" style={{ marginBottom: 12 }}>
              Навыки — какие услуги делает мастер. Комиссия % попадает в чек при закрытии заезда.
            </Text>
            {masters.length === 0 ? (
              <Empty description={<Text className="text-titanium">Нет мастеров. Добавьте на шаге онбординга или здесь.</Text>} />
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
                    title: <Text className="text-gold">Комиссия</Text>,
                    dataIndex: 'commission_percent',
                    key: 'commission_percent',
                    width: 110,
                    render: (val: number | undefined) => (
                      <Text className="text-gold-bold">{val || 0}%</Text>
                    ),
                  },
                  {
                    title: '',
                    key: 'skills',
                    width: 200,
                    render: (_: unknown, record: UserRow) => (
                      <Button
                        size="small"
                        look="ghost"
                        icon={<ToolOutlined />}
                        onClick={() => openSkills(record)}
                        style={{ width: 'auto' }}
                      >
                        Навыки и комиссия
                      </Button>
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

      <Modal
        title={<Text className="text-gold-bold">Услуги и комиссия · {skillMaster?.full_name}</Text>}
        open={skillModal}
        onCancel={() => { setSkillModal(false); setSkillMaster(null); }}
        footer={null}
        width={520}
        className="modal-command"
      >
        <Spin spinning={skillLoading}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <span className="label-field">Комиссия в чеке, %</span>
              <InputNumber
                size="large"
                className="w-full input-luxury"
                min={0}
                max={100}
                value={skillPercent}
                onChange={(v) => setSkillPercent(v || 0)}
                style={{ width: '100%' }}
              />
              <Text className="text-titanium text-12 d-block" style={{ marginTop: 4 }}>
                Считается от цены заезда при закрытии. Пустой список услуг — мастер делает всё.
              </Text>
            </div>
            <div>
              <span className="label-field">Услуги / техкарты</span>
              <Select
                mode="multiple"
                size="large"
                className="w-full"
                placeholder="Все услуги"
                value={skillServiceIds}
                onChange={setSkillServiceIds}
                optionFilterProp="label"
                options={allServices.map((s) => ({
                  value: s.id,
                  label: skillHasCard[s.id] ? `${s.name} · техкарта` : s.name,
                }))}
              />
            </div>
            <Button type="primary" look="gold" loading={skillSaving} onClick={saveSkills}>
              Сохранить
            </Button>
          </Space>
        </Spin>
      </Modal>
    </>
  );
}
