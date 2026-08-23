/**
 * Оболочка клиентского кабинета: шапка, сайдбар, нижнее меню.
 */
import React from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Button, Layout, Space, Typography } from 'antd';
import {
  CalendarOutlined, CameraOutlined, CommentOutlined, GiftOutlined,
  HomeOutlined, LogoutOutlined, UserOutlined,
} from '@ant-design/icons';
import { CLIENT_NAV, clientTabFromPath } from './navConfig';

const { Header, Content, Sider } = Layout;
const { Text } = Typography;

const ICONS: Record<string, React.ReactNode> = {
  home: <HomeOutlined />,
  calendar: <CalendarOutlined />,
  camera: <CameraOutlined />,
  chat: <CommentOutlined />,
  gift: <GiftOutlined />,
  user: <UserOutlined />,
};

type Props = {
  user: { id: number; phone: string; full_name: string; role: string };
  onLogout: () => void;
};

export default function ClientLayout({ user, onLogout }: Props) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const active = clientTabFromPath(pathname);

  return (
    <Layout className="client-layout client-app">
      <Header className="header-mobile client-header">
        <Space size="small" align="center">
          <img
            src="/images/logo-formula-sport.png"
            alt=""
            className="client-header-logo"
          />
          <Text className="client-header-title">CAR DETAILING AI</Text>
        </Space>
        <span className="client-header-badge">Кабинет</span>
      </Header>

      <Header className="header-desktop client-header">
        <Space className="client-header-brand" size="middle" align="center">
          <img
            src="/images/logo-formula-sport.png"
            alt=""
            className="client-header-logo"
          />
          <Text className="client-header-title">CAR DETAILING AI</Text>
          <span className="client-header-badge">Кабинет</span>
        </Space>
        <Space size="middle" className="client-header-actions" wrap>
          <span className="client-header-user">
            <UserOutlined />
            <span>{user.full_name}</span>
          </span>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={onLogout}
            className="client-header-btn client-header-btn-logout"
          >
            Выйти
          </Button>
        </Space>
      </Header>

      <Layout className="client-body-layout">
        <Sider
          className="sidebar client-sidebar"
          breakpoint="md"
          collapsedWidth={0}
          width={228}
          trigger={null}
        >
          {CLIENT_NAV.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`sidebar-item${active === item.key ? ' active' : ''}`}
              onClick={() => navigate(item.path)}
            >
              <span className="sidebar-icon">{ICONS[item.icon]}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </Sider>

        <Content className="client-content">
          <div className="client-app-inner">
            <Outlet />
          </div>
        </Content>
      </Layout>

      <div className="bottom-nav">
        {CLIENT_NAV.map((item) => (
          <button
            key={item.key}
            className={`bottom-nav-item${active === item.key ? ' active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            <span className="bottom-nav-icon">{ICONS[item.icon]}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        ))}
      </div>
    </Layout>
  );
}
