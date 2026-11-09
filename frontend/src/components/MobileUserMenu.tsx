/**
 * MobileUserMenu — единое меню аватара для мобильных шапок.
 * Используется в кабинетах Админа, Мастера и Клиента:
 * имя, телефон, дополнительные пункты и выход.
 */
import React from 'react';
import { Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { LogoutOutlined, UserOutlined } from '@ant-design/icons';

interface MobileUserMenuProps {
  user: { full_name: string; phone: string };
  onLogout: () => void;
  extraItems?: MenuProps['items'];
  onExtraClick?: (key: string) => void;
}

export default function MobileUserMenu({
  user,
  onLogout,
  extraItems = [],
  onExtraClick,
}: MobileUserMenuProps) {
  const items: MenuProps['items'] = [
    {
      key: 'profile',
      disabled: true,
      label: (
        <div className="mobile-user-meta">
          <span className="mobile-user-meta-name">{user.full_name}</span>
          <span className="mobile-user-meta-phone">{user.phone}</span>
        </div>
      ),
    },
    ...extraItems,
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Выйти', danger: true },
  ];

  const handleClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      onLogout();
      return;
    }
    onExtraClick?.(key);
  };

  return (
    <Dropdown
      menu={{ items, onClick: handleClick }}
      trigger={['click']}
      placement="bottomRight"
      overlayClassName="mobile-user-menu"
    >
      <button
        type="button"
        className="mobile-user-trigger"
        title="Профиль и выход"
        aria-label="Меню пользователя"
      >
        <UserOutlined />
      </button>
    </Dropdown>
  );
}
