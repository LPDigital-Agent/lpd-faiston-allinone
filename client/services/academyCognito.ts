// =============================================================================
// Academy Cognito Authentication Service - Faiston Academy
// =============================================================================
// Purpose: Provide JWT tokens for AgentCore invocation.
// Uses AWS Cognito for authentication.
//
// Note: This service is specifically for Academy AI features.
// The main app authentication is handled by authService.ts.
// =============================================================================

import { cognitoConfig, tokenConfig } from '@/lib/config/cognito';
import { ACADEMY_STORAGE_KEYS } from '@/lib/academy/constants';

// =============================================================================
// Types
// =============================================================================

export interface CognitoTokens {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresAt: number;
}

export interface CognitoUser {
  sub: string;
  email: string;
  email_verified?: boolean;
  name?: string;
  given_name?: string;
  family_name?: string;
  picture?: string;
}

// =============================================================================
// Token Cache
// =============================================================================

let cachedTokens: CognitoTokens | null = null;

function getCachedTokens(): CognitoTokens | null {
  if (typeof window === 'undefined') return null;

  if (cachedTokens) {
    return cachedTokens;
  }

  try {
    const stored = localStorage.getItem(ACADEMY_STORAGE_KEYS.COGNITO_TOKENS);
    if (stored) {
      cachedTokens = JSON.parse(stored);
      return cachedTokens;
    }
  } catch {
    // localStorage not available or invalid data
  }

  return null;
}

function setCachedTokens(tokens: CognitoTokens): void {
  cachedTokens = tokens;
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(ACADEMY_STORAGE_KEYS.COGNITO_TOKENS, JSON.stringify(tokens));
  } catch {
    // localStorage not available
  }
}

// =============================================================================
// Authentication
// =============================================================================

/**
 * Authenticate user with Cognito and obtain JWT tokens.
 */
export async function authenticateAcademyCognito(
  username: string,
  password: string
): Promise<CognitoTokens> {
  const endpoint = `https://cognito-idp.${cognitoConfig.region}.amazonaws.com/`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-amz-json-1.1',
      'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
    },
    body: JSON.stringify({
      AuthFlow: 'USER_PASSWORD_AUTH',
      ClientId: cognitoConfig.clientId,
      AuthParameters: {
        USERNAME: username,
        PASSWORD: password,
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const message = error.__type || error.message || 'Autenticacao falhou';
    throw new Error(`Cognito: ${message}`);
  }

  const data = await response.json();

  if (data.ChallengeName) {
    throw new Error(`Desafio de autenticacao: ${data.ChallengeName}`);
  }

  const result = data.AuthenticationResult;
  if (!result) {
    throw new Error('Sem resultado de autenticacao');
  }

  const tokens: CognitoTokens = {
    accessToken: result.AccessToken,
    idToken: result.IdToken,
    refreshToken: result.RefreshToken,
    expiresAt: Date.now() + result.ExpiresIn * 1000,
  };

  setCachedTokens(tokens);
  return tokens;
}

/**
 * Refresh tokens using the refresh token.
 */
export async function refreshAcademyTokens(): Promise<CognitoTokens> {
  const tokens = getCachedTokens();
  if (!tokens?.refreshToken) {
    throw new Error('Sem refresh token disponivel');
  }

  const endpoint = `https://cognito-idp.${cognitoConfig.region}.amazonaws.com/`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-amz-json-1.1',
      'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
    },
    body: JSON.stringify({
      AuthFlow: 'REFRESH_TOKEN_AUTH',
      ClientId: cognitoConfig.clientId,
      AuthParameters: {
        REFRESH_TOKEN: tokens.refreshToken,
      },
    }),
  });

  if (!response.ok) {
    clearAcademyTokens();
    throw new Error('Falha ao renovar token');
  }

  const data = await response.json();
  const result = data.AuthenticationResult;

  const newTokens: CognitoTokens = {
    accessToken: result.AccessToken,
    idToken: result.IdToken,
    refreshToken: tokens.refreshToken,
    expiresAt: Date.now() + result.ExpiresIn * 1000,
  };

  setCachedTokens(newTokens);
  return newTokens;
}

/**
 * Get the current access token for AgentCore invocation.
 * Automatically refreshes if about to expire.
 */
export async function getAcademyCognitoToken(): Promise<string | null> {
  let tokens = getCachedTokens();

  if (!tokens) {
    return null;
  }

  // Refresh if about to expire (within refresh margin)
  const marginMs = tokenConfig.refreshMargin * 60 * 1000;
  if (Date.now() > tokens.expiresAt - marginMs) {
    try {
      tokens = await refreshAcademyTokens();
    } catch {
      return null;
    }
  }

  return tokens.accessToken;
}

/**
 * Clear all Cognito tokens (logout).
 */
export function clearAcademyTokens(): void {
  cachedTokens = null;
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(ACADEMY_STORAGE_KEYS.COGNITO_TOKENS);
  } catch {
    // localStorage not available
  }
}

/**
 * Check if user has valid Cognito tokens.
 */
export function hasAcademyTokens(): boolean {
  const tokens = getCachedTokens();
  return tokens !== null && Date.now() < tokens.expiresAt;
}

// =============================================================================
// User Data from ID Token
// =============================================================================

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    let payload = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const pad = payload.length % 4;
    if (pad) {
      payload += '='.repeat(4 - pad);
    }

    const binaryString = atob(payload);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const decoded = new TextDecoder('utf-8').decode(bytes);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

/**
 * Get user data from Cognito ID token.
 */
export function getAcademyCognitoUser(): CognitoUser | null {
  const tokens = getCachedTokens();
  if (!tokens?.idToken) return null;

  const payload = decodeJwtPayload(tokens.idToken);
  if (!payload) return null;

  const user: CognitoUser = {
    sub: (payload.sub as string) || '',
    email: (payload.email as string) || '',
    email_verified: payload.email_verified as boolean | undefined,
    name: (payload.name as string) || undefined,
    given_name: (payload.given_name as string) || undefined,
    family_name: (payload.family_name as string) || undefined,
    picture: (payload.picture as string) || undefined,
  };

  if (!user.name && (user.given_name || user.family_name)) {
    user.name = [user.given_name, user.family_name].filter(Boolean).join(' ');
  }

  return user;
}

// =============================================================================
// Configuration Helper
// =============================================================================

export function getAcademyCognitoConfig() {
  return {
    region: cognitoConfig.region,
    userPoolId: cognitoConfig.userPoolId,
    clientId: cognitoConfig.clientId,
    configured: Boolean(cognitoConfig.userPoolId && cognitoConfig.clientId),
  };
}
