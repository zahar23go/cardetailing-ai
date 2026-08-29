import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import AppRoutes, { type AppUser } from './routes';
import { EnabledModulesProvider } from './ModulesContext';
import { PLAN_UPDATED_EVENT } from './pages/settings/tariffs';
import PwaInstallBanner from './PwaInstallBanner';
import { applyPwaBrand, hidePwaSplash, type PwaBrand } from './pwa';

const API_BASE = '';

function userFromMe(data: Record<string, unknown>): AppUser {
  return {
    id: data.id as number,
    phone: String(data.phone || ''),
    full_name: String(data.full_name || ''),
    role: (data.role as AppUser['role']) || 'client',
    tenant_id: data.tenant_id ? String(data.tenant_id) : undefined,
    enabled_modules: (data.enabled_modules as string[]) || (data.modules as string[]),
    plan: data.plan as string | undefined,
    plan_label: data.plan_label as string | undefined,
    features: data.features as AppUser['features'],
    appointment_limit: (data.appointment_limit as number | null | undefined) ?? null,
    appointments_this_month: data.appointments_this_month as number | undefined,
    tenant_name: data.tenant_name as string | undefined,
    logo_url: data.logo_url as string | undefined,
    pwa: data.pwa as PwaBrand | undefined,
  };
}

function userFromLogin(data: {
  user: { id: number; phone: string; full_name: string; role: string };
  enabled_modules?: string[];
  plan?: string;
  plan_label?: string;
  features?: AppUser['features'];
  appointment_limit?: number | null;
  appointments_this_month?: number;
  tenant_name?: string;
  logo_url?: string | null;
  pwa?: PwaBrand;
}): AppUser {
  return {
    ...data.user,
    role: (data.user.role as AppUser['role']) || 'client',
    enabled_modules: data.enabled_modules,
    plan: data.plan,
    plan_label: data.plan_label,
    features: data.features,
    appointment_limit: data.appointment_limit,
    appointments_this_month: data.appointments_this_month,
    tenant_name: data.tenant_name,
    logo_url: data.logo_url,
    pwa: data.pwa,
  };
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AppUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setAuthReady(true);
      return;
    }
    const timer = window.setTimeout(() => setAuthReady(true), 4000);
    fetchUser(token).finally(() => {
      window.clearTimeout(timer);
      setAuthReady(true);
    });
  }, []);

  useEffect(() => {
    const onPlan = () => {
      const token = localStorage.getItem('token');
      if (token) fetchUser(token);
    };
    window.addEventListener(PLAN_UPDATED_EVENT, onPlan);
    return () => window.removeEventListener(PLAN_UPDATED_EVENT, onPlan);
  }, []);

  useEffect(() => {
    if (authReady) hidePwaSplash();
  }, [authReady]);

  useEffect(() => {
    applyPwaBrand(user?.pwa, user?.tenant_id);
  }, [user?.pwa, user?.tenant_id]);

  const fetchUser = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUser(userFromMe(data));
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
    navigate('/client');
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
        setUser(userFromLogin(data));
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

  const handleRegistered = (_token: string, newUser: AppUser) => {
    setUser({
      ...newUser,
      role: newUser.role || 'client',
    });
    setIsAuthenticated(true);
    message.success(`Аккаунт создан. Добро пожаловать, ${newUser.full_name}!`);
    navigate('/client');
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
    <EnabledModulesProvider
      modules={user?.enabled_modules}
      features={user?.features}
      plan={user?.plan}
    >
      <AppRoutes
        isAuthenticated={isAuthenticated}
        user={user}
        onLogin={handleLogin}
        onRegistered={handleRegistered}
        onLogout={handleLogout}
        navigateToRegister={() => navigate('/register')}
      />
      {isAuthenticated ? <PwaInstallBanner /> : null}
    </EnabledModulesProvider>
  );
}

export default App;
