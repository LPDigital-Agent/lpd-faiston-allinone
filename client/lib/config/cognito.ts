/**
 * @file cognito.ts
 * @description Configuração do AWS Cognito para autenticação no Faiston NEXO
 *
 * Este arquivo centraliza todas as configurações do Cognito, incluindo:
 * - Credenciais do User Pool (via variáveis de ambiente)
 * - Validade dos tokens
 * - Requisitos de senha para validação client-side
 */

// =============================================================================
// Configuração Principal do Cognito
// =============================================================================

export const cognitoConfig = {
  /** Região AWS onde o User Pool está hospedado */
  region: process.env.NEXT_PUBLIC_AWS_REGION || 'us-east-2',

  /** ID do User Pool (formato: us-east-2_XXXXXXXXX) */
  userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID || '',

  /** ID do Client App do User Pool */
  clientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID || '',

  /** Endpoint do GraphQL API (AWS AppSync) */
  graphqlEndpoint: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT || '',
} as const;

// =============================================================================
// Configuração de Validade dos Tokens
// =============================================================================

export const tokenConfig = {
  /** Validade do Access Token em minutos */
  accessTokenValidity: 60,

  /** Validade do ID Token em minutos */
  idTokenValidity: 60,

  /** Validade do Refresh Token em dias */
  refreshTokenValidity: 30,

  /** Margem de segurança para renovação (em minutos antes de expirar) */
  refreshMargin: 5,
} as const;

// =============================================================================
// Requisitos de Senha (para validação client-side)
// =============================================================================

export const passwordRequirements = {
  /** Comprimento mínimo da senha */
  minLength: 8,

  /** Requer pelo menos uma letra maiúscula (A-Z) */
  requireUppercase: true,

  /** Requer pelo menos uma letra minúscula (a-z) */
  requireLowercase: true,

  /** Requer pelo menos um número (0-9) */
  requireNumbers: true,

  /** Requer pelo menos um caractere especial (!@#$%^&*...) */
  requireSymbols: true,
} as const;

// =============================================================================
// Funções de Validação
// =============================================================================

/**
 * Resultado da validação de senha com checks individuais
 */
export interface PasswordValidationResult {
  isValid: boolean;
  checks: {
    minLength: boolean;
    hasUppercase: boolean;
    hasLowercase: boolean;
    hasNumber: boolean;
    hasSpecial: boolean;
  };
  errorMessage: string | null;
}

/**
 * Valida se uma senha atende aos requisitos de segurança do Cognito
 *
 * @param password - Senha a ser validada
 * @returns Objeto com resultado da validação e checks individuais
 *
 * @example
 * ```typescript
 * const validation = validatePassword('Test123!');
 * if (!validation.isValid) {
 *   console.log(validation.checks); // Ver quais requisitos faltam
 * }
 * ```
 */
export const validatePassword = (password: string): PasswordValidationResult => {
  const checks = {
    minLength: password.length >= passwordRequirements.minLength,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[^A-Za-z0-9]/.test(password),
  };

  const isValid =
    checks.minLength &&
    (!passwordRequirements.requireUppercase || checks.hasUppercase) &&
    (!passwordRequirements.requireLowercase || checks.hasLowercase) &&
    (!passwordRequirements.requireNumbers || checks.hasNumber) &&
    (!passwordRequirements.requireSymbols || checks.hasSpecial);

  let errorMessage: string | null = null;
  if (!checks.minLength) {
    errorMessage = `A senha deve ter pelo menos ${passwordRequirements.minLength} caracteres`;
  } else if (passwordRequirements.requireUppercase && !checks.hasUppercase) {
    errorMessage = 'A senha deve conter pelo menos uma letra maiúscula';
  } else if (passwordRequirements.requireLowercase && !checks.hasLowercase) {
    errorMessage = 'A senha deve conter pelo menos uma letra minúscula';
  } else if (passwordRequirements.requireNumbers && !checks.hasNumber) {
    errorMessage = 'A senha deve conter pelo menos um número';
  } else if (passwordRequirements.requireSymbols && !checks.hasSpecial) {
    errorMessage = 'A senha deve conter pelo menos um caractere especial';
  }

  return { isValid, checks, errorMessage };
};

/**
 * Domínios de email permitidos para cadastro
 */
export const allowedEmailDomains = ['lpdigital.ai', 'faiston.com'] as const;

/**
 * Valida formato de email e domínio permitido
 *
 * @param email - Email a ser validado
 * @returns true se o email é válido e de um domínio permitido
 */
export const validateEmail = (email: string): boolean => {
  // Regex que valida formato e restringe aos domínios permitidos
  const emailRegex = /^[^\s@]+@(lpdigital\.ai|faiston\.com)$/i;
  return emailRegex.test(email);
};

/**
 * Verifica se a configuração do Cognito está completa
 * Útil para debug e validação em desenvolvimento
 *
 * @returns true se todas as variáveis estão configuradas
 */
export const isConfigValid = (): boolean => {
  return !!(
    cognitoConfig.userPoolId &&
    cognitoConfig.clientId &&
    cognitoConfig.region
  );
};

/**
 * Retorna mensagem de erro se a configuração estiver incompleta
 *
 * @returns Mensagem de erro ou null se configuração válida
 */
export const getConfigError = (): string | null => {
  if (!cognitoConfig.userPoolId) {
    return 'NEXT_PUBLIC_USER_POOL_ID não configurado';
  }
  if (!cognitoConfig.clientId) {
    return 'NEXT_PUBLIC_USER_POOL_CLIENT_ID não configurado';
  }
  return null;
};
