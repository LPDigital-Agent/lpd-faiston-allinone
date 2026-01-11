# Faiston NEXO Test Infrastructure

## Overview

This directory contains the testing infrastructure for the Faiston NEXO client application, built with Vitest, React Testing Library, and MSW (Mock Service Worker).

## Installation

Dependencies are already added to `package.json`. If you need to reinstall:

```bash
npm install
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- useAgentRoomStream
```

## Test Structure

```
client/
├── tests/
│   ├── setup.ts              # Global test setup (MSW, matchers)
│   ├── utils/
│   │   └── test-utils.tsx    # Custom render with providers
│   └── mocks/
│       ├── server.ts          # MSW server setup
│       ├── handlers.ts        # API mock handlers
│       ├── helpers.ts         # Helper functions for creating handlers
│       └── authService.ts     # Auth service mocks
├── hooks/ativos/__tests__/
│   ├── useAgentRoomStream.test.tsx        # Comprehensive tests
│   └── useAgentRoomStream.simple.test.tsx # Simplified reliable tests
└── vitest.config.ts          # Vitest configuration
```

## Key Features

### 1. Vitest Configuration (`vitest.config.ts`)
- JSX/TSX support with automatic JSX runtime
- jsdom environment for browser APIs
- Path aliases (`@` maps to project root)
- Coverage with V8 provider
- Global test utilities

### 2. Test Setup (`tests/setup.ts`)
- **@testing-library/jest-dom** matchers (toBeInTheDocument, toHaveLength, etc.)
- **MSW server** lifecycle (beforeAll, afterEach, afterAll)
- **SessionStorage mock** for browser storage APIs
- **Console mock** to reduce noise in test output
- **Auth service mock** for JWT token generation

### 3. Mock Service Worker (MSW)
- Intercepts AgentCore API calls at network level
- Provides consistent mock responses
- Easy to override per-test with `server.use()`

### 4. Test Utilities (`tests/utils/test-utils.tsx`)
- Custom `render` function with QueryClientProvider
- `createTestQueryClient` for isolated test queries
- `AllTheProviders` wrapper component

## Writing Tests

### Basic Test Example

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useAgentRoomStream } from '../useAgentRoomStream';
import { createWrapper } from './test-helpers';

describe('My Hook', () => {
  it('fetches data', async () => {
    const { result } = renderHook(() => useAgentRoomStream(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.agents).toBeDefined();
  });
});
```

### Mocking API Responses

```typescript
import { server } from '@/tests/mocks/server';
import { createAgentCoreHandler } from '@/tests/mocks/helpers';

it('handles custom response', async () => {
  const customData = { /* ... */ };

  server.use(createAgentCoreHandler(customData));

  // Test continues...
});
```

## Agent Room Hook Tests

The `useAgentRoomStream` hook has two test suites:

### 1. Comprehensive Tests (`useAgentRoomStream.test.tsx`)
- **23 test cases** covering all functionality
- Data transformation (agents, messages, stories, workflow, decisions)
- Hook behavior (loading, fetching, polling, paused state)
- Error handling (retries, error messages)
- Specialized hooks (useLiveFeed, useAgentProfiles, etc.)

### 2. Simplified Tests (`useAgentRoomStream.simple.test.tsx`)
- **15 test cases** with more reliable async handling
- Basic behavior tests
- Error handling tests
- Specialized hooks tests
- Data transformation tests

## Test Coverage Areas

### Data Transformation
- ✅ `transformAgents` - Backend to frontend agent format
- ✅ `transformMessages` - Live feed messages
- ✅ `transformLearningStories` - Learning entries
- ✅ `transformWorkflow` - Active workflow timeline
- ✅ `transformDecisions` - Pending HIL decisions
- ✅ `getMockAgentProfiles` - Fallback to constants

### Hook Behavior
- ✅ Initial loading state
- ✅ Fetch when enabled
- ✅ Don't fetch when disabled
- ✅ Don't fetch when paused
- ✅ `clearMessages` removes messages by ID
- ✅ `setPaused` controls polling
- ✅ `refetch` triggers manual fetch
- ✅ SessionId in query key

### Error Handling
- ✅ Fetch errors (500, 503, etc.)
- ✅ Retry logic with exponential backoff
- ✅ Error message when success: false
- ✅ Connection state management

### Specialized Hooks
- ✅ `useLiveFeed` - Messages only
- ✅ `useAgentProfiles` - Agents only
- ✅ `useLearningStories` - Stories only
- ✅ `useWorkflowTimeline` - Workflow only
- ✅ `usePendingDecisions` - Decisions only

## Known Issues & Debugging

### Issue: MSW Handlers Not Intercepting

Some tests show that mock handlers are not being properly intercepted. This could be due to:

1. **URL Pattern Mismatch**: Ensure handlers match the exact URL pattern used by the service
   - Current pattern: `https://bedrock-agentcore.us-east-2.amazonaws.com/runtimes/*/invocations`
   - Verify with console logs in the service

2. **Async Timing**: React Query may be caching or not triggering fetches
   - Solution: Use `waitFor` with explicit expectations
   - Solution: Reset QueryClient between tests

3. **Network Requests**: MSW may not be intercepting in test environment
   - Solution: Ensure `server.listen()` is called in `beforeAll`
   - Solution: Check MSW version compatibility with Node.js

### Debugging Tips

```typescript
// Log what MSW is intercepting
server.events.on('request:start', (req) => {
  console.log('MSW intercepted:', req.method, req.url);
});

// Log React Query state
const { result } = renderHook(() => useAgentRoomStream());
console.log('Query state:', result.current);
```

## Next Steps

1. **Fix MSW Interception**: Debug why some handlers aren't matching
2. **Add Component Tests**: Test React components that use these hooks
3. **Integration Tests**: Test full user flows
4. **E2E Tests**: Consider Playwright/Cypress for end-to-end testing
5. **Performance Tests**: Measure hook re-render counts
6. **Accessibility Tests**: Add axe-core for a11y testing

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [MSW Documentation](https://mswjs.io/)
- [TanStack Query Testing](https://tanstack.com/query/latest/docs/react/guides/testing)

## Test Philosophy

> "Write tests. Not too many. Mostly integration."
> — Guillermo Rauch

- Focus on testing behavior, not implementation
- Mock external dependencies (API, auth)
- Use real React Query, real hooks
- Test user-facing functionality
- Keep tests simple and readable
