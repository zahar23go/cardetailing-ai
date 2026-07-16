/* ============================================================
   HistoryDrawer — боковая панель с историей изменений
   ============================================================ */

import React, { useState, useEffect } from 'react';
import { Drawer, Button, Typography, Spin, message, Space } from 'antd';
import { HistoryOutlined, ReloadOutlined } from '@ant-design/icons';
import { getHistory } from '../api/history';
import type { HistoryEntry } from '../api/history';
import HistoryTimeline from './HistoryTimeline';

const { Text } = Typography;

interface HistoryDrawerProps {
  appointmentId: number;
  trigger?: React.ReactNode;
}

export default function HistoryDrawer({ appointmentId, trigger }: HistoryDrawerProps) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<HistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await getHistory(appointmentId, 0, 100);
      setItems(data.items);
      setTotal(data.total);
    } catch {
      message.error('Ошибка загрузки истории');
    }
    setLoading(false);
  };

  useEffect(() => {
    if (open) fetchHistory();
  }, [open, appointmentId]);

  return (
    <>
      {trigger ? (
        <span onClick={() => setOpen(true)}>{trigger}</span>
      ) : (
        <Button
          size="small"
          className="btn-action-gold"
          icon={<HistoryOutlined />}
          onClick={() => setOpen(true)}
        >
          История
        </Button>
      )}

      <Drawer
        title={
          <Space>
            <HistoryOutlined />
            <Text className="text-white">История изменений</Text>
            <Text className="text-titanium text-12">({total})</Text>
          </Space>
        }
        placement="right"
        width={400}
        onClose={() => setOpen(false)}
        open={open}
        className="modal-command"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchHistory} size="small" className="btn-logout" />
        }
      >
        <Spin spinning={loading}>
          <HistoryTimeline items={items} />
        </Spin>
      </Drawer>
    </>
  );
}
