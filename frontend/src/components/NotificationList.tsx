/* ============================================================
   NotificationList — страница со списком уведомлений
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, List, Tag, Button, Space, Spin, Empty, message,
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

const TYPE_COLORS: Record<string, string> = {
  appointment_reminder: 'gold',
  appointment_cancelled: 'red',
  status_change: 'blue',
  promo: 'green',
  info: 'default',
};

interface NotificationListProps {
  /** Фильтр: только непрочитанные */
  unreadOnly?: boolean;
  /** Заголовок */
  title?: string;
}

export default function NotificationList({
  unreadOnly = false,
  title = 'Уведомления',
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
    <div>
      <div className="flex-space-between mb-12">
        <Text className="title-gold text-18">{title}</Text>
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(1)} className="btn-logout" />
          <Button size="small" className="btn-action-gold" onClick={handleMarkAllRead}>
            <CheckOutlined /> Всё прочитано
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {notifications.length === 0 && !loading ? (
          <Empty description={<Text className="text-titanium">Нет уведомлений</Text>} />
        ) : (
          <List
            dataSource={notifications}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: total,
              onChange: (p) => fetchData(p),
              showSizeChanger: false,
              size: 'small',
            }}
            renderItem={(item) => (
              <List.Item
                style={{
                  backgroundColor: item.is_read ? 'transparent' : 'rgba(200,169,119,0.05)',
                  borderRadius: '14px',
                  padding: '12px 16px',
                  marginBottom: '8px',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={TYPE_COLORS[item.type]} className="tag-status">
                        {TYPE_LABELS[item.type] || item.type}
                      </Tag>
                      <Text className="text-gold-bold">
                        {item.title}
                      </Text>
                      {!item.is_read && (
                        <Button
                          size="small"
                          className="btn-action-gold"
                          icon={<CheckOutlined />}
                          onClick={() => handleMarkRead(item.id)}
                        />
                      )}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={2}>
                      <Text className="text-titanium">{item.message}</Text>
                      <Text className="text-small opacity-70">
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
    </div>
  );
}
