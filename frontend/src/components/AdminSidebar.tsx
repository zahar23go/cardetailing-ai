/* ============================================================
   AdminSidebar — иерархическое меню с аккордеоном
   Стили: только существующие .sidebar-item / .sidebar-icon / .active
   ============================================================ */

import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  HomeOutlined, AreaChartOutlined, BulbOutlined, DollarOutlined,
  BarChartOutlined, FileTextOutlined, CalendarOutlined, TeamOutlined,
  SettingOutlined, GiftOutlined, BellOutlined, DownOutlined, RightOutlined,
  ToolOutlined, BgColorsOutlined, AppstoreOutlined,
} from '@ant-design/icons';
import {
  ADMIN_NAV,
  NAV_STORAGE_KEY,
  groupIdForPath,
  type NavEntry,
  type NavLeaf,
} from '../admin/navConfig';

const ICONS: Record<string, React.ReactNode> = {
  home: <HomeOutlined />,
  analytics: <AreaChartOutlined />,
  financier: <BulbOutlined />,
  finances: <DollarOutlined />,
  metrics: <AreaChartOutlined />,
  reports: <BarChartOutlined />,
  upload: <AppstoreOutlined />,
  records: <FileTextOutlined />,
  calendar: <CalendarOutlined />,
  crm: <TeamOutlined />,
  users: <TeamOutlined />,
  services: <ToolOutlined />,
  discounts: <GiftOutlined />,
  settings: <SettingOutlined />,
  notifications: <BellOutlined />,
  branding: <BgColorsOutlined />,
};

function readOpenGroups(): string[] {
  try {
    const raw = localStorage.getItem(NAV_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

export default function AdminSidebar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [openGroups, setOpenGroups] = useState<string[]>(readOpenGroups);

  // Авто-открыть группу активного пункта + сохранить
  useEffect(() => {
    const gid = groupIdForPath(pathname);
    if (!gid) return;
    setOpenGroups((prev) => {
      if (prev.includes(gid)) return prev;
      const next = [...prev, gid];
      localStorage.setItem(NAV_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, [pathname]);

  const persist = (next: string[]) => {
    setOpenGroups(next);
    localStorage.setItem(NAV_STORAGE_KEY, JSON.stringify(next));
  };

  const toggleGroup = (id: string) => {
    persist(
      openGroups.includes(id)
        ? openGroups.filter((g) => g !== id)
        : [...openGroups, id],
    );
  };

  const go = (leaf: NavLeaf) => {
    navigate(leaf.path);
  };

  const renderLeaf = (leaf: NavLeaf, nested = false) => {
    const active = pathname === leaf.path;
    return (
      <button
        key={leaf.path}
        type="button"
        className={`sidebar-item${active ? ' active' : ''}`}
        style={nested ? { paddingLeft: 36 } : undefined}
        onClick={() => go(leaf)}
      >
        <span className="sidebar-icon">{ICONS[leaf.icon || ''] || null}</span>
        <span>{leaf.label}</span>
      </button>
    );
  };

  const renderEntry = (entry: NavEntry) => {
    if (entry.type === 'leaf') {
      return renderLeaf(entry, false);
    }

    const isOpen = openGroups.includes(entry.id);
    const childActive = entry.children.some((c) => c.path === pathname);

    return (
      <div key={entry.id}>
        <button
          type="button"
          className={`sidebar-item${childActive ? ' active' : ''}`}
          onClick={() => toggleGroup(entry.id)}
          aria-expanded={isOpen}
        >
          <span className="sidebar-icon">{ICONS[entry.icon || ''] || null}</span>
          <span style={{ flex: 1 }}>{entry.label}</span>
          <span className="sidebar-icon">
            {isOpen ? <DownOutlined /> : <RightOutlined />}
          </span>
        </button>
        {isOpen && entry.children.map((child) => renderLeaf(child, true))}
      </div>
    );
  };

  return <>{ADMIN_NAV.map(renderEntry)}</>;
}
