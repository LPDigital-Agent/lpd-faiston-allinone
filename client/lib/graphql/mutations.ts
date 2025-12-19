/**
 * @file mutations.ts
 * @description Mutations GraphQL para o Faiston NEXO
 *
 * Mutations para criar, atualizar e deletar recursos na API AppSync.
 */

import { gql } from '@apollo/client';
import type { User } from './queries';

// =============================================================================
// Mutations de Perfil
// =============================================================================

/**
 * Atualizar perfil do usuário atual
 *
 * @example
 * ```tsx
 * const [updateProfile, { loading }] = useMutation(UPDATE_PROFILE);
 *
 * await updateProfile({
 *   variables: {
 *     input: { name: 'Novo Nome' }
 *   }
 * });
 * ```
 */
export const UPDATE_PROFILE = gql`
  mutation UpdateProfile($input: UpdateProfileInput!) {
    updateProfile(input: $input) {
      id
      email
      name
      updatedAt
    }
  }
`;

// =============================================================================
// Mutations de Admin
// =============================================================================

/**
 * Criar novo usuário (apenas admin)
 *
 * @example
 * ```tsx
 * const [createUser] = useMutation(ADMIN_CREATE_USER);
 *
 * await createUser({
 *   variables: {
 *     input: {
 *       email: 'novo@faiston.com',
 *       name: 'Novo Usuário',
 *       isAdmin: false
 *     }
 *   }
 * });
 * ```
 */
export const ADMIN_CREATE_USER = gql`
  mutation AdminCreateUser($input: AdminCreateUserInput!) {
    adminCreateUser(input: $input) {
      id
      email
      name
      isAdmin
      createdAt
    }
  }
`;

/**
 * Atualizar usuário (apenas admin)
 */
export const ADMIN_UPDATE_USER = gql`
  mutation AdminUpdateUser($id: ID!, $input: AdminUpdateUserInput!) {
    adminUpdateUser(id: $id, input: $input) {
      id
      email
      name
      isAdmin
      status
      updatedAt
    }
  }
`;

/**
 * Desativar usuário (apenas admin)
 */
export const ADMIN_DISABLE_USER = gql`
  mutation AdminDisableUser($id: ID!) {
    adminDisableUser(id: $id) {
      id
      status
      updatedAt
    }
  }
`;

/**
 * Reativar usuário (apenas admin)
 */
export const ADMIN_ENABLE_USER = gql`
  mutation AdminEnableUser($id: ID!) {
    adminEnableUser(id: $id) {
      id
      status
      updatedAt
    }
  }
`;

// =============================================================================
// Tipos TypeScript para Inputs e Responses
// =============================================================================

/** Input para UPDATE_PROFILE */
export interface UpdateProfileInput {
  name?: string;
}

/** Response de UPDATE_PROFILE */
export interface UpdateProfileResponse {
  updateProfile: Pick<User, 'id' | 'email' | 'name' | 'updatedAt'>;
}

/** Input para ADMIN_CREATE_USER */
export interface AdminCreateUserInput {
  email: string;
  name?: string;
  isAdmin?: boolean;
}

/** Response de ADMIN_CREATE_USER */
export interface AdminCreateUserResponse {
  adminCreateUser: Pick<User, 'id' | 'email' | 'name' | 'isAdmin' | 'createdAt'>;
}

/** Input para ADMIN_UPDATE_USER */
export interface AdminUpdateUserInput {
  name?: string;
  isAdmin?: boolean;
  status?: 'ACTIVE' | 'INACTIVE';
}

/** Response de ADMIN_UPDATE_USER */
export interface AdminUpdateUserResponse {
  adminUpdateUser: Pick<User, 'id' | 'email' | 'name' | 'isAdmin' | 'status' | 'updatedAt'>;
}

/** Response de ADMIN_DISABLE_USER / ADMIN_ENABLE_USER */
export interface AdminToggleUserResponse {
  adminDisableUser?: Pick<User, 'id' | 'status' | 'updatedAt'>;
  adminEnableUser?: Pick<User, 'id' | 'status' | 'updatedAt'>;
}

/** Variáveis para UPDATE_PROFILE */
export interface UpdateProfileVariables {
  input: UpdateProfileInput;
}

/** Variáveis para ADMIN_CREATE_USER */
export interface AdminCreateUserVariables {
  input: AdminCreateUserInput;
}

/** Variáveis para ADMIN_UPDATE_USER */
export interface AdminUpdateUserVariables {
  id: string;
  input: AdminUpdateUserInput;
}

/** Variáveis para ADMIN_DISABLE_USER / ADMIN_ENABLE_USER */
export interface AdminToggleUserVariables {
  id: string;
}
