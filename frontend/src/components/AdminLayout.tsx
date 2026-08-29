/**
 * AdminLayout — оболочка админки: хедер, сайдбар, bottom nav, <Outlet />.
 * Страницы живут в pages/*; общего state нет.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { Typography, Space, Layout } from 'antd';
import { Button } from '../components/ui';
import {
  DollarOutlined,
  TeamOutlined,
  LogoutOutlined,
  HomeOutlined,
  FileTextOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import NotificationBell from './NotificationBell';
import Sidebar from './Sidebar';
import ModuleGate from '../ModuleGate';
import { pathFromTab, tabFromPath } from '../admin/navConfig';
import { usePlanFeatures } from '../ModulesContext';

const { Text } = Typography;
const { Header, Content, Sider } = Layout;

interface AdminLayoutProps {
  user: {
    id: number;
    phone: string;
    full_name: string;
    role: string;
    pwa?: { name: string; icon: string; white_label: boolean };
  };
  onLogout: () => void;
}

export default function AdminLayout({ user, onLogout }: AdminLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTabState] = useState('overview');
  const features = usePlanFeatures();
  const showBranding = features?.branding !== false;
  const brandName = user.pwa?.white_label && user.pwa.name ? user.pwa.name : 'CAR DETAILING AI';
  const brandIcon = user.pwa?.icon || '/images/logo-formula-sport.png';

  useEffect(() => {
    const tab = tabFromPath(location.pathname);
    if (tab) setActiveTabState(tab);
  }, [location.pathname]);

  const setActiveTab = (key: string) => {
    const path = pathFromTab(key);
    if (path) {
      navigate(path);
      setActiveTabState(key);
    } else {
      setActiveTabState(key);
    }
  };

  const bottomNavItems = [
    { key: 'overview', icon: <HomeOutlined />, label: 'Обзор' },
    { key: 'appointments', icon: <FileTextOutlined />, label: 'Записи' },
    { key: 'services', icon: <SettingOutlined />, label: 'Услуги' },
    { key: 'finances', icon: <DollarOutlined />, label: 'Финансы' },
    { key: 'users', icon: <TeamOutlined />, label: 'Люди' },
  ];

  return (
    <Layout className="admin-layout client-layout">
      <Header className="header-mobile admin-header-mobile">
        <img src={brandIcon} alt="" className="client-header-logo" />
        <Text className="admin-header-title">{brandName}</Text>
        <span className="admin-header-badge">Command Center</span>
      </Header>

      <Header className="header-desktop admin-header">
        <Space className="admin-header-brand" size="middle" align="center">
          <img src={brandIcon} alt="" className="client-header-logo" />
          <Text className="admin-header-title">{brandName}</Text>
          <span className="admin-header-badge">Command Center</span>
        </Space>
        <Space size="middle" className="admin-header-actions" wrap>
          {showBranding && (
            <Button
              type="text"
              className="admin-header-btn"
              onClick={() => navigate('/settings/branding')}
            >
              Брендинг
            </Button>
          )}
          <span className="admin-header-user">
            <span>{user.full_name}</span>
          </span>
          <NotificationBell />
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={onLogout}
            className="admin-header-btn admin-header-btn-logout"
          >
            Выйти
          </Button>
        </Space>
      </Header>

      <Layout className="admin-body-layout">
        <Sider
          className="sidebar admin-sidebar"
          breakpoint="md"
          collapsedWidth={0}
          width={228}
          trigger={null}
        >
          <Sidebar />
        </Sider>

        <Content className="client-content admin-content">
          <ModuleGate>
            <Outlet />
          </ModuleGate>
        </Content>
      </Layout>

      <div className="bottom-nav">
        {bottomNavItems.map((item) => (
          <button
            key={item.key}
            className={`bottom-nav-item${activeTab === item.key ? ' active' : ''}`}
            onClick={() => setActiveTab(item.key)}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        ))}
      </div>
    </Layout>
  );
}
