/**
 * Mock Auth Service for Tests
 *
 * Provides mock authentication functions that return test tokens.
 */

import { vi } from 'vitest';

export const mockAuthService = {
  getAccessToken: vi.fn().mockResolvedValue('mock-jwt-token-12345'),
  isAuthenticated: vi.fn().mockReturnValue(true),
  getCurrentUser: vi.fn().mockResolvedValue({
    username: 'test-user',
    attributes: {
      email: 'test@example.com',
    },
  }),
};

// Mock the actual auth service module
vi.mock('@/services/authService', () => mockAuthService);
