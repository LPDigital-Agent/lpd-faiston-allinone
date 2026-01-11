# Auditoria Profunda: Arquitetura de Agentes (Google ADK + AWS AgentCore)

**Status:** 🔴 CRÍTICO (Ação Necessária para Produção)
**Data:** 11/01/2026

Este documento detalha as descobertas da auditoria técnica profunda realizada na implementação dos agentes em `server/agentcore-inventory/`.

## 1. Integridade Arquitetural & Estado (Memória)

### 🔴 Falha Crítica: Persistência de Conversação
A implementação atual sofre de "Goldfish Memory" (Memória de Peixinho Dourado) em ambiente Serverless.

*   **O Problema:** O `BaseInventoryAgent` instancia um `InMemorySessionService` a cada invocação (`invoke`). Como o ambiente é AWS Lambda (efêmero), essa memória é apagada a cada requisição.
*   **A Ilusão:** Existe uma classe `SGASessionManager` (`tools/dynamodb_client.py`), mas ela armazena apenas **metadados** (última ação, contagem de turnos), e **não o histórico de mensagens**.
*   **Impacto:** O usuário não pode fazer perguntas de seguimento.
    *   *User:* "Onde está o Serial A?" -> *Agent:* "Em SP."
    *   *User:* "E qual o status dele?" -> *Agent:* "Desculpe, de quem estamos falando?"

### ✅ Concorrência e Isolamento
O código utiliza corretamente isolamento por requisição. Não há variáveis globais mutáveis que vazem dados entre usuários diferentes no mesmo container "quente" do Lambda.

## 2. Mecânica de Integração (Frameworks)

### 🟡 Padrão "Hybrid Router" (Roteador Híbrido)
A aplicação mistura dois padrões arquiteturais:
1.  **RPC (Remote Procedure Call):** Para ações como `process_nf_upload`, o código age como uma API clássica. Isso é **bom e performático**.
2.  **Agente Conversacional:** Para o Chat, a implementação está incompleta (`TODO` em `main.py:720`).

### 🟡 Propagação de Contexto
*   **User Identity:** O `user_id` é extraído corretamente do payload.
*   **Session ID:** O `session_id` é propagado, mas como não há persistência associada a ele no ADK, ele serve apenas para logs de auditoria no momento.

## 3. Segurança e Governança

### ✅ Fronteira de Autenticação
A segurança depende da Role IAM de execução do AgentCore. O código assume que se chegou até o handler, a requisição é legítima.
*   **Ponto Positivo:** Uso de `tools.s3_client` com reset de cliente para garantir credenciais frescas (SigV4).

## 4. Plano de Remediação (Roadmap Orientado)

Para tornar este sistema "Enterprise Grade" de verdade e funcional na AWS:

### Passo 1 (Imediato): Ponte de Memória (Memory Bridge)
Precisamos criar um adaptador que salve/carregue o histórico do ADK usando o DynamoDB ou os `sessionAttributes` do AgentCore.

**Solução Proposta:**
Criar `DynamoDBSessionService` implementando a interface `SessionService` do Google ADK.

```python
class DynamoDBSessionService(SessionService):
    def load_session(self, session_id):
        # Carrega histórico da tabela DynamoDB
        ...
    def save_session(self, session):
        # Salva novas mensagens
        ...
```

### Passo 2: Habilitar o Chat Genérico
Implementar o handler `_nexo_estoque_chat` usando o `Runner` do ADK conectado a este novo serviço de sessão.

### Passo 3: Refinamento do Router
Manter as ações específicas (`process_nf`) como estão (stateness desnecessário), e focar a persistência apenas na ação `chat`.

## Conclusão
O código tem bases sólidas de Engenharia de Software (Typos, Docstrings, Modularização), mas falha na arquitetura específica de **Agentes de Estado**. A implementação da persistência de sessão é o único bloqueador real para o "Go Live".
