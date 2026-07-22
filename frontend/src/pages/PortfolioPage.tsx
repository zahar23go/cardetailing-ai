/* ============================================================
   PortfolioPage — страница портфолио салона для клиента
   ============================================================ */

import React, { useState, useEffect, useRef } from 'react';
import {
  Typography, Spin, Card, Select, Layout, Space, message, Button, Input,
} from 'antd';
import {
  CameraOutlined, ReloadOutlined, FilterOutlined, SendOutlined, RobotOutlined,
} from '@ant-design/icons';
import { getAllPortfolio, getPortfolioServices } from '../api/photos';
import type { Photo, PortfolioService } from '../api/photos';
import Gallery from '../components/Gallery';

const { Text } = Typography;
const { Content } = Layout;
const { Option } = Select;
const API_BASE = '';

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

export default function PortfolioPage() {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [services, setServices] = useState<PortfolioService[]>([]);
  const [serviceFilter, setServiceFilter] = useState<number | undefined>(undefined);
  const [aiMessages, setAiMessages] = useState<{role: 'user' | 'ai'; text: string}[]>([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [aiMessages]);

  const fetchPortfolio = async (serviceId?: number) => {
    setLoading(true);
    try {
      const data = await getAllPortfolio(serviceId);
      setPhotos(data);
    } catch {
      message.error('Ошибка загрузки портфолио');
    }
    setLoading(false);
  };

  const fetchServices = async () => {
    try {
      const data = await getPortfolioServices();
      setServices(data);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchPortfolio(serviceFilter);
    fetchServices();
  }, [serviceFilter]);

  const sendAiMessage = async () => {
    if (!aiInput.trim()) return;
    const question = aiInput.trim();
    setAiMessages((prev) => [...prev, { role: 'user', text: question }]);
    setAiInput('');
    setAiLoading(true);
    try {
      const context = photos.length > 0
        ? `В портфолио салона ${photos.length} работ. Доступные услуги: ${services.map(s => s.service_name).join(', ')}.`
        : 'Портфолио пока пусто.';
      const data = await apiFetch<{response: string}>('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ message: `Контекст: ${context}\n\nВопрос клиента: ${question}` }),
      });
      setAiMessages((prev) => [...prev, { role: 'ai', text: data.response }]);
    } catch {
      setAiMessages((prev) => [...prev, { role: 'ai', text: 'Извините, ошибка связи. Попробуйте позже.' }]);
    }
    setAiLoading(false);
  };

  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#0B0D10' }}>
      <Content className="content-command">
        <Space direction="vertical" size="large" className="w-full">
          {/* Header */}
          <div className="flex-space-between">
            <Space>
              <CameraOutlined className="text-gold" style={{ fontSize: '24px' }} />
              <Text className="title-gold" style={{ fontSize: '22px', fontWeight: 700 }}>
                Портфолио салона
              </Text>
            </Space>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => fetchPortfolio(serviceFilter)}
              type="text"
              className="btn-logout"
            />
          </div>

          <Text className="text-titanium text-14">
            Наши работы — лучший показатель качества. Смотрите фото до и после,
            выбирайте услугу и мастера.
          </Text>

          {/* Filter by service */}
          {services.length > 0 && (
            <div>
              <Space size="small">
                <FilterOutlined className="text-titanium" />
                <Select
                  size="small"
                  placeholder="Все услуги"
                  value={serviceFilter}
                  onChange={setServiceFilter}
                  allowClear
                  style={{ minWidth: 200 }}
                  onClear={() => setServiceFilter(undefined)}
                >
                  {services.map((s) => (
                    <Option key={s.service_id} value={s.service_id}>
                      {s.service_name} ({s.photo_count})
                    </Option>
                  ))}
                </Select>
              </Space>
            </div>
          )}

          {/* Portfolio stats */}
          {!loading && photos.length > 0 && (
            <div>
              <Text className="text-titanium text-13">
                Показано работ: <Text className="text-white-bold">{photos.length}</Text>
              </Text>
            </div>
          )}

          {/* Gallery */}
          <Spin spinning={loading}>
            {photos.length === 0 && !loading ? (
              <Card className="card-luxury">
                <Text className="text-titanium d-block text-center">
                  {serviceFilter
                    ? 'Нет работ для выбранной услуги'
                    : 'Портфолио салона пока пусто'}
                </Text>
              </Card>
            ) : (
              <Gallery
                photos={photos}
                readonly={true}
                columns={3}
              />
            )}
          </Spin>

          {/* AI Consultant */}
          <Card className="card-luxury">
            <div className="flex-space-between mb-12">
              <Space>
                <RobotOutlined className="text-gold" style={{ fontSize: '18px' }} />
                <Text className="title-gold text-16">AI-консультант</Text>
              </Space>
            </div>
            <Text className="text-titanium text-13 d-block mb-12">
              Спросите о наших работах, услугах или получите рекомендацию.
            </Text>
            <div style={{ maxHeight: 200, overflowY: 'auto', marginBottom: 12 }}>
              {aiMessages.map((m, i) => (
                <div key={i} className="mb-8" style={{
                  textAlign: m.role === 'user' ? 'right' : 'left',
                }}>
                  <Text className={m.role === 'user' ? 'text-titanium text-13' : 'text-white text-13'}
                    style={{
                      display: 'inline-block',
                      padding: '6px 12px',
                      borderRadius: 12,
                      background: m.role === 'user' ? 'rgba(200,169,119,0.15)' : 'rgba(255,255,255,0.04)',
                      maxWidth: '90%',
                    }}>
                    {m.text}
                  </Text>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                className="input-luxury"
                placeholder="Ваш вопрос..."
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                onPressEnter={sendAiMessage}
                disabled={aiLoading}
              />
              <Button
                className="btn-gold"
                icon={<SendOutlined />}
                onClick={sendAiMessage}
                loading={aiLoading}
              />
            </Space.Compact>
          </Card>
        </Space>
      </Content>
    </Layout>
  );
}
