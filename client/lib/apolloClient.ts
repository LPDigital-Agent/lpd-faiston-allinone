'use client';

/**
 * @file apolloClient.ts
 * @description Configuração do Apollo Client para GraphQL API (AWS AppSync)
 *
 * Inclui:
 * - HTTP Link para conexão com AppSync
 * - Auth Link para adicionar token JWT às requisições
 * - Error Link para tratamento de erros de autenticação
 * - Cache InMemory com políticas de fetch
 */

import {
  ApolloClient,
  InMemoryCache,
  createHttpLink,
  ApolloLink,
  from,
} from '@apollo/client/core';
import { setContext } from '@apollo/client/link/context';
import { onError } from '@apollo/client/link/error';
import { ensureValidToken } from '@/utils/tokenRefresh';
import { signOut } from '@/services/authService';
import { cognitoConfig } from '@/lib/config/cognito';

// =============================================================================
// HTTP Link
// =============================================================================

/**
 * Link HTTP para conexão com o GraphQL API (AWS AppSync)
 */
const httpLink = createHttpLink({
  uri: cognitoConfig.graphqlEndpoint,
});

// =============================================================================
// Auth Link
// =============================================================================

/**
 * Link de autenticação que adiciona o token JWT a cada requisição
 * Usa ensureValidToken para garantir que o token está válido
 */
const authLink = setContext(async (_, { headers }) => {
  try {
    // Obtém token válido (renova automaticamente se necessário)
    const token = await ensureValidToken();

    if (!token) {
      // Sem token, requisição vai falhar - deixar o error link tratar
      return { headers };
    }

    return {
      headers: {
        ...headers,
        authorization: token,
      },
    };
  } catch (error) {
    console.error('[Apollo] Erro ao obter token:', error);
    return { headers };
  }
});

// =============================================================================
// Error Link
// =============================================================================

/**
 * Link de tratamento de erros
 * Redireciona para login em caso de erros de autenticação
 */
const errorLink = onError(({ graphQLErrors, networkError, operation }) => {
  // Tratar erros GraphQL
  if (graphQLErrors) {
    for (const err of graphQLErrors) {
      const errorCode = err.extensions?.code as string;
      const errorMessage = err.message;

      console.error(
        `[Apollo GraphQL Error] ${operation.operationName}:`,
        errorMessage
      );

      // Verificar se é erro de autenticação
      if (
        errorCode === 'UNAUTHENTICATED' ||
        errorCode === 'UNAUTHORIZED' ||
        errorMessage.includes('Unauthorized') ||
        errorMessage.includes('Not Authorized')
      ) {
        console.warn('[Apollo] Erro de autenticação, fazendo logout...');

        // Fazer logout e redirecionar
        signOut();

        // Só redirecionar se estiver no browser
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      }
    }
  }

  // Tratar erros de rede
  if (networkError) {
    console.error('[Apollo Network Error]:', networkError);

    // Verificar se é erro 401/403
    if ('statusCode' in networkError) {
      const statusCode = (networkError as { statusCode: number }).statusCode;

      if (statusCode === 401 || statusCode === 403) {
        console.warn('[Apollo] Status 401/403, fazendo logout...');
        signOut();

        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      }
    }
  }
});

// =============================================================================
// Cache
// =============================================================================

/**
 * Cache InMemory com configurações otimizadas
 */
const cache = new InMemoryCache({
  typePolicies: {
    Query: {
      fields: {
        // Configuração para queries específicas pode ser adicionada aqui
        me: {
          // Mesclar dados do usuário ao atualizar
          merge: true,
        },
      },
    },
    // Configurar identificadores únicos para tipos
    User: {
      keyFields: ['id'],
    },
  },
});

// =============================================================================
// Apollo Client
// =============================================================================

/**
 * Instância do Apollo Client configurada
 *
 * @example
 * ```tsx
 * // Em um componente React
 * import { useQuery } from '@apollo/client';
 * import { GET_ME } from '@/lib/graphql/queries';
 *
 * function Profile() {
 *   const { data, loading, error } = useQuery(GET_ME);
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <Error message={error.message} />;
 *
 *   return <div>Olá, {data.me.name}</div>;
 * }
 * ```
 */
export const apolloClient = new ApolloClient({
  // Combinar links na ordem correta: error -> auth -> http
  link: from([errorLink, authLink, httpLink]),

  // Cache configurado
  cache,

  // Opções padrão para queries
  defaultOptions: {
    watchQuery: {
      // Buscar do cache e da rede (dados atualizados)
      fetchPolicy: 'cache-and-network',
      // Em caso de erro, ainda usar dados do cache
      errorPolicy: 'all',
    },
    query: {
      fetchPolicy: 'cache-first',
      errorPolicy: 'all',
    },
    mutate: {
      errorPolicy: 'all',
    },
  },

  // Identificador do cliente (útil para debugging)
  name: 'faiston-nexo-web',
  version: '1.0.0',
});

// =============================================================================
// Helper para SSR
// =============================================================================

/**
 * Resetar o cache do Apollo (útil após logout)
 */
export const resetApolloCache = async (): Promise<void> => {
  await apolloClient.resetStore();
};

/**
 * Limpar completamente o cache (mais agressivo que reset)
 */
export const clearApolloCache = (): void => {
  apolloClient.clearStore();
};
