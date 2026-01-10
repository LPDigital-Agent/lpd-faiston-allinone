/**
 * Agent Room Constants - Sala de Transparência
 *
 * Human-friendly agent profiles, status labels, and colors.
 * All text is in Portuguese for user-facing content.
 */

import {
  Bot,
  FileText,
  Upload,
  Shield,
  Brain,
  Send,
  Truck,
  Package,
  Search,
  Database,
  RotateCcw,
  Scale,
  Bell,
  Sparkles,
  Zap,
  Eye,
} from "lucide-react";
import type { AgentFriendlyStatus, AgentProfileConfig, LiveMessageType } from "./agentRoomTypes";

// =============================================================================
// Agent Profiles
// =============================================================================

/**
 * Configuration for each agent's display in the Agent Room.
 * Maps technical agent names to user-friendly profiles.
 */
export const AGENT_PROFILES: Record<string, AgentProfileConfig> = {
  // Primary SGA Agents
  nexo_import: {
    friendlyName: "NEXO",
    description: "Seu assistente principal de importação",
    icon: Bot,
    color: "magenta",
  },
  intake: {
    friendlyName: "Leitor de Notas",
    description: "Lê e entende notas fiscais",
    icon: FileText,
    color: "blue",
  },
  import: {
    friendlyName: "Importador",
    description: "Traz seus dados para o sistema",
    icon: Upload,
    color: "cyan",
  },
  compliance: {
    friendlyName: "Validador",
    description: "Verifica se tudo está correto",
    icon: Shield,
    color: "green",
  },
  learning: {
    friendlyName: "Memória",
    description: "Aprende com cada interação",
    icon: Brain,
    color: "purple",
  },
  expedition: {
    friendlyName: "Despachante",
    description: "Cuida das expedições",
    icon: Send,
    color: "orange",
  },
  carrier: {
    friendlyName: "Logística",
    description: "Gerencia transportadoras",
    icon: Truck,
    color: "yellow",
  },
  stock_control: {
    friendlyName: "Controlador",
    description: "Cuida do estoque",
    icon: Package,
    color: "cyan",
  },
  // Alias for backend compatibility
  estoque_control: {
    friendlyName: "Controlador",
    description: "Cuida do estoque",
    icon: Package,
    color: "cyan",
  },

  // Supporting Agents
  search: {
    friendlyName: "Pesquisador",
    description: "Encontra informações rapidamente",
    icon: Search,
    color: "blue",
  },
  schema_evolution: {
    friendlyName: "Arquiteto",
    description: "Adapta a estrutura de dados",
    icon: Database,
    color: "purple",
  },
  reverse_logistics: {
    friendlyName: "Reversa",
    description: "Processa devoluções",
    icon: RotateCcw,
    color: "orange",
  },
  // Alias for backend compatibility
  reverse: {
    friendlyName: "Reversa",
    description: "Processa devoluções e retornos",
    icon: RotateCcw,
    color: "orange",
  },
  inventory_count: {
    friendlyName: "Contador",
    description: "Realiza inventários",
    icon: Scale,
    color: "green",
  },
  notification: {
    friendlyName: "Notificador",
    description: "Mantém você informado",
    icon: Bell,
    color: "yellow",
  },
  analytics: {
    friendlyName: "Analista",
    description: "Gera insights e relatórios",
    icon: Sparkles,
    color: "magenta",
  },
  automation: {
    friendlyName: "Automação",
    description: "Executa tarefas automáticas",
    icon: Zap,
    color: "cyan",
  },
  supervisor: {
    friendlyName: "Supervisor",
    description: "Coordena os outros agentes",
    icon: Eye,
    color: "zinc",
  },

  // Backend agents (additional)
  observation: {
    friendlyName: "Observador",
    description: "Monitora mudanças no estoque",
    icon: Eye,
    color: "green",
  },
  equipment_research: {
    friendlyName: "Pesquisador de Equipamentos",
    description: "Busca informações de equipamentos",
    icon: Search,
    color: "orange",
  },
  comunicacao: {
    friendlyName: "Comunicador",
    description: "Envia notificações e alertas",
    icon: Bell,
    color: "magenta",
  },
  reconciliacao: {
    friendlyName: "Reconciliador",
    description: "Detecta divergências no estoque",
    icon: Scale,
    color: "yellow",
  },
};

/**
 * Maps technical agent names to their profile keys.
 */
export const AGENT_NAME_MAP: Record<string, string> = {
  NexoImportAgent: "nexo_import",
  IntakeAgent: "intake",
  ImportAgent: "import",
  ComplianceAgent: "compliance",
  LearningAgent: "learning",
  ExpeditionAgent: "expedition",
  CarrierAgent: "carrier",
  EstoqueControlAgent: "stock_control",
  SearchAgent: "search",
  SchemaEvolutionAgent: "schema_evolution",
  ReverseLogisticsAgent: "reverse_logistics",
  InventoryCountAgent: "inventory_count",
  NotificationAgent: "notification",
  AnalyticsAgent: "analytics",
  AutomationAgent: "automation",
  SupervisorAgent: "supervisor",
};

// =============================================================================
// Status Configuration
// =============================================================================

/**
 * User-friendly status labels in Portuguese.
 */
export const STATUS_LABELS: Record<AgentFriendlyStatus, string> = {
  disponivel: "Disponível",
  trabalhando: "Trabalhando...",
  esperando_voce: "Esperando você",
  problema: "Encontrou um problema",
  descansando: "Descansando",
};

/**
 * Status indicator colors (for the dot/badge).
 */
export const STATUS_DOT_COLORS: Record<AgentFriendlyStatus, string> = {
  disponivel: "bg-green-500",
  trabalhando: "bg-blue-500 animate-pulse",
  esperando_voce: "bg-yellow-500 animate-pulse",
  problema: "bg-red-500",
  descansando: "bg-zinc-400",
};

/**
 * Status badge colors (background + text).
 */
export const STATUS_BADGE_COLORS: Record<AgentFriendlyStatus, string> = {
  disponivel: "bg-green-500/20 text-green-400 border-green-500/30",
  trabalhando: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  esperando_voce: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  problema: "bg-red-500/20 text-red-400 border-red-500/30",
  descansando: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

// =============================================================================
// Message Type Configuration
// =============================================================================

/**
 * Live message type colors.
 */
export const MESSAGE_TYPE_COLORS: Record<LiveMessageType, string> = {
  info: "border-l-blue-500 bg-blue-500/5",
  success: "border-l-green-500 bg-green-500/5",
  warning: "border-l-yellow-500 bg-yellow-500/5",
  action_needed: "border-l-magenta-mid bg-magenta-mid/5",
};

/**
 * Live message type icons (icon names).
 */
export const MESSAGE_TYPE_ICONS: Record<LiveMessageType, string> = {
  info: "Info",
  success: "CheckCircle",
  warning: "AlertTriangle",
  action_needed: "Hand",
};

// =============================================================================
// Agent Color Configuration
// =============================================================================

/**
 * Agent color palette (Tailwind classes).
 */
export const AGENT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  magenta: {
    bg: "bg-magenta-mid/20",
    text: "text-magenta-light",
    border: "border-magenta-mid/30",
  },
  blue: {
    bg: "bg-blue-500/20",
    text: "text-blue-400",
    border: "border-blue-500/30",
  },
  cyan: {
    bg: "bg-cyan-500/20",
    text: "text-cyan-400",
    border: "border-cyan-500/30",
  },
  green: {
    bg: "bg-green-500/20",
    text: "text-green-400",
    border: "border-green-500/30",
  },
  purple: {
    bg: "bg-purple-500/20",
    text: "text-purple-400",
    border: "border-purple-500/30",
  },
  orange: {
    bg: "bg-orange-500/20",
    text: "text-orange-400",
    border: "border-orange-500/30",
  },
  yellow: {
    bg: "bg-yellow-500/20",
    text: "text-yellow-400",
    border: "border-yellow-500/30",
  },
  red: {
    bg: "bg-red-500/20",
    text: "text-red-400",
    border: "border-red-500/30",
  },
  zinc: {
    bg: "bg-zinc-500/20",
    text: "text-zinc-400",
    border: "border-zinc-500/30",
  },
};

// =============================================================================
// Learning Confidence Configuration
// =============================================================================

/**
 * Learning confidence labels.
 */
export const CONFIDENCE_LABELS: Record<string, string> = {
  alta: "Alta confiança",
  media: "Média confiança",
  baixa: "Baixa confiança",
};

/**
 * Learning confidence colors.
 */
export const CONFIDENCE_COLORS: Record<string, string> = {
  alta: "text-green-400",
  media: "text-yellow-400",
  baixa: "text-orange-400",
};

// =============================================================================
// Workflow Step Icons
// =============================================================================

/**
 * Common workflow step icons.
 */
export const WORKFLOW_STEP_ICONS: Record<string, string> = {
  received: "FileText",
  analyzing: "Search",
  validated: "CheckCircle",
  importing: "Upload",
  completed: "Package",
  error: "AlertCircle",
  waiting: "Clock",
};

// =============================================================================
// Mock Data (for development)
// =============================================================================

/**
 * Sample live messages for development/demo.
 */
export const MOCK_LIVE_MESSAGES = [
  {
    id: "msg-1",
    timestamp: new Date().toISOString(),
    agentName: "NEXO",
    message: "Estou analisando o arquivo que você enviou...",
    type: "info" as const,
  },
  {
    id: "msg-2",
    timestamp: new Date(Date.now() - 30000).toISOString(),
    agentName: "Leitor de Notas",
    message: "Encontrei 47 itens na nota fiscal. Tudo parece correto!",
    type: "success" as const,
  },
  {
    id: "msg-3",
    timestamp: new Date(Date.now() - 60000).toISOString(),
    agentName: "Validador",
    message: "Alguns itens não têm código de projeto. Pode me ajudar?",
    type: "warning" as const,
  },
  {
    id: "msg-4",
    timestamp: new Date(Date.now() - 120000).toISOString(),
    agentName: "Importador",
    message: "Importação concluída! 47 itens adicionados ao estoque.",
    type: "success" as const,
  },
];

/**
 * Sample learning stories for development/demo.
 */
export const MOCK_LEARNING_STORIES = [
  {
    id: "learn-1",
    learnedAt: new Date(Date.now() - 86400000).toISOString(),
    agentName: "Memória",
    story: "Aprendi que suas planilhas geralmente têm o código na coluna B",
    confidence: "alta" as const,
  },
  {
    id: "learn-2",
    learnedAt: new Date(Date.now() - 172800000).toISOString(),
    agentName: "Leitor de Notas",
    story: "Reconheço o formato dos seus arquivos SAP automaticamente",
    confidence: "alta" as const,
  },
  {
    id: "learn-3",
    learnedAt: new Date(Date.now() - 259200000).toISOString(),
    agentName: "Importador",
    story: "Sei que 'SN' significa 'Serial Number' nos seus documentos",
    confidence: "media" as const,
  },
];

/**
 * Sample pending decisions for development/demo.
 */
export const MOCK_PENDING_DECISIONS = [
  {
    id: "dec-1",
    question: "Encontrei um item novo. Posso criar o cadastro?",
    options: [
      { label: "Sim, criar", action: "approve" },
      { label: "Revisar primeiro", action: "review" },
    ],
    priority: "normal" as const,
    createdAt: new Date(Date.now() - 300000).toISOString(),
    agentName: "Importador",
  },
  {
    id: "dec-2",
    question: "Este código não existe ainda. O que devo fazer?",
    options: [
      { label: "Criar novo", action: "create" },
      { label: "Ignorar", action: "skip" },
    ],
    priority: "alta" as const,
    createdAt: new Date(Date.now() - 600000).toISOString(),
    agentName: "Validador",
  },
];

/**
 * Sample active workflow for development/demo.
 */
export const MOCK_ACTIVE_WORKFLOW = {
  id: "wf-1",
  name: "Importação de NF",
  description: "Processando nota fiscal #12345",
  steps: [
    { id: "step-1", label: "Recebido", status: "concluido" as const, icon: "FileText" },
    { id: "step-2", label: "Analisando", status: "atual" as const, icon: "Search" },
    { id: "step-3", label: "Validado", status: "pendente" as const, icon: "CheckCircle" },
    { id: "step-4", label: "Concluído", status: "pendente" as const, icon: "Package" },
  ],
  startedAt: new Date(Date.now() - 180000).toISOString(),
  currentAgent: "Leitor de Notas",
};
