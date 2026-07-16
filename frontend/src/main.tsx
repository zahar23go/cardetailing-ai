import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import App from './App';

// ============================================
// ПОДКЛЮЧЕНИЕ ДИЗАЙН-СИСТЕМЫ
// ============================================
import './styles/global.css';
import './styles/theme.css';
import './styles/components.css';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: '#C8A977',
            colorBgContainer: '#13161A',
            colorBgElevated: '#13161A',
            colorText: '#FFFFFF',
            colorTextSecondary: '#AAB2BF',
            borderRadius: 14,
            fontFamily: "'Inter', -apple-system, sans-serif",
          },
        }}
      >
        <App />
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
);