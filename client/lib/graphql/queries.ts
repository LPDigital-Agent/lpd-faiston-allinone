/**
 * @file queries.ts
 * @description Queries GraphQL para o Faiston NEXO
 *
 * Queries para buscar dados do usuário e outros recursos da API AppSync.
 */

import { gql } from '@apollo/client';

// =============================================================================
// Fragments (Partes reutilizáveis)
// =============================================================================

/**
 * Fragment com campos básicos do usuário
 */
export const USER_BASIC_FIELDS = gql`
  fragment UserBasicFields on User {
    id
    email
    name
    isAdmin
    status
    createdAt
    updatedAt
  }
`;

// =============================================================================
// Queries de Usuário
// =============================================================================

/**
 * Buscar dados do usuário atual (autenticado)
 *
 * @example
 * ```tsx
 * const { data, loading } = useQuery(GET_ME);
 * console.log(data?.me.name);
 * ```
 */
export const GET_ME = gql`
  query GetMe {
    me {
      id
      email
      name
      isAdmin
      status
      createdAt
      updatedAt
    }
  }
`;

/**
 * Listar todos os usuários (apenas para admins)
 *
 * @example
 * ```tsx
 * const { data } = useQuery(LIST_USERS, {
 *   variables: { limit: 20, nextToken: null }
 * });
 * ```
 */
export const LIST_USERS = gql`
  query ListUsers($limit: Int, $nextToken: String) {
    listUsers(limit: $limit, nextToken: $nextToken) {
      users {
        id
        email
        name
        isAdmin
        status
        createdAt
      }
      nextToken
    }
  }
`;

/**
 * Buscar usuário por ID (apenas para admins)
 */
export const GET_USER_BY_ID = gql`
  query GetUserById($id: ID!) {
    user(id: $id) {
      id
      email
      name
      isAdmin
      status
      createdAt
      updatedAt
    }
  }
`;

// =============================================================================
// Tipos TypeScript para Responses
// =============================================================================

/** Dados do usuário retornados pela API */
export interface User {
  id: string;
  email: string;
  name: string | null;
  isAdmin: boolean;
  status: 'ACTIVE' | 'INACTIVE' | 'PENDING';
  createdAt: string;
  updatedAt: string;
}

/** Response da query GET_ME */
export interface GetMeResponse {
  me: User;
}

/** Response da query LIST_USERS */
export interface ListUsersResponse {
  listUsers: {
    users: User[];
    nextToken: string | null;
  };
}

/** Response da query GET_USER_BY_ID */
export interface GetUserByIdResponse {
  user: User;
}

/** Variáveis para LIST_USERS */
export interface ListUsersVariables {
  limit?: number;
  nextToken?: string | null;
}

/** Variáveis para GET_USER_BY_ID */
export interface GetUserByIdVariables {
  id: string;
}
