import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { BrandProvider } from './design';

import './styles/global.css';
import './styles/theme.css';
import './styles/components.css';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <BrandProvider>
          <App />
        </BrandProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
