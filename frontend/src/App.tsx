import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, Card, Input, Button, message, Tabs,
} from 'antd';
import {
  UserOutlined, LockOutlined, PhoneOutlined, CarOutlined,
  CrownOutlined, ToolOutlined,
} from '@ant-design/icons';
import OwnerDashboard from './OwnerDashboard';
import MasterDashboard from './MasterDashboard';
import ClientDashboard from './ClientDashboard';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

/* ============================================================
   TYPES
   ============================================================ */
interface User {
  id: number;
  phone: string;
  full_name: string;
  role: 'client' | 'master' | 'admin' | 'super_admin';
}

/* ============================================================
   HELPERS
   ============================================================ */
const API_BASE = '';

/* ============================================================
   MAIN APP COMPONENT
   ============================================================ */
function App() {
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  const [registerPhone, setRegisterPhone] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerName, setRegisterName] = useState('');

  const [loginPhone, setLoginPhone] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) fetchUser(token);
  }, []);

  const fetchUser = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUser(data);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('token');
      }
    } catch {
      localStorage.removeItem('token');
    }
  };

  const handleRegister = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: registerPhone, password: registerPassword, full_name: registerName }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        setIsAuthenticated(true);
        message.success(`👋 Добро пожаловать, ${data.user.full_name}!`);
        setRegisterPhone('');
        setRegisterPassword('');
        setRegisterName('');
      } else {
        message.error(data.detail || 'Ошибка регистрации');
      }
    } catch {
      message.error('❌ Ошибка соединения с сервером');
    }
    setLoading(false);
  };

  const handleLogin = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: loginPhone, password: loginPassword }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        setIsAuthenticated(true);
        message.success(`👋 Добро пожаловать, ${data.user.full_name}!`);
      } else {
        message.error(data.detail || '❌ Неверный телефон или пароль');
      }
    } catch {
      message.error('❌ Ошибка соединения с сервером');
    }
    setLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    message.info('👋 Вы вышли из системы');
  };

  // ============================================================
  // AUTHENTICATED
  // ============================================================
  if (isAuthenticated && user) {
    if (user.role === 'client') {
      return <ClientDashboard user={user} onLogout={handleLogout} />;
    }

    // Master / Admin / Super Admin
    if (user.role === 'admin' || user.role === 'super_admin') {
      return <OwnerDashboard user={user} onLogout={handleLogout} />;
    }

    // Master
    if (user.role === 'master') {
      return <MasterDashboard user={user} onLogout={handleLogout} />;
    }
  }

  // ============================================================
  // NOT AUTHENTICATED — Login / Register
  // ============================================================
  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      minHeight: '100vh', backgroundColor: '#0B0D10', padding: '16px',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }} style={{ maxWidth: '400px', width: '100%' }}
      >
        <Card style={{
          backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '24px', padding: '24px 20px', boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
        }}>
          <div style={{ textAlign: 'center', marginBottom: '4px' }}>
            <CarOutlined style={{ fontSize: '36px', color: '#C8A977' }} />
          </div>
          <Title level={1} style={{ color: '#C8A977', textAlign: 'center', marginBottom: '2px', fontSize: '26px', fontWeight: 700 }}>
            CarDetailing AI
          </Title>
          <Text style={{ color: '#AAB2BF', display: 'block', textAlign: 'center', marginBottom: '20px', fontSize: '13px' }}>
            🚀 Luxury Automotive Command Center
          </Text>

          <Tabs activeKey={activeTab} onChange={setActiveTab} centered style={{ marginBottom: '16px' }}
            tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
          >
            <TabPane tab={<span style={{ color: activeTab === 'login' ? '#C8A977' : '#AAB2BF', fontWeight: 500 }}>Вход</span>} key="login">
              <Input size="large" placeholder="Телефон (+7XXXXXXXXXX)" prefix={<PhoneOutlined style={{ color: '#AAB2BF' }} />}
                value={loginPhone} onChange={(e) => setLoginPhone(e.target.value)}
                style={{ marginBottom: '12px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Input.Password size="large" placeholder="Пароль" prefix={<LockOutlined style={{ color: '#AAB2BF' }} />}
                value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} onPressEnter={handleLogin}
                style={{ marginBottom: '16px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Button type="primary" size="large" onClick={handleLogin} loading={loading}
                style={{ width: '100%', borderRadius: '20px', height: '46px', backgroundColor: '#C8A977', borderColor: '#C8A977', color: '#0B0D10', fontWeight: 600, fontSize: '15px', boxShadow: '0 20px 40px rgba(200,169,119,0.15)' }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#D5B98D'; e.currentTarget.style.boxShadow = '0 20px 50px rgba(200,169,119,0.25)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 20px 40px rgba(200,169,119,0.15)'; }}
              >▶ Войти</Button>
            </TabPane>

            <TabPane tab={<span style={{ color: activeTab === 'register' ? '#C8A977' : '#AAB2BF', fontWeight: 500 }}>Регистрация</span>} key="register">
              <Input size="large" placeholder="Полное имя" prefix={<UserOutlined style={{ color: '#AAB2BF' }} />}
                value={registerName} onChange={(e) => setRegisterName(e.target.value)}
                style={{ marginBottom: '12px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Input size="large" placeholder="Телефон (+7XXXXXXXXXX)" prefix={<PhoneOutlined style={{ color: '#AAB2BF' }} />}
                value={registerPhone} onChange={(e) => setRegisterPhone(e.target.value)}
                style={{ marginBottom: '12px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Input.Password size="large" placeholder="Пароль" prefix={<LockOutlined style={{ color: '#AAB2BF' }} />}
                value={registerPassword} onChange={(e) => setRegisterPassword(e.target.value)}
                style={{ marginBottom: '16px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />

              <div style={{ marginBottom: '14px' }}>
                <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block', marginBottom: '8px' }}>Вы получите роль:</Text>
                <div className="role-selector">
                  <div className="role-btn role-btn-active">👤 Клиент</div>
                  <div className="role-btn" style={{ cursor: 'default' }}>🔧 Мастер</div>
                  <div className="role-btn" style={{ cursor: 'default' }}>👑 Владелец</div>
                </div>
                <Text style={{ color: '#AAB2BF', fontSize: '11px', display: 'block', marginTop: '6px', opacity: 0.6 }}>Роль назначается администратором</Text>
              </div>

              <Button type="primary" size="large" onClick={handleRegister} loading={loading}
                style={{ width: '100%', borderRadius: '20px', height: '46px', backgroundColor: '#C8A977', borderColor: '#C8A977', color: '#0B0D10', fontWeight: 600, fontSize: '15px', boxShadow: '0 20px 40px rgba(200,169,119,0.15)' }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#D5B98D'; e.currentTarget.style.boxShadow = '0 20px 50px rgba(200,169,119,0.25)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 20px 40px rgba(200,169,119,0.15)'; }}
              >🚀 Зарегистрироваться</Button>
            </TabPane>
          </Tabs>

          <div style={{ marginTop: '16px', display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap', padding: '12px', backgroundColor: '#1A1E23', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.03)' }}>
            <span style={{ color: '#AAB2BF', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}><UserOutlined style={{ color: '#C8A977', fontSize: '11px' }} /> Клиент</span>
            <span style={{ color: '#AAB2BF', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}><ToolOutlined style={{ color: '#C8A977', fontSize: '11px' }} /> Мастер</span>
            <span style={{ color: '#AAB2BF', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}><CrownOutlined style={{ color: '#C8A977', fontSize: '11px' }} /> Владелец</span>
          </div>

          <div style={{ marginTop: '12px', textAlign: 'center' }}>
            <Text style={{ color: '#AAB2BF', fontSize: '10px', opacity: 0.5, letterSpacing: '0.5px' }}>
              CarDetailing AI v1.0 — AI-управляющий автомойкой
            </Text>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}

export default App;
