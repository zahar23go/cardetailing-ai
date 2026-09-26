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

import OwnerOnboardingPage from '../pages/onboarding';
import DashboardPage from '../pages/dashboard';
import AiFinancierPage from '../pages/analytics/ai-financier';
import FinancesPage from '../pages/analytics/finances';
import AnalyticsPage from '../pages/analytics/analytics';
import ReportsPage from '../pages/analytics/reports';
import RecordsPage from '../pages/upload/records';
import CalendarPage from '../pages/upload/calendar';
import BoxesFloorPage from '../pages/upload/boxes';
import UsersPage from '../pages/crm/users';
import ServicesPage from '../pages/crm/services';
import DiscountsPage from '../pages/discounts';
import WarehousePage from '../pages/technology/warehouse';
import TechCardsPage from '../pages/technology/tech-cards';
import TechCardViewPage from '../pages/technology/tech-cards/view';
import InventoryPage from '../pages/technology/inventory';
import TechAnalyticsPage from '../pages/technology/analytics';
import NotificationsPage from '../pages/settings/notifications';
import BrandingPage from '../pages/settings/branding';
import TariffsPage from '../pages/settings/tariffs';
import ServiceAnalyticsPage from '../pages/analytics/service-analytics';
import ReviewsPage from '../pages/reviews';
import ClientLayout from '../pages/client/layout';
import ClientHomePage from '../pages/client/home';
import ClientBookingPage from '../pages/client/booking';
import ClientPortfolioPage from '../pages/client/portfolio';
import ClientReviewsPage from '../pages/client/reviews';
import ClientChatPage from '../pages/client/chat';
import ClientDiscountsPage from '../pages/client/discounts';
import ClientSettingsPage from '../pages/client/settings';

export interface AppUser {
  id: number;
  phone: string;
  full_name: string;
  role: 'client' | 'master' | 'admin' | 'super_admin';
  tenant_id?: string;
  enabled_modules?: string[];
  plan?: string;
  plan_label?: string;
  features?: { financier?: boolean; branding?: boolean };
  appointment_limit?: number | null;
  appointments_this_month?: number;
  tenant_name?: string;
  logo_url?: string | null;
  pwa?: {
    name: string;
    short_name: string;
    icon: string;
    theme_color: string;
    background_color: string;
    white_label: boolean;
  };
}

export type AppRoutesProps = {
  isAuthenticated: boolean;
  user: AppUser | null;
  onLogin: (phone: string, password: string) => void | Promise<void>;
  onRegistered: (token: string, user: AppUser) => void;
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

      <Route
        path="/onboarding"
        element={
          isAuthenticated && user && isAdmin ? (
            <OwnerOnboardingPage />
          ) : !isAuthenticated ? (
            loginEl
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
      <Route
        element={
          isAuthenticated && user && isAdmin ? (
            <AdminLayout user={user} onLogout={onLogout} />
          ) : !isAuthenticated ? (
            loginEl
          ) : isMaster ? (
            <Navigate to="/" replace />
          ) : isClient ? (
            <Navigate to="/client" replace />
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
          <Route path="boxes" element={<BoxesFloorPage />} />
          <Route path="calendar" element={<CalendarPage />} />
        </Route>

        <Route path="crm">
          <Route index element={<Navigate to="users" replace />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="services" element={<ServicesPage />} />
        </Route>

        <Route path="discounts" element={<DiscountsPage />} />

        <Route path="reviews" element={<ReviewsPage />} />

        <Route path="technology">
          <Route index element={<Navigate to="warehouse" replace />} />
          <Route path="warehouse" element={<WarehousePage />} />
          <Route path="tech-cards" element={<TechCardsPage />} />
          <Route path="tech-cards/:id" element={<TechCardViewPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="analytics" element={<TechAnalyticsPage />} />
        </Route>

        <Route path="settings/notifications" element={<NotificationsPage />} />
        <Route path="settings/branding" element={<BrandingPage />} />
        <Route path="settings/tariffs" element={<TariffsPage />} />
      </Route>

      <Route
        element={
          isAuthenticated && user && isClient ? (
            <ClientLayout user={user} onLogout={onLogout} />
          ) : !isAuthenticated ? (
            loginEl
          ) : (
            <Navigate to="/" replace />
          )
        }
      >
        <Route path="client" element={<ClientHomePage />} />
        <Route path="client/booking" element={<ClientBookingPage />} />
        <Route path="client/portfolio" element={<ClientPortfolioPage />} />
        <Route path="client/reviews" element={<ClientReviewsPage />} />
        <Route path="client/chat" element={<ClientChatPage />} />
        <Route path="client/discounts" element={<ClientDiscountsPage />} />
        <Route path="client/settings" element={<ClientSettingsPage />} />
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
      <Route path="/boxes" element={<Navigate to="/upload/boxes" replace />} />
      <Route path="/users" element={<Navigate to="/crm/users" replace />} />
      <Route path="/services" element={<Navigate to="/crm/services" replace />} />
      <Route path="/notifications" element={<Navigate to="/settings/notifications" replace />} />
      <Route path="/analytics/metrics" element={<Navigate to="/analytics/analytics" replace />} />
      <Route path="/settings" element={<Navigate to="/settings/notifications" replace />} />
      <Route path="/warehouse" element={<Navigate to="/technology/warehouse" replace />} />

      <Route
        path="/master/portfolio"
        element={
          isAuthenticated && user && isMaster ? (
            <MasterDashboard user={user} onLogout={onLogout} initialSection="portfolio" />
          ) : !isAuthenticated ? (
            loginEl
          ) : (
            <Navigate to="/" replace />
          )
        }
      />

      <Route
        path="/"
        element={
          isAuthenticated && user ? (
            isClient ? (
              <Navigate to="/client" replace />
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
            : isAuthenticated && isClient
              ? <Navigate to="/client" replace />
              : <Navigate to="/" replace />
        }
      />
    </Routes>
  );
}
