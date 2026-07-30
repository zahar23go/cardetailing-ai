import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import { ThemeProvider } from 'styled-components';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { theme } from './theme';

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
      <ThemeProvider theme={theme}>
        <BrowserRouter>
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: '#C8A977',
              colorBgContainer: '#13161A',
              colorBgElevated: '#13161A',
              colorText: '#FFFFFF',
              colorTextSecondary: '#AAB2BF',
              borderRadius: 14,
              fontFamily: "'Manrope', -apple-system, sans-serif",
            },
          }}
        >
          <App />
        </ConfigProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
);