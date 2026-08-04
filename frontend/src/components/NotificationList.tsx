/* ============================================================
   NotificationList — список уведомлений (стиль Command Center)
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, List, Button, Space, Spin, Empty, message, Card,
} from 'antd';
import { CheckOutlined, ReloadOutlined } from '@ant-design/icons';
import { getNotifications, markAsRead, markAllAsRead } from '../api/notifications';
import type { Notification } from '../api/notifications';
import dayjs from 'dayjs';

const { Text } = Typography;

const TYPE_LABELS: Record<string, string> = {
  appointment_reminder: 'Напоминание',
  appointment_cancelled: 'Отмена',
  status_change: 'Статус',
  promo: 'Акция',
  info: 'Инфо',
};

/** Вариант .badge по типу уведомления */
const TYPE_BADGE: Record<string, string> = {
  appointment_reminder: 'badge--gold',
  appointment_cancelled: 'badge--danger',
  status_change: 'badge--info',
  promo: 'badge--success',
  info: 'badge--neutral',
};

interface NotificationListProps {
  unreadOnly?: boolean;
  title?: string;
  plaque?: string;
}

export default function NotificationList({
  unreadOnly = false,
  title = 'Уведомления',
  plaque = 'Лента событий салона · напоминания, статусы и акции',
}: NotificationListProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const fetchData = async (p = page) => {
    setLoading(true);
    try {
      const skip = (p - 1) * PAGE_SIZE;
      const data = await getNotifications(skip, PAGE_SIZE, unreadOnly);
      setNotifications(data.items);
      setTotal(data.total);
      setPage(p);
    } catch {
      message.error('Ошибка загрузки уведомлений');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleMarkRead = async (id: number) => {
    try {
      await markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
    } catch {
      message.error('Ошибка');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const result = await markAllAsRead();
      message.success(`Отмечено ${result.count} уведомлений`);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      message.error('Ошибка');
    }
  };

  return (
    <div className="notifications-module">
      <div className="admin-section-head reports-head">
        <div>
          <div className="admin-overview-kicker">Коммуникации</div>
          <h3>{title}</h3>
          <span className="badge badge--lg badge--gold badge--lead">{plaque}</span>
        </div>
        <div className="reports-toolbar">
          <Button
            icon={<ReloadOutlined />}
            className="btn-gold-secondary"
            onClick={() => fetchData(1)}
          >
            Обновить
          </Button>
          <Button
            icon={<CheckOutlined />}
            className="btn-gold"
            onClick={handleMarkAllRead}
          >
            Всё прочитано
          </Button>
        </div>
      </div>

      <Card className="admin-panel-card" bordered={false}>
        <Spin spinning={loading}>
          {notifications.length === 0 && !loading ? (
            <Empty
              className="notifications-empty"
              description={<Text className="text-titanium">Нет уведомлений</Text>}
            />
          ) : (
            <List
              className="notifications-list"
              dataSource={notifications}
              pagination={{
                current: page,
                pageSize: PAGE_SIZE,
                total,
                onChange: (p) => fetchData(p),
                showSizeChanger: false,
                size: 'small',
              }}
              renderItem={(item) => (
                <List.Item className={`notification-item${item.is_read ? ' is-read' : ' is-unread'}`}>
                  <List.Item.Meta
                    title={
                      <Space wrap size={8}>
                        <span className={`badge badge--sm tag-status ${TYPE_BADGE[item.type] || 'badge--neutral'}`}>
                          {TYPE_LABELS[item.type] || item.type}
                        </span>
                        <Text className="text-gold-bold">{item.title}</Text>
                        {!item.is_read && (
                          <Button
                            size="small"
                            className="btn-gold-secondary"
                            icon={<CheckOutlined />}
                            onClick={() => handleMarkRead(item.id)}
                          >
                            Прочитано
                          </Button>
                        )}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={2}>
                        <Text className="text-titanium">{item.message}</Text>
                        <Text className="notification-time">
                          {item.created_at ? dayjs(item.created_at).format('DD.MM.YYYY HH:mm') : ''}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
}
