/**
 * Уведомления — /settings/notifications
 * Пример переноса с локальными вложенными табами (список / настройки).
 */
import { Tabs } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import NotificationList from '../../../components/NotificationList';
import NotificationSettings from '../../../components/NotificationSettings';

export default function NotificationsPage() {
  return (
    <Tabs
      className="notifications-tabs"
      size="large"
      items={[
        {
          key: 'list',
          label: (
            <span>
              <BellOutlined /> Список уведомлений
            </span>
          ),
          children: <NotificationList title="Все уведомления" />,
        },
        {
          key: 'settings',
          label: <span>Настройки</span>,
          children: <NotificationSettings />,
        },
      ]}
    />
  );
}
