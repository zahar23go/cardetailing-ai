/* ============================================================
   NotificationSettings — настройки уведомлений
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Card, Switch, InputNumber, Button, Space, message, Spin,
} from 'antd';
import { getNotificationSettings, updateNotificationSettings } from '../api/notifications';
import type { NotificationSettings as SettingsType } from '../api/notifications';
import TelegramSetup from './TelegramSetup';

const { Text } = Typography;

export default function NotificationSettingsPage() {
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await getNotificationSettings();
      setSettings(data);
    } catch {
      message.error('Ошибка загрузки настроек');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleToggle = async (key: keyof SettingsType, value: boolean) => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await updateNotificationSettings({ [key]: value });
      setSettings(updated);
    } catch {
      message.error('Ошибка сохранения');
    }
    setSaving(false);
  };

  const handleHoursChange = async (value: number | null) => {
    if (!settings || !value) return;
    setSaving(true);
    try {
      const updated = await updateNotificationSettings({ remind_hours_before: value });
      setSettings(updated);
    } catch {
      message.error('Ошибка сохранения');
    }
    setSaving(false);
  };

  if (loading) {
    return <Spin />;
  }

  return (
    <Card className="card-luxury">
      <Text className="title-gold text-16 d-block mb-8">Настройки уведомлений</Text>

      <Space direction="vertical" size="middle" className="w-full">
        <div className="flex-space-between">
          <Text className="text-white">SMS-уведомления</Text>
          <Switch
            checked={settings?.sms_enabled || false}
            onChange={(v) => handleToggle('sms_enabled', v)}
          />
        </div>

        <div className="flex-space-between">
          <Text className="text-white">Напоминания о записи</Text>
          <Switch
            checked={settings?.notify_appointment_reminder || false}
            onChange={(v) => handleToggle('notify_appointment_reminder', v)}
          />
        </div>

        <div className="flex-space-between">
          <Text className="text-white">Изменение статуса</Text>
          <Switch
            checked={settings?.notify_status_change || false}
            onChange={(v) => handleToggle('notify_status_change', v)}
          />
        </div>

        <div className="flex-space-between">
          <Text className="text-white">Акции и новости</Text>
          <Switch
            checked={settings?.notify_promo || false}
            onChange={(v) => handleToggle('notify_promo', v)}
          />
        </div>

        <div className="flex-space-between">
          <Text className="text-white">Напоминать за (часов)</Text>
          <InputNumber
            min={1}
            max={168}
            value={settings?.remind_hours_before || 24}
            onChange={handleHoursChange}
            size="small"
          />
        </div>

        <TelegramSetup settings={settings} onUpdate={fetchSettings} />
      </Space>
    </Card>
  );
}
