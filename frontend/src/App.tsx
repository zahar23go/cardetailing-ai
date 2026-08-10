import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import AppRoutes, { type AppUser } from './routes';

const API_BASE = '';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AppUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchUser(token).finally(() => setAuthReady(true));
    } else {
      setAuthReady(true);
    }
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

  const goAfterAuth = (role?: string) => {
    if (role === 'admin' || role === 'super_admin') {
      navigate('/dashboard');
      return;
    }
    if (role === 'master') {
      navigate('/');
      return;
    }
    navigate('/concept');
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
        goAfterAuth(data.user?.role);
      } else {
        message.error(data.detail || '❌ Неверный телефон или пароль');
      }
    } catch {
      message.error('❌ Ошибка соединения с сервером');
    }
  };

  const handleRegistered = (_token: string, newUser: { id: number; phone: string; full_name: string; role: string }) => {
    setUser({
      ...newUser,
      role: (newUser.role as AppUser['role']) || 'client',
    });
    setIsAuthenticated(true);
    message.success(`Аккаунт создан. Добро пожаловать, ${newUser.full_name}!`);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    message.info('👋 Вы вышли из системы');
    navigate('/');
  };

  if (!authReady) {
    return null;
  }

  return (
    <AppRoutes
      isAuthenticated={isAuthenticated}
      user={user}
      onLogin={handleLogin}
      onRegistered={handleRegistered}
      onLogout={handleLogout}
      navigateToRegister={() => navigate('/register')}
    />
  );
}

export default App;
