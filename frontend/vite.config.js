import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/ask': 'http://127.0.0.1:8000',
      '/ping': 'http://127.0.0.1:8000',
    },
  },
})
