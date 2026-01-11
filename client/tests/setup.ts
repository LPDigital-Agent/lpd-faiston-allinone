/**
 * Vitest Test Setup
 *
 * Configures test environment with:
 * - @testing-library/jest-dom matchers
 * - Mock Service Worker (MSW) for API mocking
 * - SessionStorage mock for browser APIs
 */

import { expect, afterEach, beforeAll, afterAll, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';
import { server } from './mocks/server';
import './mocks/authService'; // Apply auth mocks

// Extend Vitest matchers with jest-dom matchers
expect.extend(matchers);

// Setup MSW server
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' });
});

afterEach(() => {
  // Clean up React Testing Library
  cleanup();

  // Reset MSW handlers
  server.resetHandlers();

  // Clear all mocks
  vi.clearAllMocks();

  // Clear sessionStorage
  sessionStorage.clear();
});

afterAll(() => {
  server.close();
});

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: vi.fn(),
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};
