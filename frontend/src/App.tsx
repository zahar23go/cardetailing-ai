import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { message } from 'antd';
import LoginPage from './components/LoginPage';
import MainPage from './components/MainPage';
import BrandingPage from './components/BrandingPage';
import OwnerDashboard from './OwnerDashboard';
import MasterDashboard from './MasterDashboard';

interface User {
  id: number;
  phone: string;
  full_name: string;
  role: 'client' | 'master' | 'admin' | 'super_admin';
}

const API_BASE = '';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();

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

  const handleLogin = async (phone: string, password: string) => {
    if (!phone.trim()) { message.warning('Введите телефон'); return; }
    if (!password.trim()) { message.warning('Введите пароль'); return; }
    try {
      const response = await fetch(`${API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, password }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        setIsAuthenticated(true);
        message.success(`👋 Добро пожаловать, ${data.user.full_name}!`);
        navigate('/main');
      } else {
        message.error(data.detail || '❌ Неверный телефон или пароль');
      }
    } catch {
      message.error('❌ Ошибка соединения с сервером');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    message.info('👋 Вы вышли из системы');
    navigate('/');
  };

  const openDemoHome = () => {
    navigate('/main');
  };

  return (
    <Routes>
      <Route path="/branding" element={<BrandingPage />} />
      <Route
        path="/main"
        element={
          <MainPage
            userName={user?.full_name?.split(' ')[0] || 'Алексей'}
            onLogout={handleLogout}
          />
        }
      />
      <Route
        path="/"
        element={
          isAuthenticated && user ? (
            user.role === 'client' ? (
              <MainPage userName={user.full_name?.split(' ')[0]} onLogout={handleLogout} />
            ) :
            user.role === 'admin' || user.role === 'super_admin' ? (
              <OwnerDashboard user={user} onLogout={handleLogout} />
            ) :
            user.role === 'master' ? (
              <MasterDashboard user={user} onLogout={handleLogout} />
            ) : (
              <LoginPage
                onLogin={handleLogin}
                onRegister={() => message.info('Регистрация')}
                onDemo={openDemoHome}
              />
            )
          ) : (
            <LoginPage
              onLogin={handleLogin}
              onRegister={() => message.info('Регистрация')}
              onDemo={openDemoHome}
            />
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
