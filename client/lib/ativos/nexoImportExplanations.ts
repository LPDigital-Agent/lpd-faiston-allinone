/**
 * NEXO Import Explanations - Contextual help content for Smart Import
 *
 * PHILOSOPHY: Explanations must be ACTIONABLE, not just stating facts!
 * - DON'T: "Identifiquei 9 abas" (user already sees this)
 * - DO: "A aba principal é X, as outras são secundárias. Verifique se está certo!"
 *
 * VOICE: First person (NEXO speaks directly to user)
 * - "Eu encontrei..." not "O NEXO encontrou..."
 *
 * Each section has:
 * - summary: Always visible - MUST be ACTIONABLE guidance
 * - details: Expandable - explains WHAT things mean
 * - action: What user should DO next
 *
 * Language: Brazilian Portuguese (pt-BR)
 * Following NEXO AI-First philosophy: Observant, Thoughtful, Collaborative
 */

// =============================================================================
// Type Definitions
// =============================================================================

export interface NexoExplanation {
  summary: string;
  details?: string;
  action?: string;
}

export interface DynamicExplanation {
  getSummary: (params: Record<string, unknown>) => string;
  getDetails?: (params: Record<string, unknown>) => string;
  getAction?: (params: Record<string, unknown>) => string;
}

// =============================================================================
// Reasoning Trace (ReAct Pattern)
// =============================================================================

export const REASONING_TRACE_EXPLANATION: NexoExplanation = {
  summary: "Aqui mostro meu raciocínio passo a passo. Se algo parecer errado, me corrija nas perguntas abaixo!",
  details: `Uso o padrão ReAct para ser transparente com você:

• Pensamento (roxo): O que estou analisando
• Ação (ciano): Ferramenta que estou usando
• Observação (verde): O que encontrei

Se meu raciocínio parece errado em algum ponto, use as perguntas abaixo para me corrigir.`,
  action: "Acompanhe meu raciocínio - me corrija se necessário!",
};

// =============================================================================
// Sheet Analysis - MUST explain PURPOSE of each type
// =============================================================================

export const SHEET_ANALYSIS_EXPLANATION: DynamicExplanation = {
  getSummary: (params) => {
    const count = params.sheetCount ?? 0;
    if (count === 0) return "Não encontrei abas válidas. Verifique se o arquivo está correto.";
    if (count === 1) return "Arquivo simples! Vou processar todos os dados desta única aba.";

    // Multiple sheets - guide user
    return `Encontrei ${count} abas. Verifique se identifiquei corretamente qual contém os itens a importar!`;
  },
  getDetails: () => `O que cada tipo de aba significa:

• Itens (ciano): Contém os materiais/produtos → É A MAIS IMPORTANTE!
• Seriais (roxo): Números de série de cada item
• Metadados (amarelo): Dados do fornecedor/projeto
• Resumo (verde): Totais e estatísticas (geralmente ignoro)

⚠️ Se eu errar a aba principal, vou processar os dados errados!`,
  getAction: (params) => {
    const count = params.sheetCount ?? 0;
    if (count > 1) {
      return "Confira se a aba marcada como 'Itens' é realmente a principal!";
    }
    return undefined;
  },
};

// =============================================================================
// Column Mappings - MUST explain WHAT TO DO with low confidence
// =============================================================================

export const COLUMN_MAPPINGS_EXPLANATION: DynamicExplanation = {
  getSummary: (params) => {
    const total = params.total ?? 0;
    const high = params.high ?? 0;
    const low = params.low ?? 0;

    if (total === 0) return "Ainda analisando as colunas...";

    // Focus on what needs attention
    if (low > 0) {
      return `⚠️ ${low} colunas com baixa confiança precisam da sua atenção! Responda as perguntas abaixo.`;
    }
    if (high === total) {
      return `✅ Tenho alta confiança em todos os ${total} mapeamentos. Pode prosseguir!`;
    }
    return `A maioria está ok, mas verifique os ${params.medium ?? 0} mapeamentos de média confiança.`;
  },
  getDetails: () => `O que os níveis de confiança significam:

🟢 Alta (80%+): Tenho quase certeza - não precisa verificar
🟡 Média (50-79%): Provavelmente correto - vale uma olhada
🔴 Baixa (<50%): Não tenho certeza - VOCÊ precisa confirmar!

⚠️ IMPORTANTE: Se eu mapear errado, os dados vão para o campo errado no sistema!
Exemplo: Se "EQUIPAMENTO" virar "quantidade" em vez de "part_number", você não vai encontrar os itens depois.`,
  getAction: (params) => {
    const low = params.low ?? 0;
    if (low > 0) {
      return `Responda as ${low} perguntas abaixo para corrigir meus mapeamentos!`;
    }
    return "Tudo certo! Pode confirmar a importação.";
  },
};

// =============================================================================
// Questions Panel - MUST explain WHY user needs to answer
// =============================================================================

export const QUESTIONS_CRITICAL_EXPLANATION: NexoExplanation = {
  summary: "🚨 Preciso da sua ajuda aqui! Não consegui descobrir essas informações sozinho.",
  details: `Por que estou perguntando:

• Sem sua resposta, a importação pode FALHAR ou criar dados incorretos
• Cada pergunta tem opções baseadas no que encontrei no arquivo
• Se nenhuma opção servir, use "Outros" para digitar manualmente

Estas perguntas são OBRIGATÓRIAS - não consigo continuar sem elas.`,
  action: "Responda todas para eu poder finalizar a importação!",
};

export const QUESTIONS_OPTIONAL_EXPLANATION: NexoExplanation = {
  summary: "Estas perguntas refinam a importação. Se pular, uso valores padrão que funcionam na maioria dos casos.",
  details: `Quando você deve responder:

• Se quiser mais precisão nos dados importados
• Se conhece detalhes específicos deste arquivo
• Se já teve problemas com valores padrão antes

Quando pode pular:
• Se for importação padrão/rotineira
• Se não tiver certeza da resposta`,
  action: "Opcional: responda se quiser mais precisão.",
};

// =============================================================================
// Prior Knowledge - MUST explain HOW it helps
// =============================================================================

export const PRIOR_KNOWLEDGE_WITH_HISTORY: DynamicExplanation = {
  getSummary: (params) => {
    const count = params.episodeCount ?? 0;
    if (count === 1) {
      return "🧠 Encontrei 1 importação similar! Estou usando esse conhecimento para preencher automaticamente.";
    }
    return `🧠 Encontrei ${count} importações similares! Quanto mais você me usa, mais inteligente eu fico.`;
  },
  getDetails: () => `O que aprendi com importações anteriores:

• Quais colunas do SEU arquivo correspondem a quais campos
• Qual projeto geralmente está associado a este tipo de arquivo
• Quais mapeamentos você costuma corrigir

Isso significa que faço menos perguntas e acerto mais!`,
  getAction: () => "Se minhas sugestões estiverem boas, você pode confiar nelas!",
};

export const PRIOR_KNOWLEDGE_FIRST_TIME: NexoExplanation = {
  summary: "📝 Primeira vez com este tipo de arquivo! Suas respostas vão me ensinar para as próximas.",
  details: `O que acontece agora:

• Vou fazer mais perguntas que o normal
• Suas respostas vão direto para minha memória
• Nas próximas importações similares, serei mais rápido e assertivo

É normal eu pedir mais confirmações na primeira vez!`,
  action: "Responda com atenção - você está me treinando!",
};

// =============================================================================
// File Info - MUST explain processing strategy
// =============================================================================

export const FILE_INFO_EXPLANATION: DynamicExplanation = {
  getSummary: (params) => {
    const strategy = params.strategy ?? "unknown";
    const strategyMessages: Record<string, string> = {
      direct_parse: "Arquivo estruturado! Vou processar diretamente - rápido e preciso.",
      vision_ocr: "📸 Usando IA visual para ler este arquivo. Pode demorar um pouco mais.",
      multi_sheet: "Excel com várias abas! Verifique se identifiquei a aba correta.",
      ai_extraction: "Texto não estruturado - usando IA generativa para extrair os dados.",
    };
    return strategyMessages[strategy as string] ?? "Analisando formato do arquivo...";
  },
  getDetails: () => `Estratégias de processamento:

• direct_parse: Para XML, CSV bem formatados - mais rápido
• vision_ocr: Para PDFs escaneados, imagens - usa Gemini Vision
• multi_sheet: Para Excel com várias abas - analiso cada uma
• ai_extraction: Para texto livre - usa IA generativa

Cada estratégia é otimizada para o tipo de arquivo.`,
};

// =============================================================================
// Loading States - MUST inform WHAT is happening
// =============================================================================

export const LOADING_EXPLANATIONS: Record<string, NexoExplanation> = {
  uploading: {
    summary: "📤 Enviando seu arquivo para processamento seguro...",
    details: "Usando URL assinada temporária para garantir segurança.",
  },
  recalling: {
    summary: "🧠 Consultando minha memória por importações similares...",
    details: "Buscando arquivos parecidos que você já importou antes.",
  },
  analyzing: {
    summary: "🔍 Analisando estrutura do arquivo...",
    details: "Identificando abas, colunas e tipos de dados automaticamente.",
  },
  mapping: {
    summary: "🗺️ Mapeando colunas para campos do sistema...",
    details: "Comparando nomes de colunas com campos conhecidos do SGA.",
  },
  generating: {
    summary: "❓ Gerando perguntas para esclarecer dúvidas...",
    details: "Criando perguntas baseadas em ambiguidades que encontrei.",
  },
};

// =============================================================================
// Error State - MUST give ACTIONABLE solutions
// =============================================================================

export const ERROR_EXPLANATION: NexoExplanation = {
  summary: "❌ Ops! Encontrei um problema. Veja abaixo como resolver.",
  details: `Soluções mais comuns:

1. Arquivo muito grande → Máximo 50MB
2. Formato não suportado → Use XML, PDF, CSV, XLSX, JPG, PNG ou TXT
3. Arquivo corrompido → Reexporte do sistema de origem
4. Timeout → Arquivo muito complexo - tente dividir em partes menores
5. Erro de rede → Verifique sua conexão e tente novamente`,
  action: "Corrija o problema e clique em 'Tentar novamente'!",
};

// =============================================================================
// Success State
// =============================================================================

export const SUCCESS_EXPLANATION: NexoExplanation = {
  summary: "✅ Análise completa! Revise os dados e confirme se está tudo certo.",
  details: `O que foi feito:

• Estrutura do arquivo detectada
• Colunas mapeadas para campos do sistema
• Perguntas geradas para esclarecer dúvidas

Agora é sua vez de revisar e aprovar!`,
  action: "Revise os dados e clique em 'Confirmar Importação'.",
};

// =============================================================================
// Confidence Badges Tooltip - Explains inline
// =============================================================================

export const CONFIDENCE_BADGE_EXPLANATIONS: Record<string, string> = {
  high: "✅ Tenho quase certeza - não precisa verificar.",
  medium: "⚠️ Provavelmente correto - vale uma olhada.",
  low: "🚨 Não tenho certeza - confirme manualmente!",
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get explanation based on confidence level counts
 */
export function getColumnMappingsExplanation(high: number, medium: number, low: number): NexoExplanation {
  const total = high + medium + low;
  const params = { total, high, medium, low };
  return {
    summary: COLUMN_MAPPINGS_EXPLANATION.getSummary(params),
    details: COLUMN_MAPPINGS_EXPLANATION.getDetails?.(params) ?? COLUMN_MAPPINGS_EXPLANATION.getDetails?.({}) ?? "",
    action: COLUMN_MAPPINGS_EXPLANATION.getAction?.(params),
  };
}

/**
 * Get explanation for sheet analysis
 */
export function getSheetAnalysisExplanation(sheetCount: number): NexoExplanation {
  const params = { sheetCount };
  return {
    summary: SHEET_ANALYSIS_EXPLANATION.getSummary(params),
    details: SHEET_ANALYSIS_EXPLANATION.getDetails?.(params) ?? "",
    action: SHEET_ANALYSIS_EXPLANATION.getAction?.(params),
  };
}

/**
 * Get explanation for prior knowledge
 */
export function getPriorKnowledgeExplanation(episodeCount: number): NexoExplanation {
  if (episodeCount === 0) {
    return PRIOR_KNOWLEDGE_FIRST_TIME;
  }
  return {
    summary: PRIOR_KNOWLEDGE_WITH_HISTORY.getSummary({ episodeCount }),
    details: PRIOR_KNOWLEDGE_WITH_HISTORY.getDetails?.({ episodeCount }) ?? "",
    action: PRIOR_KNOWLEDGE_WITH_HISTORY.getAction?.({ episodeCount }),
  };
}

/**
 * Get explanation for file strategy
 */
export function getFileInfoExplanation(strategy: string): NexoExplanation {
  return {
    summary: FILE_INFO_EXPLANATION.getSummary({ strategy }),
    details: FILE_INFO_EXPLANATION.getDetails?.({ strategy }) ?? "",
  };
}
