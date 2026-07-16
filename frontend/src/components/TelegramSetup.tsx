/* ============================================================
   TelegramSetup — подключение Telegram
   ============================================================ */

import React, { useState } from 'react';
import { Typography, Button, Input, Space, message } from 'antd';
import { connectTelegram, disconnectTelegram } from '../api/notifications';
import type { NotificationSettings } from '../api/notifications';

const { Text } = Typography;

interface TelegramSetupProps {
  settings: NotificationSettings | null;
  onUpdate: () => void;
}

export default function TelegramSetup({ settings, onUpdate }: TelegramSetupProps) {
  const [code, setCode] = useState('');
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    if (!code.trim()) {
      message.warning('Введите код из Telegram');
      return;
    }
    setConnecting(true);
    try {
      await connectTelegram(code.trim());
      message.success('Telegram подключён');
      onUpdate();
      setCode('');
    } catch (e: any) {
      message.error(e.message || 'Ошибка подключения');
    }
    setConnecting(false);
  };

  const handleDisconnect = async () => {
    try {
      await disconnectTelegram();
      message.success('Telegram отключён');
      onUpdate();
    } catch {
      message.error('Ошибка отключения');
    }
  };

  const isConnected = settings?.telegram_enabled && settings?.telegram_chat_id;

  return (
    <div className="card-detail" style={{ padding: '16px', borderRadius: '14px' }}>
      <Text className="title-gold text-14 d-block mb-8">Telegram</Text>

      {isConnected ? (
        <Space direction="vertical" size="small" className="w-full">
          <Text className="text-titanium text-13">
            ✅ Telegram подключён
          </Text>
          <Button className="btn-action-danger" onClick={handleDisconnect}>
            Отключить Telegram
          </Button>
        </Space>
      ) : (
        <Space direction="vertical" size="small" className="w-full">
          <Text className="text-titanium text-13">
            Напишите боту @CarDetailingBot команду /start, затем введите код:
          </Text>
          <Space.Compact className="w-full">
            <Input
              placeholder="Код из Telegram"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onPressEnter={handleConnect}
            />
            <Button type="primary" loading={connecting} onClick={handleConnect}>
              Подключить
            </Button>
          </Space.Compact>
        </Space>
      )}
    </div>
  );
}
