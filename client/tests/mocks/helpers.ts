/**
 * Test Mock Helpers
 *
 * Utilities for creating consistent mock handlers and responses.
 */

import { http, HttpResponse } from 'msw';
import type { AgentRoomDataResponse } from '@/services/sgaAgentcore';

/**
 * URL pattern for AgentCore invocations.
 * Must match the actual endpoint used by the service.
 */
export const AGENTCORE_URL_PATTERN = 'https://bedrock-agentcore.us-east-2.amazonaws.com/runtimes/*/invocations';

/**
 * Create a mock handler for AgentCore invocations.
 *
 * @param responseData - Data to return
 * @returns MSW HTTP handler
 */
export function createAgentCoreHandler(responseData: AgentRoomDataResponse) {
  return http.post(AGENTCORE_URL_PATTERN, () => {
    return HttpResponse.json({
      data: responseData,
      sessionId: `test-session-${crypto.randomUUID()}`,
    });
  });
}

/**
 * Create an error handler for testing error scenarios.
 *
 * @param status - HTTP status code
 * @param error - Error message
 * @returns MSW HTTP handler
 */
export function createAgentCoreErrorHandler(status: number, error: string) {
  return http.post(AGENTCORE_URL_PATTERN, () => {
    return HttpResponse.json(
      { error },
      { status }
    );
  });
}
