/* ============================================================
   HistoryPage — страница истории изменений записи
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Layout, Select, Space, message, Button,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { getHistory } from '../api/history';
import type { HistoryEntry } from '../api/history';
import HistoryTimeline from '../components/HistoryTimeline';

const { Text } = Typography;
const { Content } = Layout;
const { Option } = Select;

const PAGE_SIZE = 50;

interface HistoryPageProps {
  appointmentId: number;
  onBack?: () => void;
}

export default function HistoryPage({ appointmentId, onBack }: HistoryPageProps) {
  const [items, setItems] = useState<HistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filterType, setFilterType] = useState<string>('');

  const fetchData = async (p = page, type = filterType) => {
    setLoading(true);
    try {
      const skip = (p - 1) * PAGE_SIZE;
      const data = await getHistory(appointmentId, skip, PAGE_SIZE, type || undefined);
      setItems(data.items);
      setTotal(data.total);
      setPage(p);
    } catch {
      message.error('Ошибка загрузки истории');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData(1, filterType);
  }, [appointmentId, filterType]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#0B0D10' }}>
      <Content className="content-command">
        <Space direction="vertical" size="large" className="w-full">
          <div className="flex-space-between">
            <Space>
              {onBack && (
                <Button
                  icon={<ArrowLeftOutlined />}
                  onClick={onBack}
                  className="btn-logout"
                />
              )}
              <Text className="title-gold text-18">История изменений</Text>
              <Text className="text-titanium text-13">Всего: {total}</Text>
            </Space>

            <Select
              value={filterType}
              onChange={(v) => setFilterType(v)}
              style={{ width: 160 }}
              size="small"
              placeholder="Тип изменения"
            >
              <Option value="">Все</Option>
              <Option value="create">Создание</Option>
              <Option value="update">Изменение</Option>
              <Option value="cancel">Отмена</Option>
              <Option value="move">Перенос</Option>
              <Option value="status_change">Статус</Option>
            </Select>
          </div>

          <HistoryTimeline items={items} />

          {totalPages > 1 && (
            <div className="text-center">
              <Space>
                <Button
                  disabled={page <= 1}
                  onClick={() => fetchData(page - 1)}
                  className="btn-logout"
                >
                  ← Назад
                </Button>
                <Text className="text-titanium text-13">
                  {page} / {totalPages}
                </Text>
                <Button
                  disabled={page >= totalPages}
                  onClick={() => fetchData(page + 1)}
                  className="btn-logout"
                >
                  Вперёд →
                </Button>
              </Space>
            </div>
          )}
        </Space>
      </Content>
    </Layout>
  );
}
