# Frontend Authentication Guide

Complete guide for implementing AWS Cognito authentication in your React frontend for the Faiston Backend API.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Authentication Service](#authentication-service)
5. [React Integration](#react-integration)
6. [Authentication Flows](#authentication-flows)
7. [GraphQL API Integration](#graphql-api-integration)
8. [Error Handling](#error-handling)
9. [Security Best Practices](#security-best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  React Frontend │─────▶│  AWS Cognito    │─────▶│  DynamoDB       │
│                 │      │  (Auth)         │      │  (User Sync)    │
│                 │      │                 │      │                 │
└────────┬────────┘      └─────────────────┘      └─────────────────┘
         │
         │ (JWT Token)
         ▼
┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │
│  AWS AppSync    │─────▶│  DynamoDB       │
│  (GraphQL API)  │      │  (Data)         │
│                 │      │                 │
└─────────────────┘      └─────────────────┘
```

### What the Frontend Handles

| Operation | Method |
|-----------|--------|
| Sign Up | Cognito SDK |
| Confirm Sign Up (email verification) | Cognito SDK |
| Sign In | Cognito SDK |
| Sign Out | Cognito SDK |
| Forgot Password | Cognito SDK |
| Reset Password | Cognito SDK |
| Change Password | Cognito SDK |
| Get/Update Profile | GraphQL API |

### Security Features

- **SRP Authentication**: Password never sent over the network (zero-knowledge proof)
- **Token-based Auth**: JWT tokens validated by AppSync
- **Email Verification**: Required before account activation
- **User Enumeration Prevention**: Generic error messages protect user privacy

---

## Installation

```bash
# Core Cognito SDK
npm install amazon-cognito-identity-js

# For GraphQL API calls
npm install @apollo/client graphql

# TypeScript types (if using TypeScript)
npm install --save-dev @types/amazon-cognito-identity-js
```

---

## Configuration

### Environment Variables

Create a `.env` file (or `.env.local` for Next.js):

```env
# Get these values from CloudFormation outputs after deployment
REACT_APP_AWS_REGION=us-east-2
REACT_APP_USER_POOL_ID=YOUR_USER_POOL_ID
REACT_APP_USER_POOL_CLIENT_ID=YOUR_CLIENT_ID
REACT_APP_GRAPHQL_ENDPOINT=YOUR_GRAPHQL_ENDPOINT
```

### Cognito Configuration File

```typescript
// src/config/cognito.ts

export const cognitoConfig = {
  region: process.env.REACT_APP_AWS_REGION || 'us-east-2',
  userPoolId: process.env.REACT_APP_USER_POOL_ID || '',
  clientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || '',
  graphqlEndpoint: process.env.REACT_APP_GRAPHQL_ENDPOINT || '',
};

// Token validity (for reference)
export const tokenConfig = {
  accessTokenValidity: 60,  // minutes
  idTokenValidity: 60,      // minutes
  refreshTokenValidity: 30, // days
};

// Password requirements (for client-side validation)
export const passwordRequirements = {
  minLength: 8,
  requireUppercase: true,
  requireLowercase: true,
  requireNumbers: true,
  requireSymbols: true,
};
```

---

## Authentication Service

Complete TypeScript service class with all authentication methods:

```typescript
// src/services/authService.ts

import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
  CognitoUserSession,
  ISignUpResult,
} from 'amazon-cognito-identity-js';
import { cognitoConfig } from '../config/cognito';

// Initialize the User Pool
const userPool = new CognitoUserPool({
  UserPoolId: cognitoConfig.userPoolId,
  ClientId: cognitoConfig.clientId,
});

// Types
export interface SignUpParams {
  email: string;
  password: string;
  name?: string;
}

export interface SignInParams {
  email: string;
  password: string;
}

export interface AuthTokens {
  accessToken: string;
  idToken: string;
  refreshToken: string;
}

export interface UserAttributes {
  email: string;
  name?: string;
  sub: string; // Cognito user ID
}

// ============================================
// SIGN UP
// ============================================

export const signUp = (params: SignUpParams): Promise<ISignUpResult> => {
  return new Promise((resolve, reject) => {
    const { email, password, name } = params;

    const attributeList: CognitoUserAttribute[] = [
      new CognitoUserAttribute({ Name: 'email', Value: email }),
    ];

    if (name) {
      attributeList.push(
        new CognitoUserAttribute({ Name: 'name', Value: name })
      );
    }

    userPool.signUp(
      email, // username (email in our case)
      password,
      attributeList,
      [], // validation data
      (err, result) => {
        if (err) {
          reject(err);
          return;
        }
        if (!result) {
          reject(new Error('Sign up failed - no result returned'));
          return;
        }
        resolve(result);
      }
    );
  });
};

// ============================================
// CONFIRM SIGN UP (Email Verification)
// ============================================

export const confirmSignUp = (
  email: string,
  code: string
): Promise<string> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: userPool,
    });

    cognitoUser.confirmRegistration(code, true, (err, result) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(result);
    });
  });
};

// ============================================
// RESEND VERIFICATION CODE
// ============================================

export const resendVerificationCode = (email: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: userPool,
    });

    cognitoUser.resendConfirmationCode((err, result) => {
      if (err) {
        reject(err);
        return;
      }
      resolve();
    });
  });
};

// ============================================
// SIGN IN
// ============================================

export const signIn = (params: SignInParams): Promise<CognitoUserSession> => {
  return new Promise((resolve, reject) => {
    const { email, password } = params;

    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: userPool,
    });

    const authenticationDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: (session) => {
        resolve(session);
      },
      onFailure: (err) => {
        reject(err);
      },
      // Handle new password required (for admin-created users)
      newPasswordRequired: (userAttributes, requiredAttributes) => {
        // Remove non-mutable attributes
        delete userAttributes.email_verified;
        delete userAttributes.email;

        reject({
          code: 'NewPasswordRequired',
          message: 'New password required',
          userAttributes,
          requiredAttributes,
          cognitoUser, // Pass user for completing challenge
        });
      },
    });
  });
};

// ============================================
// COMPLETE NEW PASSWORD CHALLENGE
// ============================================

export const completeNewPasswordChallenge = (
  cognitoUser: CognitoUser,
  newPassword: string,
  userAttributes: Record<string, string> = {}
): Promise<CognitoUserSession> => {
  return new Promise((resolve, reject) => {
    cognitoUser.completeNewPasswordChallenge(newPassword, userAttributes, {
      onSuccess: (session) => {
        resolve(session);
      },
      onFailure: (err) => {
        reject(err);
      },
    });
  });
};

// ============================================
// SIGN OUT
// ============================================

export const signOut = (): void => {
  const cognitoUser = userPool.getCurrentUser();
  if (cognitoUser) {
    cognitoUser.signOut();
  }
};

// Global sign out (invalidates all sessions)
export const globalSignOut = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = userPool.getCurrentUser();
    if (!cognitoUser) {
      resolve();
      return;
    }

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session) {
        signOut();
        resolve();
        return;
      }

      cognitoUser.globalSignOut({
        onSuccess: () => {
          resolve();
        },
        onFailure: (err) => {
          reject(err);
        },
      });
    });
  });
};

// ============================================
// FORGOT PASSWORD
// ============================================

export const forgotPassword = (email: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: userPool,
    });

    cognitoUser.forgotPassword({
      onSuccess: () => {
        resolve();
      },
      onFailure: (err) => {
        reject(err);
      },
    });
  });
};

// ============================================
// CONFIRM FORGOT PASSWORD (Reset Password)
// ============================================

export const confirmForgotPassword = (
  email: string,
  code: string,
  newPassword: string
): Promise<void> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: userPool,
    });

    cognitoUser.confirmPassword(code, newPassword, {
      onSuccess: () => {
        resolve();
      },
      onFailure: (err) => {
        reject(err);
      },
    });
  });
};

// ============================================
// CHANGE PASSWORD (Authenticated User)
// ============================================

export const changePassword = (
  oldPassword: string,
  newPassword: string
): Promise<void> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = userPool.getCurrentUser();
    if (!cognitoUser) {
      reject(new Error('No user is currently signed in'));
      return;
    }

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session) {
        reject(err || new Error('No valid session'));
        return;
      }

      cognitoUser.changePassword(oldPassword, newPassword, (err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve();
      });
    });
  });
};

// ============================================
// GET CURRENT USER
// ============================================

export const getCurrentUser = (): CognitoUser | null => {
  return userPool.getCurrentUser();
};

// ============================================
// GET CURRENT SESSION
// ============================================

export const getCurrentSession = (): Promise<CognitoUserSession | null> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = userPool.getCurrentUser();
    if (!cognitoUser) {
      resolve(null);
      return;
    }

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(session);
    });
  });
};

// ============================================
// GET TOKENS
// ============================================

export const getTokens = async (): Promise<AuthTokens | null> => {
  const session = await getCurrentSession();
  if (!session) {
    return null;
  }

  return {
    accessToken: session.getAccessToken().getJwtToken(),
    idToken: session.getIdToken().getJwtToken(),
    refreshToken: session.getRefreshToken().getToken(),
  };
};

// Get ID Token (for GraphQL API calls)
export const getIdToken = async (): Promise<string | null> => {
  const tokens = await getTokens();
  return tokens?.idToken || null;
};

// Get Access Token
export const getAccessToken = async (): Promise<string | null> => {
  const tokens = await getTokens();
  return tokens?.accessToken || null;
};

// ============================================
// GET USER ATTRIBUTES
// ============================================

export const getUserAttributes = (): Promise<UserAttributes | null> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = userPool.getCurrentUser();
    if (!cognitoUser) {
      resolve(null);
      return;
    }

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session) {
        resolve(null);
        return;
      }

      cognitoUser.getUserAttributes((err, attributes) => {
        if (err) {
          reject(err);
          return;
        }

        if (!attributes) {
          resolve(null);
          return;
        }

        const userAttrs: UserAttributes = {
          email: '',
          sub: '',
        };

        attributes.forEach((attr) => {
          if (attr.Name === 'email') userAttrs.email = attr.Value;
          if (attr.Name === 'name') userAttrs.name = attr.Value;
          if (attr.Name === 'sub') userAttrs.sub = attr.Value;
        });

        resolve(userAttrs);
      });
    });
  });
};

// ============================================
// CHECK IF USER IS AUTHENTICATED
// ============================================

export const isAuthenticated = async (): Promise<boolean> => {
  try {
    const session = await getCurrentSession();
    return session !== null && session.isValid();
  } catch {
    return false;
  }
};

// ============================================
// REFRESH SESSION
// ============================================

export const refreshSession = (): Promise<CognitoUserSession> => {
  return new Promise((resolve, reject) => {
    const cognitoUser = userPool.getCurrentUser();
    if (!cognitoUser) {
      reject(new Error('No user is currently signed in'));
      return;
    }

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session) {
        reject(err || new Error('No valid session'));
        return;
      }

      const refreshToken = session.getRefreshToken();

      cognitoUser.refreshSession(refreshToken, (err, newSession) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(newSession);
      });
    });
  });
};
```

---

## React Integration

### Auth Context and Provider

```typescript
// src/contexts/AuthContext.tsx

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import {
  signUp as authSignUp,
  confirmSignUp as authConfirmSignUp,
  signIn as authSignIn,
  signOut as authSignOut,
  forgotPassword as authForgotPassword,
  confirmForgotPassword as authConfirmForgotPassword,
  changePassword as authChangePassword,
  getCurrentSession,
  getUserAttributes,
  isAuthenticated as checkIsAuthenticated,
  resendVerificationCode as authResendCode,
  SignUpParams,
  SignInParams,
  UserAttributes,
} from '../services/authService';

// Types
interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserAttributes | null;
}

interface AuthContextType extends AuthState {
  signUp: (params: SignUpParams) => Promise<void>;
  confirmSignUp: (email: string, code: string) => Promise<void>;
  resendVerificationCode: (email: string) => Promise<void>;
  signIn: (params: SignInParams) => Promise<void>;
  signOut: () => void;
  forgotPassword: (email: string) => Promise<void>;
  confirmForgotPassword: (email: string, code: string, newPassword: string) => Promise<void>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider Component
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
  });

  // Check authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const authenticated = await checkIsAuthenticated();
      if (authenticated) {
        const userAttrs = await getUserAttributes();
        setState({
          isAuthenticated: true,
          isLoading: false,
          user: userAttrs,
        });
      } else {
        setState({
          isAuthenticated: false,
          isLoading: false,
          user: null,
        });
      }
    } catch (error) {
      setState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
      });
    }
  };

  const signUp = async (params: SignUpParams): Promise<void> => {
    await authSignUp(params);
    // User needs to confirm email before signing in
  };

  const confirmSignUp = async (email: string, code: string): Promise<void> => {
    await authConfirmSignUp(email, code);
  };

  const resendVerificationCode = async (email: string): Promise<void> => {
    await authResendCode(email);
  };

  const signIn = async (params: SignInParams): Promise<void> => {
    await authSignIn(params);
    const userAttrs = await getUserAttributes();
    setState({
      isAuthenticated: true,
      isLoading: false,
      user: userAttrs,
    });
  };

  const signOut = useCallback(() => {
    authSignOut();
    setState({
      isAuthenticated: false,
      isLoading: false,
      user: null,
    });
  }, []);

  const forgotPassword = async (email: string): Promise<void> => {
    await authForgotPassword(email);
  };

  const confirmForgotPassword = async (
    email: string,
    code: string,
    newPassword: string
  ): Promise<void> => {
    await authConfirmForgotPassword(email, code, newPassword);
  };

  const changePassword = async (
    oldPassword: string,
    newPassword: string
  ): Promise<void> => {
    await authChangePassword(oldPassword, newPassword);
  };

  const refreshAuth = async (): Promise<void> => {
    await checkAuthStatus();
  };

  const value: AuthContextType = {
    ...state,
    signUp,
    confirmSignUp,
    resendVerificationCode,
    signIn,
    signOut,
    forgotPassword,
    confirmForgotPassword,
    changePassword,
    refreshAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom Hook
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### Protected Route Component

```typescript
// src/components/ProtectedRoute.tsx

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // Show loading spinner while checking auth status
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login with return URL
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
```

### App Setup

```typescript
// src/App.tsx

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';

// Pages
import { LoginPage } from './pages/LoginPage';
import { SignUpPage } from './pages/SignUpPage';
import { ConfirmSignUpPage } from './pages/ConfirmSignUpPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProfilePage } from './pages/ProfilePage';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/confirm-signup" element={<ConfirmSignUpPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};
```

---

## Authentication Flows

### Sign Up Flow

```typescript
// src/pages/SignUpPage.tsx

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { passwordRequirements } from '../config/cognito';

export const SignUpPage: React.FC = () => {
  const navigate = useNavigate();
  const { signUp } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Client-side password validation
  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < passwordRequirements.minLength) {
      return `Password must be at least ${passwordRequirements.minLength} characters`;
    }
    if (passwordRequirements.requireUppercase && !/[A-Z]/.test(pwd)) {
      return 'Password must contain an uppercase letter';
    }
    if (passwordRequirements.requireLowercase && !/[a-z]/.test(pwd)) {
      return 'Password must contain a lowercase letter';
    }
    if (passwordRequirements.requireNumbers && !/[0-9]/.test(pwd)) {
      return 'Password must contain a number';
    }
    if (passwordRequirements.requireSymbols && !/[^A-Za-z0-9]/.test(pwd)) {
      return 'Password must contain a special character';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate password
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    setIsLoading(true);

    try {
      await signUp({ email, password, name });
      // Navigate to confirmation page with email
      navigate('/confirm-signup', { state: { email } });
    } catch (err: any) {
      setError(err.message || 'Sign up failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h1>Create Account</h1>

      {error && <div className="error">{error}</div>}

      <input
        type="text"
        placeholder="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      <p className="text-sm text-gray-600">
        Password must be at least 8 characters with uppercase, lowercase, number, and symbol.
      </p>

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Creating account...' : 'Sign Up'}
      </button>
    </form>
  );
};
```

### Confirm Sign Up (Email Verification)

```typescript
// src/pages/ConfirmSignUpPage.tsx

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const ConfirmSignUpPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { confirmSignUp, resendVerificationCode } = useAuth();

  // Get email from navigation state
  const email = location.state?.email || '';

  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await confirmSignUp(email, code);
      navigate('/login', {
        state: { message: 'Email verified! You can now sign in.' },
      });
    } catch (err: any) {
      setError(err.message || 'Verification failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendCode = async () => {
    setError('');
    setMessage('');

    try {
      await resendVerificationCode(email);
      setMessage('A new verification code has been sent to your email.');
    } catch (err: any) {
      setError(err.message || 'Failed to resend code');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h1>Verify Your Email</h1>

      <p>Enter the 6-digit code sent to {email}</p>

      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}

      <input
        type="text"
        placeholder="Verification Code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        maxLength={6}
        required
      />

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Verifying...' : 'Verify Email'}
      </button>

      <button type="button" onClick={handleResendCode}>
        Resend Code
      </button>
    </form>
  );
};
```

### Sign In Flow

```typescript
// src/pages/LoginPage.tsx

import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Get success message from navigation state
  const successMessage = location.state?.message;

  // Get return URL
  const from = location.state?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await signIn({ email, password });
      navigate(from, { replace: true });
    } catch (err: any) {
      // Handle specific error codes
      switch (err.code) {
        case 'UserNotConfirmedException':
          navigate('/confirm-signup', { state: { email } });
          break;
        case 'NewPasswordRequired':
          // Handle new password challenge for admin-created users
          navigate('/new-password', {
            state: {
              email,
              cognitoUser: err.cognitoUser,
              userAttributes: err.userAttributes,
            },
          });
          break;
        case 'NotAuthorizedException':
        case 'UserNotFoundException':
          // Generic message to prevent user enumeration
          setError('Invalid email or password');
          break;
        default:
          setError(err.message || 'Sign in failed');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h1>Sign In</h1>

      {successMessage && <div className="success">{successMessage}</div>}
      {error && <div className="error">{error}</div>}

      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Signing in...' : 'Sign In'}
      </button>

      <div className="links">
        <Link to="/forgot-password">Forgot password?</Link>
        <Link to="/signup">Create an account</Link>
      </div>
    </form>
  );
};
```

### Forgot Password Flow

```typescript
// src/pages/ForgotPasswordPage.tsx

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const ForgotPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const { forgotPassword } = useAuth();

  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await forgotPassword(email);
      navigate('/reset-password', { state: { email } });
    } catch (err: any) {
      // Always show success message to prevent user enumeration
      // Even if user doesn't exist, we show the same message
      navigate('/reset-password', { state: { email } });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h1>Forgot Password</h1>

      <p>Enter your email and we'll send you a reset code.</p>

      {error && <div className="error">{error}</div>}

      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Sending...' : 'Send Reset Code'}
      </button>
    </form>
  );
};
```

### Reset Password Flow

```typescript
// src/pages/ResetPasswordPage.tsx

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { passwordRequirements } from '../config/cognito';

export const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { confirmForgotPassword } = useAuth();

  const email = location.state?.email || '';

  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      await confirmForgotPassword(email, code, newPassword);
      navigate('/login', {
        state: { message: 'Password reset successfully. Please sign in.' },
      });
    } catch (err: any) {
      setError(err.message || 'Password reset failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h1>Reset Password</h1>

      <p>Enter the code sent to {email} and your new password.</p>

      {error && <div className="error">{error}</div>}

      <input
        type="text"
        placeholder="Reset Code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        maxLength={6}
        required
      />

      <input
        type="password"
        placeholder="New Password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
      />

      <input
        type="password"
        placeholder="Confirm New Password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        required
      />

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Resetting...' : 'Reset Password'}
      </button>
    </form>
  );
};
```

### Change Password (Authenticated)

```typescript
// src/pages/ChangePasswordPage.tsx

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

export const ChangePasswordPage: React.FC = () => {
  const { changePassword } = useAuth();

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      await changePassword(oldPassword, newPassword);
      setSuccess('Password changed successfully');
      // Clear form
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err.message || 'Password change failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h1>Change Password</h1>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <input
        type="password"
        placeholder="Current Password"
        value={oldPassword}
        onChange={(e) => setOldPassword(e.target.value)}
        required
      />

      <input
        type="password"
        placeholder="New Password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
      />

      <input
        type="password"
        placeholder="Confirm New Password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        required
      />

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Changing...' : 'Change Password'}
      </button>
    </form>
  );
};
```

---

## GraphQL API Integration

### Apollo Client Setup

```typescript
// src/lib/apolloClient.ts

import {
  ApolloClient,
  InMemoryCache,
  createHttpLink,
  ApolloLink,
} from '@apollo/client';
import { setContext } from '@apollo/client/link/context';
import { onError } from '@apollo/client/link/error';
import { getIdToken, signOut } from '../services/authService';
import { cognitoConfig } from '../config/cognito';

// HTTP Link
const httpLink = createHttpLink({
  uri: cognitoConfig.graphqlEndpoint,
});

// Auth Link - Add JWT token to requests
const authLink = setContext(async (_, { headers }) => {
  try {
    const token = await getIdToken();
    return {
      headers: {
        ...headers,
        authorization: token || '',
      },
    };
  } catch (error) {
    return { headers };
  }
});

// Error Link - Handle authentication errors
const errorLink = onError(({ graphQLErrors, networkError }) => {
  if (graphQLErrors) {
    for (const err of graphQLErrors) {
      // Handle unauthorized errors
      if (
        err.extensions?.code === 'UNAUTHENTICATED' ||
        err.message.includes('Unauthorized')
      ) {
        signOut();
        window.location.href = '/login';
      }
    }
  }

  if (networkError) {
    console.error('Network error:', networkError);
  }
});

// Create Apollo Client
export const apolloClient = new ApolloClient({
  link: ApolloLink.from([errorLink, authLink, httpLink]),
  cache: new InMemoryCache(),
  defaultOptions: {
    watchQuery: {
      fetchPolicy: 'cache-and-network',
    },
  },
});
```

### GraphQL Queries and Mutations

```typescript
// src/graphql/queries.ts

import { gql } from '@apollo/client';

// Get current user profile
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

// List all users (Admin only)
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
```

```typescript
// src/graphql/mutations.ts

import { gql } from '@apollo/client';

// Update user profile
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

// Admin: Create new user
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
```

### Using GraphQL in Components

```typescript
// src/pages/ProfilePage.tsx

import React, { useState } from 'react';
import { useQuery, useMutation } from '@apollo/client';
import { GET_ME } from '../graphql/queries';
import { UPDATE_PROFILE } from '../graphql/mutations';
import { useAuth } from '../contexts/AuthContext';

interface User {
  id: string;
  email: string;
  name: string;
  isAdmin: boolean;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export const ProfilePage: React.FC = () => {
  const { signOut } = useAuth();

  // Fetch user profile
  const { data, loading, error, refetch } = useQuery<{ me: User }>(GET_ME);

  // Update profile mutation
  const [updateProfile, { loading: updating }] = useMutation(UPDATE_PROFILE, {
    onCompleted: () => {
      refetch();
      setIsEditing(false);
    },
  });

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState('');

  const handleEdit = () => {
    setName(data?.me.name || '');
    setIsEditing(true);
  };

  const handleSave = async () => {
    await updateProfile({
      variables: {
        input: { name },
      },
    });
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  const user = data?.me;

  return (
    <div className="profile">
      <h1>Profile</h1>

      {isEditing ? (
        <div>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name"
          />
          <button onClick={handleSave} disabled={updating}>
            {updating ? 'Saving...' : 'Save'}
          </button>
          <button onClick={() => setIsEditing(false)}>Cancel</button>
        </div>
      ) : (
        <div>
          <p><strong>Email:</strong> {user?.email}</p>
          <p><strong>Name:</strong> {user?.name || 'Not set'}</p>
          <p><strong>Admin:</strong> {user?.isAdmin ? 'Yes' : 'No'}</p>
          <p><strong>Member since:</strong> {new Date(user?.createdAt).toLocaleDateString()}</p>
          <button onClick={handleEdit}>Edit Profile</button>
        </div>
      )}

      <hr />

      <button onClick={signOut}>Sign Out</button>
    </div>
  );
};
```

### App with Apollo Provider

```typescript
// src/App.tsx (updated)

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ApolloProvider } from '@apollo/client';
import { apolloClient } from './lib/apolloClient';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
// ... import pages

export const App: React.FC = () => {
  return (
    <ApolloProvider client={apolloClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* ... routes */}
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ApolloProvider>
  );
};
```

---

## Error Handling

### Error Codes Reference

| Error Code | Meaning | Recommended Action |
|------------|---------|-------------------|
| `UserNotConfirmedException` | Email not verified | Redirect to confirmation page |
| `NotAuthorizedException` | Wrong password OR user doesn't exist | Show "Invalid credentials" (generic) |
| `UserNotFoundException` | User doesn't exist | Show "Invalid credentials" (generic) |
| `UsernameExistsException` | Email already registered | Suggest sign in or password reset |
| `CodeMismatchException` | Wrong verification/reset code | Ask user to retry |
| `ExpiredCodeException` | Verification/reset code expired | Offer to resend code |
| `LimitExceededException` | Too many attempts | Show cooldown message |
| `InvalidPasswordException` | Password doesn't meet policy | Show password requirements |
| `InvalidParameterException` | Invalid input format | Validate input client-side |
| `TooManyRequestsException` | Rate limited | Implement exponential backoff |
| `NewPasswordRequired` | Admin-created user first login | Redirect to new password flow |

### Error Handler Utility

```typescript
// src/utils/authErrors.ts

export interface AuthError {
  code: string;
  message: string;
  userMessage: string;
  action?: 'redirect' | 'resend' | 'retry' | 'wait';
  redirectTo?: string;
}

export const handleAuthError = (error: any, email?: string): AuthError => {
  const code = error.code || error.name || 'UnknownError';

  switch (code) {
    case 'UserNotConfirmedException':
      return {
        code,
        message: error.message,
        userMessage: 'Please verify your email address before signing in.',
        action: 'redirect',
        redirectTo: '/confirm-signup',
      };

    case 'NotAuthorizedException':
    case 'UserNotFoundException':
      return {
        code,
        message: error.message,
        userMessage: 'Invalid email or password.',
        action: 'retry',
      };

    case 'UsernameExistsException':
      return {
        code,
        message: error.message,
        userMessage: 'An account with this email already exists.',
        action: 'redirect',
        redirectTo: '/login',
      };

    case 'CodeMismatchException':
      return {
        code,
        message: error.message,
        userMessage: 'Invalid verification code. Please check and try again.',
        action: 'retry',
      };

    case 'ExpiredCodeException':
      return {
        code,
        message: error.message,
        userMessage: 'This code has expired. Please request a new one.',
        action: 'resend',
      };

    case 'LimitExceededException':
    case 'TooManyRequestsException':
      return {
        code,
        message: error.message,
        userMessage: 'Too many attempts. Please wait a few minutes and try again.',
        action: 'wait',
      };

    case 'InvalidPasswordException':
      return {
        code,
        message: error.message,
        userMessage:
          'Password must be at least 8 characters with uppercase, lowercase, number, and symbol.',
        action: 'retry',
      };

    case 'NewPasswordRequired':
      return {
        code,
        message: error.message,
        userMessage: 'You need to set a new password.',
        action: 'redirect',
        redirectTo: '/new-password',
      };

    default:
      return {
        code,
        message: error.message || 'An unexpected error occurred',
        userMessage: 'Something went wrong. Please try again.',
        action: 'retry',
      };
  }
};
```

---

## Security Best Practices

### 1. Token Storage

```typescript
// The Cognito SDK uses localStorage by default.
// For enhanced security, you can implement a custom storage:

// src/utils/secureStorage.ts

class SecureStorage {
  private storage: Map<string, string> = new Map();

  setItem(key: string, value: string): void {
    this.storage.set(key, value);
  }

  getItem(key: string): string | null {
    return this.storage.get(key) || null;
  }

  removeItem(key: string): void {
    this.storage.delete(key);
  }

  clear(): void {
    this.storage.clear();
  }
}

export const secureStorage = new SecureStorage();

// Use with Cognito:
const userPool = new CognitoUserPool({
  UserPoolId: cognitoConfig.userPoolId,
  ClientId: cognitoConfig.clientId,
  Storage: secureStorage, // Use in-memory storage
});
```

### 2. Token Refresh Strategy

```typescript
// src/utils/tokenRefresh.ts

import { refreshSession, getTokens } from '../services/authService';

// Check and refresh tokens before they expire
export const ensureValidToken = async (): Promise<string | null> => {
  const tokens = await getTokens();
  if (!tokens) return null;

  // Decode token to check expiry (without verification - just for timing)
  const payload = JSON.parse(atob(tokens.idToken.split('.')[1]));
  const expiresAt = payload.exp * 1000;
  const now = Date.now();

  // Refresh if token expires within 5 minutes
  if (expiresAt - now < 5 * 60 * 1000) {
    try {
      await refreshSession();
      const newTokens = await getTokens();
      return newTokens?.idToken || null;
    } catch (error) {
      // Refresh failed - user needs to sign in again
      return null;
    }
  }

  return tokens.idToken;
};
```

### 3. Prevent User Enumeration

```typescript
// Always show generic error messages for auth failures
// GOOD:
setError('Invalid email or password');

// BAD:
setError('User does not exist'); // Reveals that email is not registered
setError('Incorrect password');  // Reveals that email IS registered
```

### 4. Secure Password Handling

```typescript
// Never log passwords
console.log('Login attempt for:', email); // OK
console.log('Login with:', email, password); // NEVER DO THIS

// Clear password from state after use
const handleSubmit = async () => {
  try {
    await signIn({ email, password });
  } finally {
    setPassword(''); // Clear password from memory
  }
};
```

### 5. CSRF Protection

```typescript
// Apollo Client automatically includes credentials
// For custom fetch requests, include credentials:
fetch(url, {
  method: 'POST',
  credentials: 'include', // Include cookies
  headers: {
    'Content-Type': 'application/json',
    'Authorization': token,
  },
  body: JSON.stringify(data),
});
```

---

## Troubleshooting

### Common Issues

#### 1. "User pool client does not have a secret"

This is expected. The Cognito client is configured as a public client (no secret) for frontend use. This is correct for SPA applications.

#### 2. "Network request failed"

```typescript
// Check if the GraphQL endpoint is correct
console.log('GraphQL endpoint:', cognitoConfig.graphqlEndpoint);

// Ensure CORS is configured on AppSync (it is by default)
```

#### 3. "NotAuthorizedException" on valid credentials

```typescript
// User might not be confirmed
try {
  await signIn(credentials);
} catch (error) {
  if (error.code === 'UserNotConfirmedException') {
    // Redirect to confirmation page
    navigate('/confirm-signup', { state: { email } });
  }
}
```

#### 4. Token expired during session

```typescript
// Implement automatic token refresh in Apollo
const authLink = setContext(async (_, { headers }) => {
  // Use ensureValidToken instead of getIdToken
  const token = await ensureValidToken();
  if (!token) {
    // Redirect to login
    window.location.href = '/login';
    return { headers };
  }
  return {
    headers: {
      ...headers,
      authorization: token,
    },
  };
});
```

#### 5. "InvalidParameterException: Missing required parameter"

```typescript
// Ensure all required fields are provided
const attributeList = [
  new CognitoUserAttribute({ Name: 'email', Value: email }),
  // Name is optional in our schema
];
```

### Debug Mode

```typescript
// Enable console logging for debugging
const DEBUG = process.env.NODE_ENV === 'development';

export const debugLog = (...args: any[]) => {
  if (DEBUG) {
    console.log('[Auth Debug]', ...args);
  }
};

// Usage in authService.ts
export const signIn = async (params: SignInParams) => {
  debugLog('Attempting sign in for:', params.email);
  // ...
};
```

---

## Quick Reference

### Configuration Checklist

- [ ] Set `REACT_APP_USER_POOL_ID` from CloudFormation output `UserPoolId`
- [ ] Set `REACT_APP_USER_POOL_CLIENT_ID` from CloudFormation output `UserPoolClientId`
- [ ] Set `REACT_APP_GRAPHQL_ENDPOINT` from CloudFormation output `GraphQLEndpoint`
- [ ] Set `REACT_APP_AWS_REGION` to `us-east-2`

### Token Validity

| Token | Validity | Use For |
|-------|----------|---------|
| Access Token | 60 minutes | API authorization (not used with AppSync) |
| ID Token | 60 minutes | GraphQL API calls (AppSync) |
| Refresh Token | 30 days | Getting new access/ID tokens |

### Password Requirements

- Minimum 8 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)
- At least 1 number (0-9)
- At least 1 special character (!@#$%^&*...)

---

## Getting CloudFormation Outputs

After deployment, get your configuration values:

```bash
# Using AWS CLI
aws cloudformation describe-stacks \
  --stack-name faiston-backend-prod \
  --query 'Stacks[0].Outputs' \
  --output table
```

Or check the GitHub Actions deployment logs for the output values.
