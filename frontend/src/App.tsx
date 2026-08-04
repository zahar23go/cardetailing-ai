import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, Outlet, useNavigate } from 'react-router-dom';
import { message } from 'antd';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import MainPage from './components/MainPage';
import BrandingPage from './components/BrandingPage';
import ConceptPage from './components/ConceptPage';
import OwnerDashboard from './OwnerDashboard';
import MasterDashboard from './MasterDashboard';

interface User {
  id: number;
  phone: string;
  full_name: string;
  role: 'client' | 'master' | 'admin' | 'super_admin';
}

const API_BASE = '';

/** Пустой outlet — контент рисует OwnerDashboard по URL */
function AdminSection() {
  return <Outlet />;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
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
      navigate('/overview');
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
      role: (newUser.role as User['role']) || 'client',
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

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';
  const isMaster = user?.role === 'master';
  const isClient = user?.role === 'client';

  const loginEl = (
    <LoginPage
      onLogin={handleLogin}
      onRegister={() => navigate('/register')}
    />
  );

  if (!authReady) {
    return null;
  }

  return (
    <Routes>
      <Route path="/register" element={<RegisterPage onRegistered={handleRegistered} />} />
      <Route
        path="/concept"
        element={
          <ConceptPage
            isAuthenticated={isAuthenticated}
            onLogout={handleLogout}
          />
        }
      />
      <Route
        path="/main"
        element={
          <MainPage
            userName={user?.full_name?.split(' ')[0] || 'Алексей'}
            onLogout={handleLogout}
          />
        }
      />

      {/* Админ-layout: один OwnerDashboard, дочерние path только для URL */}
      <Route
        element={
          isAuthenticated && user && isAdmin ? (
            <OwnerDashboard user={user} onLogout={handleLogout} />
          ) : !isAuthenticated ? (
            loginEl
          ) : isMaster ? (
            <Navigate to="/" replace />
          ) : isClient ? (
            <Navigate to="/concept" replace />
          ) : (
            loginEl
          )
        }
      >
        <Route path="overview" element={<AdminSection />} />
        <Route path="analytics/:section" element={<AdminSection />} />
        <Route path="upload/:section" element={<AdminSection />} />
        <Route path="crm/:section" element={<AdminSection />} />
        <Route path="discounts" element={<AdminSection />} />
        <Route path="settings/notifications" element={<AdminSection />} />
      </Route>

      <Route
        path="/settings/branding"
        element={
          isAuthenticated && isAdmin
            ? <BrandingPage />
            : !isAuthenticated
              ? loginEl
              : <Navigate to="/" replace />
        }
      />

      {/* Редиректы со старых путей */}
      <Route path="/branding" element={<Navigate to="/settings/branding" replace />} />
      <Route path="/financier" element={<Navigate to="/analytics/ai-financier" replace />} />
      <Route path="/finances" element={<Navigate to="/analytics/finances" replace />} />
      <Route path="/reports" element={<Navigate to="/analytics/reports" replace />} />
      <Route path="/appointments" element={<Navigate to="/upload/records" replace />} />
      <Route path="/calendar" element={<Navigate to="/upload/calendar" replace />} />
      <Route path="/users" element={<Navigate to="/crm/users" replace />} />
      <Route path="/services" element={<Navigate to="/crm/services" replace />} />
      <Route path="/notifications" element={<Navigate to="/settings/notifications" replace />} />
      <Route path="/analytics" element={<Navigate to="/analytics/metrics" replace />} />
      <Route path="/upload" element={<Navigate to="/upload/records" replace />} />
      <Route path="/crm" element={<Navigate to="/crm/users" replace />} />
      <Route path="/settings" element={<Navigate to="/settings/notifications" replace />} />

      <Route
        path="/"
        element={
          isAuthenticated && user ? (
            isClient ? (
              <Navigate to="/concept" replace />
            ) : isAdmin ? (
              <Navigate to="/overview" replace />
            ) : isMaster ? (
              <MasterDashboard user={user} onLogout={handleLogout} />
            ) : (
              loginEl
            )
          ) : (
            loginEl
          )
        }
      />

      <Route
        path="*"
        element={
          isAuthenticated && isAdmin
            ? <Navigate to="/overview" replace />
            : <Navigate to="/" replace />
        }
      />
    </Routes>
  );
}

export default App;
