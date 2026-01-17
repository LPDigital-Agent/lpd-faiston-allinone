// =============================================================================
// AgentCore A2A Response Extraction Utility - Faiston NEXO
// =============================================================================
// Purpose: Extract actual response data from Strands A2A wrapped responses.
//
// Strands A2A wraps specialist agent responses with observability metadata:
// {
//   success: boolean,
//   specialist_agent: string,   // Agent that handled the request
//   response: T,                // Actual payload from specialist
//   request_id: string          // Request tracing ID
// }
//
// This utility extracts the inner response for frontend consumption while
// preserving the Agentic architecture pattern on the backend.
// =============================================================================

/**
 * Strands A2A wrapped response format.
 * All specialist agent responses include observability metadata.
 */
export interface AgentWrappedResponse<T> {
  success: boolean;
  specialist_agent: string;
  response: T;
  request_id: string;
}

/**
 * Type guard to check if response has A2A agent metadata.
 */
export function isAgentWrappedResponse<T>(data: unknown): data is AgentWrappedResponse<T> {
  if (!data || typeof data !== 'object') return false;
  const obj = data as Record<string, unknown>;
  return 'specialist_agent' in obj && 'response' in obj;
}

/**
 * Extract actual response data from AgentCore A2A wrapped responses.
 *
 * Handles both wrapped A2A responses and direct/legacy flat responses
 * for backward compatibility during migration.
 *
 * @param data - The response data (potentially wrapped)
 * @returns The inner response payload (type T)
 *
 * @example
 * ```typescript
 * // Wrapped A2A response
 * const wrapped = {
 *   success: true,
 *   specialist_agent: "intake",
 *   response: { upload_url: "https://...", s3_key: "uploads/..." },
 *   request_id: "direct-get_nf_upload_url"
 * };
 * const data = extractAgentResponse<UploadUrlResponse>(wrapped);
 * // data = { upload_url: "https://...", s3_key: "uploads/..." }
 *
 * // Direct/legacy response (unchanged)
 * const flat = { upload_url: "https://...", s3_key: "uploads/..." };
 * const data2 = extractAgentResponse<UploadUrlResponse>(flat);
 * // data2 = { upload_url: "https://...", s3_key: "uploads/..." }
 * ```
 */
export function extractAgentResponse<T>(data: unknown): T {
  if (!data || typeof data !== 'object') {
    return data as T;
  }

  // Check if this is a wrapped A2A response
  if (isAgentWrappedResponse<T>(data)) {
    return data.response;
  }

  // Already flat (legacy or direct response)
  return data as T;
}

/**
 * Extract agent metadata from a wrapped response.
 * Returns null if the response is not wrapped.
 */
export function extractAgentMetadata(data: unknown): {
  specialist_agent: string;
  request_id: string;
} | null {
  if (!isAgentWrappedResponse(data)) return null;
  return {
    specialist_agent: data.specialist_agent,
    request_id: data.request_id,
  };
}

// =============================================================================
// BUG-022 FIX: Safe Error Message Extraction
// =============================================================================
// Handles double-encoded JSON strings that can occur when A2A transport
// serializes already-JSON responses (e.g., '"success"' instead of 'success')
// =============================================================================

/**
 * Safely extract error message from potentially double-encoded string.
 *
 * Handles cases where backend sends:
 * - "\"success\"" (double-encoded string)
 * - "success" (normal string)
 * - { error: "message" } (object with error field)
 *
 * @param value - The value to extract error message from
 * @returns The unwrapped error message string
 *
 * @example
 * ```typescript
 * safeExtractErrorMessage('"success"'); // Returns: 'success'
 * safeExtractErrorMessage('normal error'); // Returns: 'normal error'
 * safeExtractErrorMessage({ error: '"nested"' }); // Returns: 'nested'
 * ```
 */
export function safeExtractErrorMessage(value: unknown): string {
  if (typeof value === 'string') {
    // Try to unwrap if it looks like a JSON-encoded string
    if (value.startsWith('"') && value.endsWith('"')) {
      try {
        const parsed = JSON.parse(value);
        if (typeof parsed === 'string') {
          return parsed;
        }
      } catch {
        // Return as-is if parsing fails
      }
    }
    return value;
  }

  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    if ('error' in obj) {
      return safeExtractErrorMessage(obj.error);
    }
    if ('message' in obj) {
      return safeExtractErrorMessage(obj.message);
    }
  }

  return 'Erro desconhecido';
}

/**
 * Check if a response indicates an error.
 *
 * @param data - The response data to check
 * @returns True if the response contains error indicators
 */
export function isErrorResponse(data: unknown): boolean {
  if (!data || typeof data !== 'object') return false;
  const obj = data as Record<string, unknown>;
  return obj.success === false || 'error' in obj;
}
