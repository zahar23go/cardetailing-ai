import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // antd — один крупный vendor-чанк (~1.2 МБ, 363 КБ gzip): это сама библиотека.
    // Код приложения разбит по роутам (React.lazy), поэтому порог предупреждения
    // поднят под размер вендора, а не под размер приложения.
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // Крупные библиотеки — отдельными чанками: кэшируются и грузятся параллельно.
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'antd-vendor': ['antd'],
          'icons-vendor': ['@ant-design/icons'],
          'charts-vendor': ['recharts'],
          'motion-vendor': ['framer-motion'],
        },
      },
    },
  },
});
