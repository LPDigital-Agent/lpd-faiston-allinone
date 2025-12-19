/**
 * Mock Data for Faiston One Dashboard
 *
 * Realistic mock data for demonstration purposes.
 * This will be replaced with real API calls in future phases.
 */

// Calendar Events
export const calendarEvents = [
  {
    id: "evt-001",
    title: "Daily Standup",
    start: "2025-12-19T09:00:00-03:00",
    end: "2025-12-19T09:30:00-03:00",
    type: "meeting",
    attendees: ["Maria Silva", "João Costa"],
    location: "Teams",
    isAllDay: false,
  },
  {
    id: "evt-002",
    title: "1:1 com Gestor",
    start: "2025-12-19T14:00:00-03:00",
    end: "2025-12-19T14:30:00-03:00",
    type: "meeting",
    attendees: ["Carlos Mendes"],
    location: "Sala 302",
    isAllDay: false,
  },
  {
    id: "evt-003",
    title: "Review Sprint 23",
    start: "2025-12-19T15:00:00-03:00",
    end: "2025-12-19T16:00:00-03:00",
    type: "meeting",
    attendees: ["Equipe Dev"],
    location: "Teams",
    isAllDay: false,
  },
  {
    id: "evt-004",
    title: "Planning Sprint 24",
    start: "2025-12-20T10:00:00-03:00",
    end: "2025-12-20T12:00:00-03:00",
    type: "meeting",
    attendees: ["Equipe Dev", "Product"],
    location: "Sala 401",
    isAllDay: false,
  },
];

// News Articles
export const newsArticles = [
  {
    id: "news-001",
    title: "AWS re:Invent 2025: Novidades em GenAI e Bedrock",
    source: "AWS News Blog",
    sourceIcon: "aws",
    category: "cloud-aws",
    summary:
      "Amazon anuncia novas funcionalidades do Bedrock AgentCore para construção de agentes de IA empresariais.",
    url: "https://aws.amazon.com/blogs/aws/",
    publishedAt: "2025-12-18T10:00:00Z",
    readTime: 5,
    relevanceScore: 95,
  },
  {
    id: "news-002",
    title: "Google ADK v1.0: Agent Development Kit Oficial",
    source: "Google Cloud Blog",
    sourceIcon: "google",
    category: "ai",
    summary:
      "O novo Agent Development Kit da Google facilita a criação de agentes de IA com protocolo A2A.",
    url: "https://cloud.google.com/blog/",
    publishedAt: "2025-12-17T14:30:00Z",
    readTime: 8,
    relevanceScore: 92,
  },
  {
    id: "news-003",
    title: "Microsoft Azure: Atualizações do Copilot Studio",
    source: "Microsoft Azure Blog",
    sourceIcon: "azure",
    category: "cloud-azure",
    summary:
      "Novas capacidades para criar copilots customizados para empresas.",
    url: "https://azure.microsoft.com/blog/",
    publishedAt: "2025-12-17T09:00:00Z",
    readTime: 6,
    relevanceScore: 88,
  },
  {
    id: "news-004",
    title: "OpenAI Apresenta GPT-5 Turbo",
    source: "TechCrunch",
    sourceIcon: "techcrunch",
    category: "ai",
    summary:
      "Nova versão do modelo apresenta melhorias significativas em raciocínio e velocidade.",
    url: "https://techcrunch.com/",
    publishedAt: "2025-12-16T18:00:00Z",
    readTime: 4,
    relevanceScore: 90,
  },
];

// Teams Messages
export const teamsMessages = [
  {
    id: "msg-001",
    sender: {
      id: "user-002",
      name: "Maria Silva",
      avatar: null,
      status: "online",
    },
    preview:
      "Oi! Você viu o documento que enviei ontem? Precisamos revisar antes da reunião de amanhã.",
    timestamp: "2025-12-19T08:45:00-03:00",
    unread: true,
    channel: "direct",
  },
  {
    id: "msg-002",
    sender: {
      id: "user-003",
      name: "João Costa",
      avatar: null,
      status: "away",
    },
    preview: "Documento revisado e aprovado. Pode prosseguir com o deploy.",
    timestamp: "2025-12-19T08:30:00-03:00",
    unread: true,
    channel: "direct",
  },
  {
    id: "msg-003",
    sender: {
      id: "user-004",
      name: "Ana Oliveira",
      avatar: null,
      status: "online",
    },
    preview: "Time, lembrete: reunião de alinhamento às 14h hoje!",
    timestamp: "2025-12-19T08:15:00-03:00",
    unread: false,
    channel: "Equipe-Dev",
  },
  {
    id: "msg-004",
    sender: {
      id: "user-005",
      name: "Carlos Mendes",
      avatar: null,
      status: "busy",
    },
    preview: "Excelente trabalho no último sprint! Vamos discutir na 1:1.",
    timestamp: "2025-12-18T17:30:00-03:00",
    unread: false,
    channel: "direct",
  },
];

// Announcements
export const announcements = [
  {
    id: "ann-001",
    title: "Nova Política de Férias 2026",
    content:
      "Consulte o novo calendário de férias e as regras atualizadas para o próximo ano.",
    type: "policy",
    priority: "high",
    publishedAt: "2025-12-18T10:00:00-03:00",
    author: "RH",
  },
  {
    id: "ann-002",
    title: "Resultados Q4 2025",
    content:
      "Confira os resultados do último trimestre. Crescimento de 15% em relação ao período anterior.",
    type: "business",
    priority: "medium",
    publishedAt: "2025-12-17T14:00:00-03:00",
    author: "Diretoria",
  },
  {
    id: "ann-003",
    title: "Manutenção Sistemas - Domingo",
    content:
      "Os sistemas estarão indisponíveis das 02h às 06h para manutenção programada.",
    type: "it",
    priority: "medium",
    publishedAt: "2025-12-16T09:00:00-03:00",
    author: "TI",
  },
];

// NEXO Conversation (static example)
export const nexoConversation = {
  messages: [
    {
      id: "nexo-001",
      role: "assistant" as const,
      content: "Bom dia, Fábio! 👋",
      timestamp: "2025-12-19T08:00:00-03:00",
    },
    {
      id: "nexo-002",
      role: "assistant" as const,
      content:
        "Aqui está seu resumo do dia:\n\n• 3 reuniões agendadas (próxima: Daily em 15min)\n• 5 mensagens não lidas no Teams\n• 2 notícias importantes sobre AWS e Google AI",
      timestamp: "2025-12-19T08:00:05-03:00",
      metadata: {
        type: "summary",
        data: {
          meetings: 3,
          unreadMessages: 5,
          newsCount: 2,
        },
      },
    },
  ],
  suggestions: ["Ver calendário", "Abrir Teams", "Ver notícias", "Agendar reunião"],
};

// User profile
export const currentUser = {
  id: "user-001",
  name: "Fábio Santos",
  email: "fabio@faiston.com",
  role: "Desenvolvedor",
  department: "Tecnologia",
  avatar: null,
};

// Quick actions
export const quickActions = [
  {
    id: "qa-001",
    label: "Agendar",
    icon: "calendar",
    action: "schedule-meeting",
  },
  {
    id: "qa-002",
    label: "Mensagem",
    icon: "message",
    action: "send-message",
  },
  {
    id: "qa-003",
    label: "Relatórios",
    icon: "chart",
    action: "view-reports",
  },
  {
    id: "qa-004",
    label: "Buscar",
    icon: "search",
    action: "search",
  },
];
