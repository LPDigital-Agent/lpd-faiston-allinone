/**
 * MSW Server Configuration
 *
 * Sets up Mock Service Worker for intercepting HTTP requests in tests.
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
