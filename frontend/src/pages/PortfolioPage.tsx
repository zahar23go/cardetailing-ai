/* ============================================================
   PortfolioPage — страница портфолио всех мастеров
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Spin, Card, Select, Layout, Space, message,
} from 'antd';
import {
  ToolOutlined, ReloadOutlined, UserOutlined,
} from '@ant-design/icons';
import { getPhotos } from '../api/photos';
import type { Photo } from '../api/photos';
import Gallery from '../components/Gallery';

const { Text } = Typography;
const { Content } = Layout;
const { Option } = Select;

// Временные данные — в реальном приложении получать список мастеров из API
const MASTERS: { id: number; name: string }[] = [];

interface PortfolioPageProps {
  masters?: { id: number; name: string }[];
}

export default function PortfolioPage({ masters = MASTERS }: PortfolioPageProps) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedMaster, setSelectedMaster] = useState<number | null>(
    masters.length > 0 ? masters[0].id : null,
  );

  useEffect(() => {
    if (selectedMaster) {
      fetchPortfolio(selectedMaster);
    }
  }, [selectedMaster]);

  const fetchPortfolio = async (masterId: number) => {
    setLoading(true);
    try {
      const data = await getPhotos('portfolio', masterId);
      setPhotos(data);
    } catch {
      message.error('Ошибка загрузки портфолио');
    }
    setLoading(false);
  };

  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#0B0D10' }}>
      <Content className="content-command">
        <Space direction="vertical" size="large" className="w-full">
          <div className="flex-space-between">
            <Text className="title-gold text-24">Портфолио мастеров</Text>
          </div>

          <Spin spinning={loading}>
            {photos.length === 0 && !loading ? (
              <Card className="card-luxury">
                <Text className="text-titanium d-block text-center">
                  Нет фотографий в портфолио
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
        </Space>
      </Content>
    </Layout>
  );
}
