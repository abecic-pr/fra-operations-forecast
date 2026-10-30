import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    proxy: {
      '/how-it-works': { target: 'http://127.0.0.1:8000', changeOrigin: false },
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
});
