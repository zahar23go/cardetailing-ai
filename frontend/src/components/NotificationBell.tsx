/* ============================================================
   NotificationBell — иконка с бейджем
   ============================================================ */

import React, { useState, useEffect, useRef } from 'react';
import { Badge, Popover, List, Button, Typography, Space, Empty } from 'antd';
import { BellOutlined, CheckOutlined } from '@ant-design/icons';
import { getUnreadCount, markAllAsRead, getNotifications, markAsRead } from '../api/notifications';
import type { Notification } from '../api/notifications';
import dayjs from 'dayjs';

const { Text } = Typography;

const TYPE_ICONS: Record<string, string> = {
  appointment_reminder: '📅',
  appointment_cancelled: '❌',
  status_change: '🔄',
  promo: '🎉',
  info: 'ℹ️',
};

export default function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const prevCount = useRef(0);

  const fetchUnread = async () => {
    try {
      const data = await getUnreadCount();
      setUnread(data.count);
    } catch {
      // ignore
    }
  };

  const fetchList = async () => {
    setLoading(true);
    try {
      const data = await getNotifications(0, 10, true);
      setNotifications(data.items);
    } catch {
      // ignore
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchUnread();
    // Poll every 30 seconds
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenChange = (visible: boolean) => {
    setOpen(visible);
    if (visible) fetchList();
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
    setUnread(0);
    setNotifications([]);
  };

  const handleMarkRead = async (id: number) => {
    await markAsRead(id);
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    setUnread((prev) => Math.max(0, prev - 1));
  };

  const content = (
    <div style={{ width: '320px', maxHeight: '400px', overflowY: 'auto' }}>
      <div className="flex-space-between" style={{ marginBottom: '8px' }}>
        <Text className="text-white-bold">Уведомления</Text>
        {unread > 0 && (
          <Button size="small" className="btn-action-gold" onClick={handleMarkAllRead}>
            <CheckOutlined /> Всё прочитано
          </Button>
        )}
      </div>

      {notifications.length === 0 ? (
        <Empty description={<Text className="text-titanium text-12">Нет новых уведомлений</Text>} />
      ) : (
        <List
          dataSource={notifications.slice(0, 5)}
          renderItem={(item) => (
            <List.Item
              style={{ padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.06)', cursor: 'pointer' }}
              onClick={() => handleMarkRead(item.id)}
            >
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Space>
                  <Text className="text-small">{TYPE_ICONS[item.type] || 'ℹ️'}</Text>
                  <Text className="text-white-bold text-13">{item.title}</Text>
                </Space>
                <Text className="text-titanium text-12">{item.message}</Text>
                <Text className="text-titanium text-11 opacity-70">
                  {item.created_at ? dayjs(item.created_at).format('DD.MM HH:mm') : ''}
                </Text>
              </Space>
            </List.Item>
          )}
        />
      )}
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={handleOpenChange}
      placement="bottomRight"
    >
      <Badge count={unread} size="small" offset={[-5, 5]}>
        <BellOutlined style={{ fontSize: '18px', color: '#AAB2BF', cursor: 'pointer' }} />
      </Badge>
    </Popover>
  );
}
