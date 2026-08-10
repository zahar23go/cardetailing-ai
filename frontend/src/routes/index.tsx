/**
 * Роутинг приложения: иерархические админ-пути + редиректы со старых URL.
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from '../components/LoginPage';
import RegisterPage from '../components/RegisterPage';
import MainPage from '../components/MainPage';
import ConceptPage from '../components/ConceptPage';
import AdminLayout from '../components/AdminLayout';
import MasterDashboard from '../MasterDashboard';

import DashboardPage from '../pages/dashboard';
import AiFinancierPage from '../pages/analytics/ai-financier';
import FinancesPage from '../pages/analytics/finances';
import AnalyticsPage from '../pages/analytics/analytics';
import ReportsPage from '../pages/analytics/reports';
import RecordsPage from '../pages/upload/records';
import CalendarPage from '../pages/upload/calendar';
import UsersPage from '../pages/crm/users';
import ServicesPage from '../pages/crm/services';
import DiscountsPage from '../pages/discounts';
import NotificationsPage from '../pages/settings/notifications';
import BrandingPage from '../pages/settings/branding';
import ServiceAnalyticsPage from '../pages/analytics/service-analytics';

export interface AppUser {
  id: number;
  phone: string;
  full_name: string;
  role: 'client' | 'master' | 'admin' | 'super_admin';
}

export type AppRoutesProps = {
  isAuthenticated: boolean;
  user: AppUser | null;
  onLogin: (phone: string, password: string) => void | Promise<void>;
  onRegistered: (token: string, user: { id: number; phone: string; full_name: string; role: string }) => void;
  onLogout: () => void;
  navigateToRegister: () => void;
};

export default function AppRoutes({
  isAuthenticated,
  user,
  onLogin,
  onRegistered,
  onLogout,
  navigateToRegister,
}: AppRoutesProps) {
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';
  const isMaster = user?.role === 'master';
  const isClient = user?.role === 'client';

  const loginEl = (
    <LoginPage
      onLogin={onLogin}
      onRegister={navigateToRegister}
    />
  );

  return (
    <Routes>
      <Route path="/register" element={<RegisterPage onRegistered={onRegistered} />} />
      <Route
        path="/concept"
        element={
          <ConceptPage
            isAuthenticated={isAuthenticated}
            onLogout={onLogout}
          />
        }
      />
      <Route
        path="/main"
        element={
          <MainPage
            userName={user?.full_name?.split(' ')[0] || 'Алексей'}
            onLogout={onLogout}
          />
        }
      />

      {/* Админ-layout: оболочка + pages/* по URL */}
      <Route
        element={
          isAuthenticated && user && isAdmin ? (
            <AdminLayout user={user} onLogout={onLogout} />
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
        <Route path="dashboard" element={<DashboardPage />} />

        <Route path="analytics">
          <Route index element={<Navigate to="analytics" replace />} />
          <Route path="ai-financier" element={<AiFinancierPage />} />
          <Route path="finances" element={<FinancesPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="service-analytics" element={<ServiceAnalyticsPage />} />
        </Route>

        <Route path="upload">
          <Route index element={<Navigate to="records" replace />} />
          <Route path="records" element={<RecordsPage />} />
          <Route path="calendar" element={<CalendarPage />} />
        </Route>

        <Route path="crm">
          <Route index element={<Navigate to="users" replace />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="services" element={<ServicesPage />} />
        </Route>

        <Route path="discounts" element={<DiscountsPage />} />
        <Route path="settings/notifications" element={<NotificationsPage />} />
        <Route path="settings/branding" element={<BrandingPage />} />
      </Route>

      {/* Редиректы: старые → новые */}
      <Route path="/overview" element={<Navigate to="/dashboard" replace />} />
      <Route path="/branding" element={<Navigate to="/settings/branding" replace />} />
      <Route path="/ai-financier" element={<Navigate to="/analytics/ai-financier" replace />} />
      <Route path="/financier" element={<Navigate to="/analytics/ai-financier" replace />} />
      <Route path="/finances" element={<Navigate to="/analytics/finances" replace />} />
      <Route path="/reports" element={<Navigate to="/analytics/reports" replace />} />
      <Route path="/records" element={<Navigate to="/upload/records" replace />} />
      <Route path="/appointments" element={<Navigate to="/upload/records" replace />} />
      <Route path="/calendar" element={<Navigate to="/upload/calendar" replace />} />
      <Route path="/users" element={<Navigate to="/crm/users" replace />} />
      <Route path="/services" element={<Navigate to="/crm/services" replace />} />
      <Route path="/notifications" element={<Navigate to="/settings/notifications" replace />} />
      <Route path="/analytics/metrics" element={<Navigate to="/analytics/analytics" replace />} />
      <Route path="/settings" element={<Navigate to="/settings/notifications" replace />} />

      <Route
        path="/"
        element={
          isAuthenticated && user ? (
            isClient ? (
              <Navigate to="/concept" replace />
            ) : isAdmin ? (
              <Navigate to="/dashboard" replace />
            ) : isMaster ? (
              <MasterDashboard user={user} onLogout={onLogout} />
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
            ? <Navigate to="/dashboard" replace />
            : <Navigate to="/" replace />
        }
      />
    </Routes>
  );
}
