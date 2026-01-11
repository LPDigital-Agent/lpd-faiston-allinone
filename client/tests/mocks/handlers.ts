/**
 * MSW Request Handlers
 *
 * Mock handlers for AgentCore API endpoints.
 */

import { http, HttpResponse } from 'msw';
import type { AgentRoomDataResponse } from '@/services/sgaAgentcore';

// Default mock data
export const mockAgentRoomData: AgentRoomDataResponse = {
  success: true,
  timestamp: new Date().toISOString(),
  agents: [
    {
      id: 'nexo_import',
      technicalName: 'NexoImportAgent',
      friendlyName: 'NEXO',
      description: 'Seu assistente principal de importação',
      avatar: 'Bot',
      color: 'magenta',
      status: 'disponivel',
      statusLabel: 'Disponível',
      lastActivity: 'Importei 47 itens há 5 min',
    },
    {
      id: 'intake',
      technicalName: 'IntakeAgent',
      friendlyName: 'Leitor de Notas',
      description: 'Lê e entende notas fiscais',
      avatar: 'FileText',
      color: 'blue',
      status: 'trabalhando',
      statusLabel: 'Trabalhando...',
      lastActivity: 'Processando NF 12345',
    },
  ],
  liveFeed: [
    {
      id: 'msg-1',
      timestamp: new Date(Date.now() - 60000).toISOString(),
      agentName: 'NEXO',
      message: 'Importei 47 itens da planilha estoque_2024.xlsx',
      type: 'success',
      eventType: 'import_completed',
    },
    {
      id: 'msg-2',
      timestamp: new Date(Date.now() - 120000).toISOString(),
      agentName: 'Leitor de Notas',
      message: 'Li a nota fiscal NF-12345 com 10 itens',
      type: 'info',
      eventType: 'nf_processed',
    },
  ],
  learningStories: [
    {
      id: 'story-1',
      learnedAt: new Date(Date.now() - 3600000).toISOString(),
      agentName: 'NEXO',
      story: 'Aprendi que arquivos da Empresa X sempre têm seriais na coluna "Serial Number"',
      confidence: 'alta',
    },
  ],
  activeWorkflow: {
    id: 'workflow-1',
    name: 'Importação de NF',
    startedAt: new Date(Date.now() - 300000).toISOString(),
    steps: [
      {
        id: 'step-1',
        label: 'Receber arquivo',
        icon: 'FileText',
        status: 'concluido',
      },
      {
        id: 'step-2',
        label: 'Analisar conteúdo',
        icon: 'Search',
        status: 'atual',
      },
      {
        id: 'step-3',
        label: 'Confirmar importação',
        icon: 'CheckCircle',
        status: 'pendente',
      },
    ],
  },
  pendingDecisions: [
    {
      id: 'decision-1',
      question: 'Encontrei um novo Part Number. Deseja criar?',
      options: [
        { label: 'Criar', action: 'create_pn' },
        { label: 'Ignorar', action: 'skip' },
      ],
      priority: 'alta',
      createdAt: new Date(Date.now() - 180000).toISOString(),
      taskType: 'part_number_approval',
      entityId: 'pending-pn-123',
    },
  ],
};

export const handlers = [
  // Match AgentCore invocations endpoint
  http.post('https://bedrock-agentcore.us-east-2.amazonaws.com/runtimes/*/invocations', async () => {
    return HttpResponse.json({
      data: mockAgentRoomData,
      sessionId: 'test-session-123',
    });
  }),
];

// Helper to create custom mock data
export function createMockAgentRoomData(
  overrides?: Partial<AgentRoomDataResponse>
): AgentRoomDataResponse {
  return {
    ...mockAgentRoomData,
    ...overrides,
  };
}
