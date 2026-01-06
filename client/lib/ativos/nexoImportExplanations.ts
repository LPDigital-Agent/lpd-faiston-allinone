/**
 * NEXO Import Explanations - Contextual help content for Smart Import
 *
 * Each section has:
 * - summary: Always visible (1-2 sentences)
 * - details: Expandable explanation (optional)
 * - action: Recommended next step (optional)
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
  details?: string;
  action?: string;
}

// =============================================================================
// Reasoning Trace (ReAct Pattern)
// =============================================================================

export const REASONING_TRACE_EXPLANATION: NexoExplanation = {
  summary: "Aqui você vê como o NEXO está pensando. Cada etapa mostra raciocínio, ações e observações.",
  details: `O NEXO usa o padrão ReAct (Reason + Act):

• Pensamento (roxo): NEXO reflete sobre o que viu
• Ação (ciano): NEXO executa uma ferramenta ou análise
• Observação (verde): NEXO registra o que encontrou

Este padrão garante transparência total - você entende cada decisão tomada.`,
  action: "Acompanhe o progresso em tempo real.",
};

// =============================================================================
// Sheet Analysis
// =============================================================================

export const SHEET_ANALYSIS_EXPLANATION: DynamicExplanation = {
  getSummary: (params) => {
    const count = params.sheetCount ?? 0;
    if (count === 0) return "Nenhuma aba identificada no arquivo.";
    if (count === 1) return "O NEXO identificou 1 aba e classificou pelo tipo de conteúdo.";
    return `O NEXO identificou ${count} abas e classificou cada uma pelo tipo de conteúdo.`;
  },
  details: `Cada aba é classificada por propósito:

• Itens: Materiais/produtos a importar (mais importante!)
• Seriais: Números de série para cada item
• Metadados: Informações do fornecedor/projeto
• Resumo: Totais e estatísticas (geralmente ignoramos)

O percentual indica quão certo o NEXO está. Abaixo de 70% pode precisar confirmação.`,
  action: "Verifique se a aba principal está correta.",
};

// =============================================================================
// Column Mappings (PRIORITY - Most confusing to users)
// =============================================================================

export const COLUMN_MAPPINGS_EXPLANATION: DynamicExplanation = {
  getSummary: (params) => {
    const total = params.total ?? 0;
    const high = params.high ?? 0;
    const medium = params.medium ?? 0;
    const low = params.low ?? 0;

    if (total === 0) return "Nenhuma coluna mapeada ainda.";

    return `O NEXO mapeou ${total} colunas: ${high} alta, ${medium} média, ${low} baixa confiança.`;
  },
  details: `Níveis de confiança explicados:

• Alta (verde, 80%+): Mapeamento praticamente certo
• Média (amarelo, 50-79%): Provável correto, mas vale verificar
• Baixa (vermelho, <50%): Incerto, você deve confirmar

Mapeamentos errados causam dados no campo errado! Exemplo: se "EQUIPAMENTO" mapear para "quantity" em vez de "part_number", os itens não serão identificados corretamente.`,
  action: "Revise os mapeamentos de baixa confiança nas perguntas abaixo.",
};

// =============================================================================
// Questions Panel (PRIORITY - Requires user action)
// =============================================================================

export const QUESTIONS_CRITICAL_EXPLANATION: NexoExplanation = {
  summary: "Perguntas essenciais - o NEXO não conseguiu inferir com certeza suficiente.",
  details: `Tipos de perguntas:

• Obrigatórias (vermelho): Sem resposta, importação pode falhar
• Importantes (laranja): Afetam qualidade, mas temos padrão
• Opcionais (cinza): Refinamentos que podem ser pulados

Se você selecionar "Outros", pode digitar um valor personalizado.`,
  action: "Responda pelo menos as obrigatórias.",
};

export const QUESTIONS_OPTIONAL_EXPLANATION: NexoExplanation = {
  summary: "Respostas opcionais refinam a importação. Se pular, usaremos valores padrão.",
  details: `Estas perguntas são baseadas em:

• Padrões históricos de importações similares
• Campos detectados no arquivo atual
• Regras de negócio do SGA

Respondê-las melhora a precisão e reduz correções manuais depois.`,
  action: "Preencha se tiver tempo - não são obrigatórias.",
};

// =============================================================================
// Prior Knowledge (Learning Memory)
// =============================================================================

export const PRIOR_KNOWLEDGE_WITH_HISTORY: DynamicExplanation = {
  getSummary: (params) => {
    const count = params.episodeCount ?? 0;
    return `O NEXO encontrou ${count} importaç${count === 1 ? 'ão anterior similar' : 'ões anteriores similares'}.`;
  },
  details: `Cada importação ensina o NEXO:

• Quais colunas contêm Part Number, Quantidade, etc.
• Qual projeto associado a qual tipo de arquivo
• Quais mapeamentos você corrige frequentemente

Importações bem-sucedidas aumentam a confiança do NEXO em decisões futuras.`,
  action: "Quanto mais você usar, mais inteligente ele fica!",
};

export const PRIOR_KNOWLEDGE_FIRST_TIME: NexoExplanation = {
  summary: "Primeira vez com este tipo de arquivo. Suas respostas ajudarão importações futuras.",
  details: `O NEXO está aprendendo com você:

• Esta importação será memorizada
• Próximas importações similares serão mais rápidas
• Seus ajustes refinam o conhecimento do sistema

É normal ter mais perguntas na primeira vez.`,
  action: "Responda com atenção - você está treinando o NEXO!",
};

// =============================================================================
// File Info
// =============================================================================

export const FILE_INFO_EXPLANATION: DynamicExplanation = {
  getSummary: (params) => {
    const strategy = params.strategy ?? "unknown";
    const strategyNames: Record<string, string> = {
      direct_parse: "análise direta",
      vision_ocr: "IA visual (OCR)",
      multi_sheet: "múltiplas abas",
      ai_extraction: "IA generativa",
    };
    const name = strategyNames[strategy as string] ?? strategy;
    return `O NEXO detectou o tipo do arquivo e selecionou a estratégia: ${name}.`;
  },
  details: `Estratégias de processamento:

• direct_parse: Arquivos estruturados (XML, CSV) - mais rápido
• vision_ocr: Imagens e PDFs escaneados - usa IA visual
• multi_sheet: Excel com várias abas - analisa estrutura
• ai_extraction: Texto livre - usa IA generativa para extrair

A estratégia correta garante máxima precisão na extração.`,
};

// =============================================================================
// Loading States
// =============================================================================

export const LOADING_EXPLANATIONS: Record<string, NexoExplanation> = {
  uploading: {
    summary: "Enviando arquivo para processamento seguro...",
    details: "O arquivo é armazenado de forma segura no S3 com URLs assinadas temporárias.",
  },
  recalling: {
    summary: "Consultando memória para encontrar importações similares...",
    details: "O NEXO está buscando episódios passados que possam ajudar nesta importação.",
  },
  analyzing: {
    summary: "Analisando estrutura e detectando padrões...",
    details: "Identificando abas, colunas e tipos de dados automaticamente.",
  },
  mapping: {
    summary: "Mapeando colunas para campos do sistema...",
    details: "Comparando nomes de colunas com campos conhecidos do SGA.",
  },
  generating: {
    summary: "Gerando perguntas inteligentes...",
    details: "Criando perguntas baseadas em ambiguidades detectadas e histórico.",
  },
};

// =============================================================================
// Error State
// =============================================================================

export const ERROR_EXPLANATION: NexoExplanation = {
  summary: "Algo deu errado. Veja abaixo o que pode ter causado.",
  details: `Soluções comuns:

1. Arquivo muito grande: Máximo 50MB
2. Formato não suportado: Use XML, PDF, CSV, XLSX, JPG, PNG, TXT
3. Arquivo corrompido: Reexporte do sistema de origem
4. Timeout: Arquivo muito complexo - simplifique ou divida
5. Erro de rede: Verifique sua conexão e tente novamente`,
  action: "Corrija o problema e tente novamente.",
};

// =============================================================================
// Success State
// =============================================================================

export const SUCCESS_EXPLANATION: NexoExplanation = {
  summary: "Análise completa! Revise os dados e confirme a importação.",
  details: `O NEXO analisou com sucesso:

• Estrutura do arquivo detectada
• Colunas mapeadas para campos do sistema
• Perguntas geradas para ambiguidades

Agora é sua vez de revisar e ajustar se necessário.`,
  action: "Revise e clique em 'Confirmar Importação'.",
};

// =============================================================================
// Confidence Badges Tooltip
// =============================================================================

export const CONFIDENCE_BADGE_EXPLANATIONS: Record<string, string> = {
  high: "Confiança alta (80%+): Mapeamento muito provável correto. NEXO está seguro.",
  medium: "Confiança média (50-79%): Provável correto, mas vale verificar.",
  low: "Confiança baixa (<50%): Incerto. Por favor, confirme manualmente.",
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get explanation based on confidence level counts
 */
export function getColumnMappingsExplanation(high: number, medium: number, low: number): NexoExplanation {
  const total = high + medium + low;
  return {
    summary: COLUMN_MAPPINGS_EXPLANATION.getSummary({ total, high, medium, low }),
    details: COLUMN_MAPPINGS_EXPLANATION.details,
    action: COLUMN_MAPPINGS_EXPLANATION.action,
  };
}

/**
 * Get explanation for sheet analysis
 */
export function getSheetAnalysisExplanation(sheetCount: number): NexoExplanation {
  return {
    summary: SHEET_ANALYSIS_EXPLANATION.getSummary({ sheetCount }),
    details: SHEET_ANALYSIS_EXPLANATION.details,
    action: SHEET_ANALYSIS_EXPLANATION.action,
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
    details: PRIOR_KNOWLEDGE_WITH_HISTORY.details,
    action: PRIOR_KNOWLEDGE_WITH_HISTORY.action,
  };
}

/**
 * Get explanation for file strategy
 */
export function getFileInfoExplanation(strategy: string): NexoExplanation {
  return {
    summary: FILE_INFO_EXPLANATION.getSummary({ strategy }),
    details: FILE_INFO_EXPLANATION.details,
  };
}
