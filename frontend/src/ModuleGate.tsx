import React from 'react';
import { useLocation } from 'react-router-dom';
import { isPathEnabled } from './modules';
import { useEnabledModules, usePlanFeatures } from './ModulesContext';

/** Заглушка, если маршрут выключен тарифом. */
export default function ModuleGate({ children }: { children: React.ReactNode }) {
  const enabled = useEnabledModules();
  const features = usePlanFeatures();
  const { pathname } = useLocation();
  if (!isPathEnabled(enabled, pathname, features)) {
    return (
      <div className="admin-section-head" style={{ padding: 24 }}>
        <h3>Модуль недоступен</h3>
        <p className="text-titanium">Этот раздел выключен на текущем тарифе.</p>
      </div>
    );
  }
  return <>{children}</>;
}
