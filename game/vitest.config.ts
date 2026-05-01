import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@scenes': path.resolve(__dirname, 'src/scenes'),
      '@systems': path.resolve(__dirname, 'src/systems'),
      '@data': path.resolve(__dirname, 'src/data'),
      '@entities': path.resolve(__dirname, 'src/entities'),
      '@ui': path.resolve(__dirname, 'src/ui'),
      '@state': path.resolve(__dirname, 'src/state'),
      '@pwa': path.resolve(__dirname, 'src/pwa'),
    },
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts', 'src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/systems/**/*.ts', 'src/data/**/*.ts'],
    },
  },
});
