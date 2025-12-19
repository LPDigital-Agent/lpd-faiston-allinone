# Frontend Authentication Implementation

Documentação completa da implementação de autenticação no frontend do Faiston NEXO.

## Visão Geral

O sistema de autenticação frontend utiliza **AWS Cognito** com a biblioteca `amazon-cognito-identity-js` para comunicação direta com o User Pool, seguindo as diretrizes do projeto de **NÃO usar AWS Amplify**.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 15)                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Páginas   │  │ Componentes │  │      Providers          │  │
│  │   (auth)    │  │    Auth     │  │  (Apollo + Auth)        │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          │                                       │
│                   ┌──────▼──────┐                                │
│                   │ AuthContext │                                │
│                   │  (useAuth)  │                                │
│                   └──────┬──────┘                                │
│                          │                                       │
│         ┌────────────────┼────────────────┐                     │
│         │                │                │                      │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐             │
│  │ authService │  │ authErrors  │  │tokenRefresh │             │
│  └──────┬──────┘  └─────────────┘  └─────────────┘             │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────┐
│    AWS Cognito      │
│    User Pool        │
└─────────────────────┘
```

## Estrutura de Arquivos

```
client/
├── app/
│   ├── (auth)/                    # Route group para páginas de auth (sem sidebar)
│   │   ├── layout.tsx             # Layout sem sidebar
│   │   ├── login/page.tsx         # Página de login
│   │   ├── signup/page.tsx        # Página de cadastro
│   │   ├── confirm-signup/page.tsx # Confirmação de email
│   │   ├── forgot-password/page.tsx # Solicitar reset
│   │   ├── reset-password/page.tsx  # Redefinir senha
│   │   └── new-password/page.tsx    # Nova senha (admin-created users)
│   ├── (protected)/               # Route group para páginas protegidas
│   │   ├── layout.tsx             # Layout com AppShell
│   │   └── change-password/page.tsx # Alterar senha (autenticado)
│   └── layout.tsx                 # Root layout com Providers
├── components/
│   ├── auth/
│   │   ├── AuthLayout.tsx         # Layout glassmorphism
│   │   └── ProtectedRoute.tsx     # Proteção de rotas
│   ├── layout/
│   │   ├── header.tsx             # Header com dropdown user
│   │   ├── sidebar.tsx            # Sidebar com signout
│   │   └── app-shell.tsx          # Shell com ProtectedRoute
│   └── providers/
│       └── Providers.tsx          # Wrapper de providers
├── contexts/
│   └── AuthContext.tsx            # Context de autenticação
├── lib/
│   ├── config/
│   │   └── cognito.ts             # Configuração do Cognito
│   ├── graphql/
│   │   ├── queries.ts             # Queries GraphQL
│   │   └── mutations.ts           # Mutations GraphQL
│   └── apolloClient.ts            # Cliente Apollo
├── services/
│   └── authService.ts             # Serviço de autenticação
├── utils/
│   ├── authErrors.ts              # Tratamento de erros
│   ├── tokenRefresh.ts            # Refresh de tokens
│   └── newPasswordChallenge.ts    # Challenge de nova senha
├── .env.local                     # Variáveis de ambiente
└── .env.example                   # Template de variáveis
```

## Configuração

### Variáveis de Ambiente

```env
# AWS Cognito
NEXT_PUBLIC_AWS_REGION=us-east-2
NEXT_PUBLIC_USER_POOL_ID=your_user_pool_id
NEXT_PUBLIC_USER_POOL_CLIENT_ID=your_client_id

# GraphQL (AppSync)
NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://your-api.appsync-api.region.amazonaws.com/graphql
```

### Requisitos de Senha

O Cognito está configurado com os seguintes requisitos:
- Mínimo 8 caracteres
- Pelo menos 1 letra maiúscula
- Pelo menos 1 letra minúscula
- Pelo menos 1 número
- Pelo menos 1 caractere especial (!@#$%^&*)

## Uso

### Hook useAuth

```tsx
import { useAuth } from '@/contexts/AuthContext';

function MyComponent() {
  const {
    // Estado
    isAuthenticated,
    isLoading,
    user,

    // Métodos
    signUp,
    confirmSignUp,
    resendVerificationCode,
    signIn,
    signOut,
    forgotPassword,
    confirmForgotPassword,
    changePassword,
    refreshAuth,
  } = useAuth();

  // Uso
  if (isLoading) return <Loading />;
  if (!isAuthenticated) return <LoginPrompt />;

  return <div>Olá, {user?.name}</div>;
}
```

### Proteger Rotas

```tsx
// Opção 1: Usar AppShell (padrão - já protegido)
<AppShell>
  <MinhaPageProtegida />
</AppShell>

// Opção 2: Desabilitar proteção para páginas públicas
<AppShell requireAuth={false}>
  <PaginaPublica />
</AppShell>

// Opção 3: Usar ProtectedRoute diretamente
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

<ProtectedRoute>
  <ConteudoProtegido />
</ProtectedRoute>
```

### Fluxo de Login

```tsx
const { signIn } = useAuth();

try {
  const result = await signIn(email, password);

  if (result.success) {
    router.push('/');
  } else if (result.challengeName === 'NEW_PASSWORD_REQUIRED') {
    // Primeiro login - precisa trocar senha
    router.push('/change-password');
  }
} catch (error) {
  // Erro tratado automaticamente pelo authErrors
  console.error(error.message); // Mensagem em português
}
```

### Fluxo de Cadastro

```tsx
const { signUp, confirmSignUp } = useAuth();

// Passo 1: Cadastro
const result = await signUp(email, password, name);
if (result.userConfirmed === false) {
  // Email de confirmação enviado
  router.push(`/confirm-signup?email=${encodeURIComponent(email)}`);
}

// Passo 2: Confirmação (em outra página)
const confirmed = await confirmSignUp(email, code);
if (confirmed) {
  router.push('/login?verified=true');
}
```

### Fluxo de Recuperação de Senha

```tsx
const { forgotPassword, confirmForgotPassword } = useAuth();

// Passo 1: Solicitar código
await forgotPassword(email);
router.push(`/reset-password?email=${encodeURIComponent(email)}`);

// Passo 2: Redefinir senha (em outra página)
await confirmForgotPassword(email, code, newPassword);
router.push('/login?reset=true');
```

### Fluxo de Nova Senha (Usuários Criados por Admin)

Quando um admin cria um usuário no Cognito, o usuário recebe uma senha temporária
e precisa definir uma nova senha no primeiro login:

```tsx
// No login, o Cognito retorna NewPasswordRequired
try {
  await signIn({ email, password });
} catch (err) {
  if (err.code === 'NewPasswordRequired') {
    // Salvar dados do challenge
    saveNewPasswordChallenge(email, err.userAttributes, err.cognitoUser);
    // Redirecionar para página de nova senha
    router.push('/new-password');
  }
}

// Na página /new-password
import { completeNewPasswordChallenge } from '@/services/authService';

await completeNewPasswordChallenge(cognitoUser, newPassword);
router.push('/login?message=Senha definida com sucesso!');
```

### Fluxo de Alteração de Senha (Usuário Autenticado)

```tsx
const { changePassword } = useAuth();

// Requer senha atual para confirmar identidade
await changePassword(senhaAtual, novaSenha);
// Senha alterada com sucesso
```

## Apollo Client

O Apollo Client está configurado com:
- **httpLink**: Conexão com GraphQL endpoint
- **authLink**: Injeta token JWT automaticamente
- **errorLink**: Trata erros 401 (logout automático)

### Queries GraphQL

```tsx
import { useQuery } from '@apollo/client';
import { GET_ME } from '@/lib/graphql/queries';

function Profile() {
  const { data, loading, error } = useQuery(GET_ME);

  if (loading) return <Loading />;
  if (error) return <Error />;

  return <div>{data.me.name}</div>;
}
```

### Mutations GraphQL

```tsx
import { useMutation } from '@apollo/client';
import { UPDATE_PROFILE } from '@/lib/graphql/mutations';

function EditProfile() {
  const [updateProfile, { loading }] = useMutation(UPDATE_PROFILE);

  const handleSubmit = async (data) => {
    await updateProfile({
      variables: { input: data },
      refetchQueries: [{ query: GET_ME }],
    });
  };
}
```

## Tratamento de Erros

Todos os erros do Cognito são traduzidos para português:

| Código Cognito | Mensagem |
|----------------|----------|
| UserNotFoundException | Usuário não encontrado |
| NotAuthorizedException | Email ou senha incorretos |
| UsernameExistsException | Este email já está cadastrado |
| CodeMismatchException | Código de verificação inválido |
| ExpiredCodeException | Código de verificação expirado |
| InvalidPasswordException | Senha não atende aos requisitos |
| LimitExceededException | Muitas tentativas. Aguarde alguns minutos |

### Prevenção de Enumeração

Para `forgotPassword`, sempre retornamos mensagem genérica:
> "Se este email estiver cadastrado, você receberá um código de verificação."

## Tokens

### Estrutura

- **ID Token**: Contém claims do usuário (usado para GraphQL)
- **Access Token**: Autorização de acesso
- **Refresh Token**: Renovação de sessão (30 dias)

### Auto-Refresh

O sistema renova tokens automaticamente:
- Verifica expiração a cada 5 minutos
- Renova se faltar menos de 10 minutos para expirar
- Logout automático se refresh falhar

```tsx
// Iniciado automaticamente pelo AuthContext
// Pode ser controlado manualmente:
import { startAutoRefresh, stopAutoRefresh } from '@/utils/tokenRefresh';
```

## Páginas de Autenticação

### Design

Todas as páginas de auth usam:
- **AuthLayout**: Layout centralizado com glassmorphism
- **Logo Faiston**: Versão colorida no topo
- **Animações**: Framer Motion para transições suaves
- **Responsivo**: Mobile-first design

### URLs

| Página | URL | Descrição |
|--------|-----|-----------|
| Login | `/login` | Autenticação |
| Cadastro | `/signup` | Novo usuário |
| Confirmar Email | `/confirm-signup` | Código de verificação |
| Esqueci Senha | `/forgot-password` | Solicitar reset |
| Redefinir Senha | `/reset-password` | Nova senha |
| Nova Senha | `/new-password` | Primeiro login (admin-created) |
| Alterar Senha | `/change-password` | Usuário autenticado |

## Segurança

### Boas Práticas Implementadas

1. **Tokens em memória**: Não armazenamos tokens em localStorage
2. **HttpOnly cookies**: Refresh token seguro (quando usar backend)
3. **CSRF protection**: Validação de origem
4. **Rate limiting**: Tratamento de LimitExceededException
5. **Secure password**: Validação client-side antes de enviar
6. **Session timeout**: Logout após inatividade

### Headers de Segurança

O Apollo Client envia:
```
Authorization: Bearer <idToken>
Content-Type: application/json
```

## Dependências

```json
{
  "amazon-cognito-identity-js": "^6.3.12",
  "@apollo/client": "^3.12.3",
  "graphql": "^16.9.0"
}
```

## Troubleshooting

### "Usuário não confirmado"

O usuário precisa confirmar email antes de fazer login:
```tsx
if (error.code === 'UserNotConfirmedException') {
  router.push(`/confirm-signup?email=${email}`);
}
```

### "Token expirado"

O refresh automático deve renovar. Se falhar:
```tsx
const { refreshAuth } = useAuth();
await refreshAuth(); // Força renovação
```

### "Network error"

Verifique:
1. Variáveis de ambiente configuradas
2. CORS no Cognito/AppSync
3. Conectividade de rede

## Referências

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [amazon-cognito-identity-js](https://www.npmjs.com/package/amazon-cognito-identity-js)
- [Apollo Client Documentation](https://www.apollographql.com/docs/react/)
- [Next.js App Router](https://nextjs.org/docs/app)
