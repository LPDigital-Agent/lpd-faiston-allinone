/**
 * NEXO Import Explanations - Contextual help content for Smart Import
 *
 * IMPORTANT: All text must be in FIRST PERSON voice.
 * NEXO speaks directly to the user ("Eu encontrei..." not "O NEXO encontrou...")
 *
 * Each section has:
 * - summary: Always visible (1-2 sentences) - FIRST PERSON
 * - details: Expandable explanation (optional) - FIRST PERSON
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
  summary: "Aqui você vê como estou pensando. Cada etapa mostra meu raciocínio, ações e observações.",
  details: `Uso o padrão ReAct (Reason + Act) para ser transparente:

• Pensamento (roxo): Reflito sobre o que vi
• Ação (ciano): Executo uma ferramenta ou análise
• Observação (verde): Registro o que encontrei

Assim você entende cada decisão que tomo.`,
  action: "Acompanhe meu progresso em tempo real.",
};

// =============================================================================
// Sheet Analysis
// =============================================================================

export const SHEET_ANALYSIS_EXPLANATION: DynamicExplanation = {
  getSummary: (params) => {
    const count = params.sheetCount ?? 0;
    if (count === 0) return "Não identifiquei nenhuma aba no arquivo.";
    if (count === 1) return "Identifiquei 1 aba e classifiquei pelo tipo de conteúdo.";
    return `Identifiquei ${count} abas e classifiquei cada uma pelo tipo de conteúdo.`;
  },
  details: `Classifico cada aba por propósito:

• Itens: Materiais/produtos a importar (mais importante!)
• Seriais: Números de série para cada item
• Metadados: Informações do fornecedor/projeto
• Resumo: Totais e estatísticas (geralmente ignoro)

O percentual indica minha certeza. Abaixo de 70% pode precisar sua confirmação.`,
  action: "Verifique se identifiquei a aba principal corretamente.",
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

    if (total === 0) return "Ainda não mapeei nenhuma coluna.";

    return `Mapeei ${total} colunas: ${high} com alta, ${medium} com média, ${low} com baixa confiança.`;
  },
  details: `Meus níveis de confiança significam:

• Alta (verde, 80%+): Tenho quase certeza do mapeamento
• Média (amarelo, 50-79%): Provavelmente correto, mas vale você verificar
• Baixa (vermelho, <50%): Estou incerto, preciso da sua confirmação

Se eu errar um mapeamento, os dados vão para o campo errado! Ex: "EQUIPAMENTO" mapeado para "quantity" em vez de "part_number" impede a identificação dos itens.`,
  action: "Revise os mapeamentos de baixa confiança nas perguntas abaixo.",
};

// =============================================================================
// Questions Panel (PRIORITY - Requires user action)
// =============================================================================

export const QUESTIONS_CRITICAL_EXPLANATION: NexoExplanation = {
  summary: "Preciso da sua ajuda nestas perguntas - não consegui inferir com certeza suficiente.",
  details: `Tipos de perguntas que faço:

• Obrigatórias (vermelho): Sem sua resposta, a importação pode falhar
• Importantes (laranja): Afetam a qualidade, mas tenho um padrão
• Opcionais (cinza): Refinamentos que você pode pular

Se selecionar "Outros", você pode digitar um valor personalizado.`,
  action: "Responda pelo menos as obrigatórias para eu continuar.",
};

export const QUESTIONS_OPTIONAL_EXPLANATION: NexoExplanation = {
  summary: "Estas respostas refinam a importação. Se pular, usarei valores padrão.",
  details: `Baseei estas perguntas em:

• Padrões que aprendi em importações similares
• Campos que detectei no arquivo atual
• Regras de negócio do SGA

Respondê-las me ajuda a ser mais preciso e reduz correções manuais depois.`,
  action: "Preencha se tiver tempo - não são obrigatórias.",
};

// =============================================================================
// Prior Knowledge (Learning Memory)
// =============================================================================

export const PRIOR_KNOWLEDGE_WITH_HISTORY: DynamicExplanation = {
  getSummary: (params) => {
    const count = params.episodeCount ?? 0;
    return `Encontrei ${count} importaç${count === 1 ? 'ão anterior similar' : 'ões anteriores similares'} na minha memória!`;
  },
  details: `Aprendo com cada importação:

• Quais colunas contêm Part Number, Quantidade, etc.
• Qual projeto está associado a cada tipo de arquivo
• Quais mapeamentos você costuma corrigir

Importações bem-sucedidas aumentam minha confiança em decisões futuras.`,
  action: "Quanto mais você me usar, mais inteligente eu fico!",
};

export const PRIOR_KNOWLEDGE_FIRST_TIME: NexoExplanation = {
  summary: "É minha primeira vez com este tipo de arquivo. Suas respostas vão me ajudar no futuro!",
  details: `Estou aprendendo com você:

• Vou memorizar esta importação
• Próximas importações similares serão mais rápidas
• Seus ajustes refinam meu conhecimento

É normal eu fazer mais perguntas na primeira vez.`,
  action: "Responda com atenção - você está me treinando!",
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
    return `Detectei o tipo do arquivo e escolhi a melhor estratégia: ${name}.`;
  },
  details: `Minhas estratégias de processamento:

• direct_parse: Para arquivos estruturados (XML, CSV) - mais rápido
• vision_ocr: Para imagens e PDFs escaneados - uso IA visual
• multi_sheet: Para Excel com várias abas - analiso a estrutura
• ai_extraction: Para texto livre - uso IA generativa para extrair

Escolhi a estratégia que garante máxima precisão para este arquivo.`,
};

// =============================================================================
// Loading States
// =============================================================================

export const LOADING_EXPLANATIONS: Record<string, NexoExplanation> = {
  uploading: {
    summary: "Estou recebendo seu arquivo e armazenando de forma segura...",
    details: "Uso URLs assinadas temporárias para garantir a segurança dos seus dados.",
  },
  recalling: {
    summary: "Consultando minha memória para encontrar importações similares...",
    details: "Estou buscando episódios passados que possam me ajudar nesta importação.",
  },
  analyzing: {
    summary: "Analisando a estrutura e detectando padrões...",
    details: "Estou identificando abas, colunas e tipos de dados automaticamente.",
  },
  mapping: {
    summary: "Mapeando colunas para campos do sistema...",
    details: "Estou comparando nomes de colunas com campos conhecidos do SGA.",
  },
  generating: {
    summary: "Gerando perguntas inteligentes para você...",
    details: "Estou criando perguntas baseadas em ambiguidades que detectei e no histórico.",
  },
};

// =============================================================================
// Error State
// =============================================================================

export const ERROR_EXPLANATION: NexoExplanation = {
  summary: "Ops! Encontrei um problema. Veja abaixo o que pode ter causado.",
  details: `Soluções comuns para me ajudar:

1. Arquivo muito grande: Máximo 50MB
2. Formato não suportado: Use XML, PDF, CSV, XLSX, JPG, PNG, TXT
3. Arquivo corrompido: Reexporte do sistema de origem
4. Timeout: Arquivo muito complexo - tente simplificar ou dividir
5. Erro de rede: Verifique sua conexão e tente novamente`,
  action: "Corrija o problema e vamos tentar de novo!",
};

// =============================================================================
// Success State
// =============================================================================

export const SUCCESS_EXPLANATION: NexoExplanation = {
  summary: "Análise completa! Revise os dados e me diga se está tudo certo.",
  details: `Consegui analisar com sucesso:

• Estrutura do arquivo detectada
• Colunas mapeadas para campos do sistema
• Perguntas geradas para esclarecer dúvidas

Agora é sua vez de revisar e ajustar se necessário.`,
  action: "Revise e clique em 'Confirmar Importação'.",
};

// =============================================================================
// Confidence Badges Tooltip
// =============================================================================

export const CONFIDENCE_BADGE_EXPLANATIONS: Record<string, string> = {
  high: "Confiança alta (80%+): Tenho quase certeza que este mapeamento está correto.",
  medium: "Confiança média (50-79%): Provavelmente correto, mas vale você verificar.",
  low: "Confiança baixa (<50%): Estou incerto. Por favor, confirme manualmente.",
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
