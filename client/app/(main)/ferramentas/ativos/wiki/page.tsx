'use client';

/**
 * Wiki Page - SGA Inventory Module User Guide
 *
 * Comprehensive user documentation for the Estoque (Inventory) management system.
 * All content in Brazilian Portuguese following Faiston brand guidelines.
 */

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  BookOpen,
  Search,
  ChevronDown,
  ChevronRight,
  LayoutDashboard,
  Package,
  ArrowRightLeft,
  ClipboardCheck,
  Inbox,
  Sparkles,
  Smartphone,
  Activity,
  FileText,
  MapPin,
  Users,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Truck,
  RotateCcw,
  Barcode,
  Wifi,
  WifiOff,
  HelpCircle,
} from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface WikiSection {
  id: string;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  content: string;
}

// =============================================================================
// Wiki Content (Portuguese)
// =============================================================================

const WIKI_SECTIONS: WikiSection[] = [
  {
    id: 'visao-geral',
    title: 'Visao Geral do Sistema',
    icon: LayoutDashboard,
    content: `
## O que e o SGA?

O **SGA (Sistema de Gestao de Ativos)** e uma plataforma completa para gerenciamento de inventario e ativos da Faiston. O modulo de **Estoque** permite controlar todo o ciclo de vida dos materiais: entrada, armazenamento, movimentacao e saida.

### Principais Funcionalidades

- **Gestao de Inventario**: Controle de saldos por localizacao e projeto
- **Entrada via NF-e**: Upload automatico de notas fiscais com extracao por IA
- **Movimentacoes**: Reservas, expedicoes, transferencias e ajustes
- **Contagem Fisica**: Campanhas de inventario com deteccao de divergencias
- **Aprovacoes (HIL)**: Workflow de aprovacao para operacoes sensiveis
- **NEXO Copilot**: Assistente IA para consultas rapidas

### Dashboard

O dashboard apresenta os principais KPIs:

| Metrica | Descricao |
|---------|-----------|
| **Total de Ativos** | Quantidade total de itens no estoque |
| **Tarefas Pendentes** | Aprovacoes aguardando acao |
| **Movimentacoes Hoje** | Entradas e saidas do dia |
| **Divergencias Abertas** | Pendencias de inventario |

### Navegacao

Use o menu horizontal para acessar os modulos:
- **Dashboard** - Visao geral e KPIs
- **Estoque** - Gestao de inventario (voce esta aqui)
- **Expedicao** - Envios para campo
- **Reversa** - Retornos de clientes
- **Tracking** - Rastreamento de envios
- **Comunicacao** - Notificacoes e alertas
- **Fiscal** - Documentos fiscais
`,
  },
  {
    id: 'cadastros',
    title: 'Cadastros (Master Data)',
    icon: Package,
    content: `
## Dados Mestres

Os cadastros sao a base do sistema. Antes de realizar movimentacoes, e necessario ter os dados mestres configurados.

### Part Numbers (PN)

O catalogo de produtos define todos os itens gerenciaveis:

| Campo | Descricao | Obrigatorio |
|-------|-----------|-------------|
| **Codigo** | Identificador unico (SKU) | Sim |
| **Descricao** | Nome do produto | Sim |
| **Unidade** | UN, CX, KG, etc. | Sim |
| **NCM** | Codigo fiscal | Nao |
| **Fabricante** | Nome do fabricante | Nao |
| **Serializado** | Se cada unidade tem serial | Sim |
| **Custo Unitario** | Valor de referencia | Nao |

**Como criar um Part Number:**
1. Acesse **Cadastros > Part Numbers**
2. Clique em **+ Novo PN**
3. Preencha os campos obrigatorios
4. Se o item for **serializado**, cada unidade tera um numero de serie unico

> **Atencao:** A criacao de novos PNs requer aprovacao de um gestor (HIL).

### Localizacoes

Define onde os materiais podem ser armazenados:

| Tipo | Descricao | Exemplo |
|------|-----------|---------|
| **WAREHOUSE** | Almoxarifado principal | ALM-SP-01 |
| **SHELF** | Prateleira | PRAT-A1 |
| **BIN** | Gaveta ou bin | BIN-001 |
| **CUSTOMER** | Local do cliente | CLI-ACME-SP |
| **TRANSIT** | Em transito | TRANSITO-SP-RJ |
| **VIRTUAL** | Localizacao logica | QUARENTENA |

**Locais Restritos:**
- **COFRE**: Itens de alto valor (requer aprovacao HIL)
- **QUARENTENA**: Itens com problema (requer aprovacao HIL)
- **DESCARTE**: Itens para baixa (requer aprovacao HIL)

### Projetos

Associa materiais a clientes ou contratos:

- **Codigo**: Identificador do projeto
- **Nome**: Nome descritivo
- **Cliente**: Empresa contratante
- **Gerente**: Responsavel pelo projeto
- **Periodo**: Data inicio e fim

> **Dica:** Movimentacoes entre projetos diferentes requerem aprovacao.
`,
  },
  {
    id: 'movimentacoes',
    title: 'Movimentacoes',
    icon: ArrowRightLeft,
    content: `
## Tipos de Movimentacao

O sistema suporta diversos tipos de movimentacao de materiais.

### Entrada (NF-e)

Internalizacao de materiais via Nota Fiscal Eletronica:

**Passo a passo:**
1. Acesse **Movimentacoes > Entrada**
2. Selecione o **Local de destino** e **Projeto**
3. Faca upload do arquivo **XML** ou **PDF** da NF-e
4. O sistema extrai automaticamente os itens usando IA
5. Revise o **mapeamento** dos itens com os Part Numbers
6. Confirme a entrada

**Score de Confianca:**
- **>= 80%**: Entrada aprovada automaticamente
- **< 80%**: Requer revisao manual (HIL)
- **Itens nao mapeados**: Sempre requer aprovacao

### Expedicao (Saida)

Envio de materiais para campo ou cliente:

1. Acesse **Movimentacoes > Saida**
2. Selecione uma **reserva existente** ou crie uma nova
3. Informe o **destino** e **chamado/OS**
4. Confirme os itens a expedir
5. O sistema atualiza o saldo automaticamente

### Transferencia

Movimentacao entre locais internos:

1. Acesse **Movimentacoes > Transferencia**
2. Selecione **Origem** e **Destino**
3. Escolha os itens a transferir
4. Informe o **motivo**
5. Confirme a operacao

> **Nota:** Transferencias para locais restritos (COFRE, QUARENTENA) requerem aprovacao.

### Reserva

Bloqueio temporario de materiais para expedicao futura:

- **Validade**: Reservas expiram automaticamente (configuravel)
- **Cancelamento**: Pode ser cancelada antes da expedicao
- **Cross-project**: Reservas entre projetos requerem aprovacao

### Ajuste

Correcao de saldos para acertar divergencias:

| Tipo | Descricao |
|------|-----------|
| **Ajuste (+)** | Adiciona quantidade ao saldo |
| **Ajuste (-)** | Remove quantidade do saldo |

> **IMPORTANTE:** Todos os ajustes requerem aprovacao de um gestor (HIL).
`,
  },
  {
    id: 'inventario',
    title: 'Inventario e Contagem',
    icon: ClipboardCheck,
    content: `
## Campanhas de Inventario

O modulo de inventario permite realizar contagens fisicas periodicas.

### Estados da Campanha

| Status | Descricao |
|--------|-----------|
| **DRAFT** | Campanha em preparacao |
| **ACTIVE** | Contagem em andamento |
| **ANALYSIS** | Analisando divergencias |
| **COMPLETED** | Campanha finalizada |
| **CANCELLED** | Campanha cancelada |

### Como Criar uma Campanha

1. Acesse **Inventario > Nova Campanha**
2. Defina o **nome** e **descricao**
3. Selecione os **locais** a contar
4. (Opcional) Filtre por **Part Numbers** especificos
5. Clique em **Criar Campanha**

### Processo de Contagem

1. **Iniciar Sessao**: Selecione o local e inicie a contagem
2. **Escanear/Informar**: Use o scanner ou informe manualmente
3. **Registrar Quantidade**: Para itens nao serializados
4. **Avancar**: O sistema mostra o proximo item

### Tipos de Divergencia

| Tipo | Descricao | Cor |
|------|-----------|-----|
| **POSITIVE** | Sobra (contado > sistema) | Verde |
| **NEGATIVE** | Falta (contado < sistema) | Vermelho |
| **SERIAL_MISMATCH** | Serial encontrado em local errado | Laranja |
| **LOCATION_MISMATCH** | Item em local incorreto | Amarelo |

### Resolucao de Divergencias

1. Acesse **Inventario > [Campanha] > Divergencias**
2. Analise cada divergencia
3. Clique em **Propor Ajuste**
4. Informe o **motivo** da diferenca
5. O sistema cria uma tarefa de aprovacao (HIL)

> **Nota:** Ajustes de inventario SEMPRE requerem aprovacao de gestor.
`,
  },
  {
    id: 'aprovacoes',
    title: 'Aprovacoes (HIL)',
    icon: Inbox,
    content: `
## Human-in-the-Loop (HIL)

O sistema implementa workflows de aprovacao para operacoes sensiveis.

### Task Inbox

A caixa de tarefas mostra todas as aprovacoes pendentes:

- **Badge vermelho**: Indica tarefas pendentes no menu
- **Prioridade**: LOW, MEDIUM, HIGH, URGENT
- **Ordenacao**: Tarefas urgentes aparecem primeiro

### Tipos de Tarefa

| Tipo | Descricao | Quando Ocorre |
|------|-----------|---------------|
| **ADJUSTMENT_APPROVAL** | Aprovacao de ajuste | Sempre que houver ajuste |
| **ENTRY_REVIEW** | Revisao de entrada | NF-e com baixa confianca |
| **TRANSFER_APPROVAL** | Aprovacao de transferencia | Transferencia p/ local restrito |
| **DISPOSAL_APPROVAL** | Aprovacao de baixa | Descarte de material |
| **NEW_PN_APPROVAL** | Aprovacao de novo PN | Criacao de Part Number |

### Matriz de Decisao

| Operacao | Autonomo | HIL Obrigatorio |
|----------|----------|-----------------|
| Reserva mesmo projeto | Sim | - |
| Reserva cross-project | - | Sim |
| Transferencia normal | Sim | - |
| Transferencia p/ COFRE | - | Sim |
| Entrada NF-e (>= 80%) | Sim | - |
| Entrada NF-e (< 80%) | - | Sim |
| Ajuste de inventario | - | **SEMPRE** |
| Descarte/Perda | - | **SEMPRE** |

### Como Aprovar/Rejeitar

1. Acesse a **Task Inbox** no dashboard
2. Clique na tarefa pendente
3. Revise os detalhes da operacao
4. Clique em **Aprovar** ou **Rejeitar**
5. (Se rejeitar) Informe o motivo

### Hierarquia de Aprovacao

| Nivel | Role | Pode Aprovar |
|-------|------|--------------|
| 1 | OPERATOR | Operacoes basicas |
| 2 | MANAGER | Transferencias, ajustes |
| 3 | SUPERVISOR | Baixas, cross-project |
| 4 | DIRECTOR | Todas as operacoes |
`,
  },
  {
    id: 'nexo',
    title: 'NEXO - Assistente IA',
    icon: Sparkles,
    content: `
## NEXO Copilot

O **NEXO** e o assistente de IA integrado ao modulo de Estoque.

### Como Acessar

- Clique no icone **NEXO** no canto inferior direito
- Ou use o atalho **Ctrl+K** / **Cmd+K**

### Comandos Rapidos

O NEXO oferece botoes de acao rapida:

| Comando | O que faz |
|---------|-----------|
| **Verificar saldo** | Consulta saldo de um PN ou local |
| **Localizar serial** | Encontra a localizacao de um serial |
| **Reversas pendentes** | Lista retornos aguardando |
| **Minhas tarefas** | Mostra suas aprovacoes pendentes |
| **Itens abaixo do minimo** | Alerta de estoque baixo |
| **Movimentacoes hoje** | Resumo do dia |

### Exemplos de Perguntas

Voce pode fazer perguntas em linguagem natural:

- *"Qual o saldo do PN 12345 no almoxarifado SP?"*
- *"Onde esta o serial SN-ABC-123?"*
- *"Quantas entradas tivemos essa semana?"*
- *"Quais itens estao em quarentena?"*
- *"Me mostra as ultimas 5 movimentacoes do projeto ACME"*

### Sugestoes Inteligentes

Apos cada resposta, o NEXO sugere proximas acoes:

- **Criar reserva** se voce consultou saldo
- **Ver timeline** se voce localizou um serial
- **Exportar relatorio** para consultas de historico

### Limitacoes

- O NEXO consulta apenas dados do modulo de Estoque
- Operacoes de escrita (reservas, ajustes) devem ser feitas pelos menus
- Historico de conversa e mantido apenas na sessao atual

> **Dica:** Seja especifico nas perguntas para respostas mais precisas.
`,
  },
  {
    id: 'mobile',
    title: 'Mobile / PWA',
    icon: Smartphone,
    content: `
## Funcionalidades Mobile

O sistema oferece componentes otimizados para uso em dispositivos moveis.

### Scanner de Codigo de Barras

Use a camera do celular para escanear:

1. Acesse qualquer tela de movimentacao
2. Clique no icone de **camera/barcode**
3. Aponte para o codigo de barras ou QR Code
4. O sistema identifica automaticamente o serial

**Formatos suportados:**
- Code 128, Code 39, EAN-13
- QR Code
- Data Matrix

**Modo manual:**
- Digite o serial no campo de busca
- Use para codigos danificados ou ilegíveis

### Checklist de Contagem

Na tela de inventario mobile:

- **Progresso visual**: Barra mostra % concluido
- **Lista simplificada**: Um item por vez
- **Botoes grandes**: Facil de usar com uma mao
- **Confirmacao deslizante**: Swipe para confirmar

### Modo Offline

O sistema funciona mesmo sem internet:

| Status | Indicador | Comportamento |
|--------|-----------|---------------|
| **Online** | Icone verde | Sincronizacao em tempo real |
| **Offline** | Icone vermelho | Operacoes em fila local |
| **Sincronizando** | Icone amarelo | Enviando dados pendentes |

**Operacoes disponiveis offline:**
- Consulta de saldos (cache local)
- Registro de contagens
- Escaneamento de seriais

**Operacoes que requerem conexao:**
- Confirmacao de entradas
- Aprovacoes HIL
- Consultas ao NEXO

### Sincronizacao

Quando a conexao retornar:

1. O sistema detecta automaticamente
2. Envia operacoes da fila local
3. Atualiza dados do servidor
4. Notifica conflitos (se houver)

> **Dica:** Verifique o indicador de conexao antes de operacoes criticas.
`,
  },
  {
    id: 'status',
    title: 'Status e Estados',
    icon: Activity,
    content: `
## Ciclo de Vida dos Ativos

Os ativos passam por diferentes estados ao longo de seu ciclo de vida.

### Status de Ativos

| Status | Cor | Descricao |
|--------|-----|-----------|
| **AVAILABLE** | Verde | Disponivel para uso |
| **RESERVED** | Amarelo | Reservado para expedicao |
| **IN_TRANSIT** | Azul | Em transporte |
| **WITH_CUSTOMER** | Magenta | No cliente/campo |
| **IN_REPAIR** | Laranja | Em manutencao |
| **QUARANTINE** | Vermelho | Aguardando analise |
| **DISPOSED** | Cinza | Baixado/descartado |

### Transicoes Permitidas

**De AVAILABLE:**
- -> RESERVED (via reserva)
- -> IN_TRANSIT (via expedicao direta)
- -> QUARANTINE (via ajuste)
- -> DISPOSED (via baixa aprovada)

**De RESERVED:**
- -> AVAILABLE (via cancelamento)
- -> IN_TRANSIT (via expedicao)

**De IN_TRANSIT:**
- -> WITH_CUSTOMER (confirmacao de entrega)
- -> AVAILABLE (retorno ao estoque)

**De WITH_CUSTOMER:**
- -> IN_TRANSIT (via reversa)
- -> IN_REPAIR (defeito reportado)

**De IN_REPAIR:**
- -> AVAILABLE (reparo concluido)
- -> DISPOSED (irreparavel)

**De QUARANTINE:**
- -> AVAILABLE (liberado)
- -> DISPOSED (rejeitado)

### Status de Movimentacoes

| Tipo | Icone | Descricao |
|------|-------|-----------|
| **ENTRY** | Seta para baixo | Entrada no estoque |
| **EXIT** | Seta para cima | Saida do estoque |
| **TRANSFER** | Setas duplas | Movimentacao interna |
| **ADJUSTMENT_IN** | + | Ajuste positivo |
| **ADJUSTMENT_OUT** | - | Ajuste negativo |
| **RESERVE** | Cadeado | Bloqueio de saldo |
| **UNRESERVE** | Cadeado aberto | Liberacao de saldo |
| **RETURN** | Seta curva | Reversa/devolucao |

### Timeline do Ativo

Cada ativo possui um historico completo:

1. Acesse **Lista > [Ativo]**
2. Veja a aba **Timeline**
3. Todas as movimentacoes sao listadas cronologicamente
4. Clique em um evento para ver detalhes

> **Dica:** A timeline e imutavel - nenhum registro pode ser alterado ou excluido.
`,
  },
];

// =============================================================================
// Components
// =============================================================================

/**
 * Table of Contents - Sticky sidebar navigation
 */
function TableOfContents({
  sections,
  activeSection,
  onSectionClick,
}: {
  sections: WikiSection[];
  activeSection: string;
  onSectionClick: (id: string) => void;
}) {
  return (
    <GlassCard className="sticky top-24">
      <GlassCardHeader>
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-blue-light" />
          <GlassCardTitle>Conteudo</GlassCardTitle>
        </div>
      </GlassCardHeader>
      <GlassCardContent className="p-0">
        <nav className="py-2">
          {sections.map((section) => {
            const Icon = section.icon;
            const isActive = activeSection === section.id;
            return (
              <button
                key={section.id}
                onClick={() => onSectionClick(section.id)}
                className={`
                  w-full flex items-center gap-3 px-4 py-2.5 text-left transition-all
                  ${isActive
                    ? 'bg-blue-mid/20 text-blue-light border-l-2 border-blue-light'
                    : 'text-text-secondary hover:bg-white/5 hover:text-text-primary border-l-2 border-transparent'
                  }
                `}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-light' : 'text-text-muted'}`} />
                <span className="text-sm truncate">{section.title}</span>
              </button>
            );
          })}
        </nav>
      </GlassCardContent>
    </GlassCard>
  );
}

/**
 * Wiki Section - Collapsible content section
 */
function WikiSectionComponent({
  section,
  isExpanded,
  onToggle,
}: {
  section: WikiSection;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const Icon = section.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <GlassCard id={section.id} className="scroll-mt-24">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors rounded-t-xl"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-mid/20">
              <Icon className="w-5 h-5 text-blue-light" />
            </div>
            <h2 className="text-lg font-semibold text-text-primary">
              {section.title}
            </h2>
          </div>
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-5 h-5 text-text-muted" />
          </motion.div>
        </button>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <GlassCardContent className="pt-0 border-t border-white/5">
                <div className="prose prose-invert prose-sm max-w-none">
                  <WikiMarkdown content={section.content} />
                </div>
              </GlassCardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCard>
    </motion.div>
  );
}

/**
 * Simple Markdown Renderer for Wiki content
 */
function WikiMarkdown({ content }: { content: string }) {
  const lines = content.trim().split('\n');
  const elements: React.ReactNode[] = [];
  let currentList: string[] = [];
  let currentTable: string[][] = [];
  let inTable = false;
  let tableHeaders: string[] = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="list-disc list-inside space-y-1 my-3 text-text-secondary">
          {currentList.map((item, i) => (
            <li key={i}>{formatInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  const flushTable = () => {
    if (currentTable.length > 0) {
      elements.push(
        <div key={`table-${elements.length}`} className="overflow-x-auto my-4">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                {tableHeaders.map((header, i) => (
                  <th key={i} className="text-left py-2 px-3 text-text-primary font-medium">
                    {formatInlineMarkdown(header.trim())}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {currentTable.map((row, i) => (
                <tr key={i} className="border-b border-white/5">
                  {row.map((cell, j) => (
                    <td key={j} className="py-2 px-3 text-text-secondary">
                      {formatInlineMarkdown(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      currentTable = [];
      tableHeaders = [];
      inTable = false;
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Empty line
    if (!trimmed) {
      flushList();
      flushTable();
      return;
    }

    // Headers
    if (trimmed.startsWith('## ')) {
      flushList();
      flushTable();
      elements.push(
        <h3 key={index} className="text-base font-semibold text-text-primary mt-6 mb-3">
          {formatInlineMarkdown(trimmed.slice(3))}
        </h3>
      );
      return;
    }

    if (trimmed.startsWith('### ')) {
      flushList();
      flushTable();
      elements.push(
        <h4 key={index} className="text-sm font-semibold text-text-primary mt-4 mb-2">
          {formatInlineMarkdown(trimmed.slice(4))}
        </h4>
      );
      return;
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      flushList();
      flushTable();
      elements.push(
        <blockquote
          key={index}
          className="border-l-2 border-blue-light pl-4 py-2 my-3 text-text-secondary italic bg-blue-mid/10 rounded-r"
        >
          {formatInlineMarkdown(trimmed.slice(2))}
        </blockquote>
      );
      return;
    }

    // List items
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      flushTable();
      currentList.push(trimmed.slice(2));
      return;
    }

    // Numbered list
    if (/^\d+\.\s/.test(trimmed)) {
      flushTable();
      const match = trimmed.match(/^\d+\.\s(.*)$/);
      if (match) {
        currentList.push(match[1]);
      }
      return;
    }

    // Table
    if (trimmed.startsWith('|')) {
      flushList();
      const cells = trimmed.split('|').filter(c => c.trim());

      if (trimmed.includes('---')) {
        // Separator row - skip
        return;
      }

      if (!inTable) {
        tableHeaders = cells;
        inTable = true;
      } else {
        currentTable.push(cells);
      }
      return;
    }

    // Regular paragraph
    flushList();
    flushTable();
    elements.push(
      <p key={index} className="text-text-secondary my-2 leading-relaxed">
        {formatInlineMarkdown(trimmed)}
      </p>
    );
  });

  flushList();
  flushTable();

  return <>{elements}</>;
}

/**
 * Format inline markdown (bold, italic, code, links)
 */
function formatInlineMarkdown(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    if (boldMatch && boldMatch.index === 0) {
      parts.push(<strong key={key++} className="text-text-primary font-medium">{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    // Italic
    const italicMatch = remaining.match(/\*(.+?)\*/);
    if (italicMatch && italicMatch.index === 0) {
      parts.push(<em key={key++} className="italic">{italicMatch[1]}</em>);
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    // Inline code
    const codeMatch = remaining.match(/`(.+?)`/);
    if (codeMatch && codeMatch.index === 0) {
      parts.push(
        <code key={key++} className="px-1.5 py-0.5 bg-zinc-800 rounded text-blue-light text-xs font-mono">
          {codeMatch[1]}
        </code>
      );
      remaining = remaining.slice(codeMatch[0].length);
      continue;
    }

    // Find next special character
    const nextSpecial = remaining.search(/\*|`/);
    if (nextSpecial === -1) {
      parts.push(remaining);
      break;
    } else if (nextSpecial > 0) {
      parts.push(remaining.slice(0, nextSpecial));
      remaining = remaining.slice(nextSpecial);
    } else {
      parts.push(remaining[0]);
      remaining = remaining.slice(1);
    }
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function WikiPage() {
  const [activeSection, setActiveSection] = useState(WIKI_SECTIONS[0].id);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set([WIKI_SECTIONS[0].id])
  );
  const [searchTerm, setSearchTerm] = useState('');

  // Handle section click from TOC
  const handleSectionClick = (sectionId: string) => {
    setActiveSection(sectionId);

    // Expand if collapsed
    if (!expandedSections.has(sectionId)) {
      setExpandedSections(prev => new Set([...prev, sectionId]));
    }

    // Scroll to section
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Toggle section expansion
  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
    setActiveSection(sectionId);
  };

  // Filter sections by search
  const filteredSections = searchTerm
    ? WIKI_SECTIONS.filter(
        s =>
          s.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          s.content.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : WIKI_SECTIONS;

  // Expand all on search
  useEffect(() => {
    if (searchTerm) {
      setExpandedSections(new Set(filteredSections.map(s => s.id)));
    }
  }, [searchTerm, filteredSections]);

  return (
    <div className="flex gap-6">
      {/* Sidebar - Table of Contents (hidden on mobile) */}
      <aside className="w-64 shrink-0 hidden lg:block">
        <div className="sticky top-24 space-y-4">
          {/* Search */}
          <GlassCard>
            <GlassCardContent className="p-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <Input
                  type="text"
                  placeholder="Buscar na wiki..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-transparent border-white/10"
                />
              </div>
            </GlassCardContent>
          </GlassCard>

          {/* TOC */}
          <TableOfContents
            sections={WIKI_SECTIONS}
            activeSection={activeSection}
            onSectionClick={handleSectionClick}
          />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-magenta-dark/20">
                <BookOpen className="w-6 h-6 text-magenta-light" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-text-primary">
                  Wiki - Guia do Usuario
                </h1>
                <p className="text-sm text-text-muted mt-0.5">
                  Documentacao completa do modulo de Estoque
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-blue-light border-blue-light/30">
              {WIKI_SECTIONS.length} secoes
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setExpandedSections(new Set(WIKI_SECTIONS.map(s => s.id)))}
              className="text-xs"
            >
              Expandir Todas
            </Button>
          </div>
        </div>

        {/* Mobile Search */}
        <div className="lg:hidden">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <Input
              type="text"
              placeholder="Buscar na wiki..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 bg-transparent border-white/10"
            />
          </div>
        </div>

        {/* Sections */}
        <div className="space-y-4">
          {filteredSections.length === 0 ? (
            <GlassCard>
              <GlassCardContent className="py-12 text-center">
                <HelpCircle className="w-12 h-12 text-text-muted mx-auto mb-4" />
                <p className="text-text-secondary">
                  Nenhum resultado encontrado para &quot;{searchTerm}&quot;
                </p>
              </GlassCardContent>
            </GlassCard>
          ) : (
            filteredSections.map((section) => (
              <WikiSectionComponent
                key={section.id}
                section={section}
                isExpanded={expandedSections.has(section.id)}
                onToggle={() => toggleSection(section.id)}
              />
            ))
          )}
        </div>

        {/* Footer */}
        <div className="text-center py-8 text-text-muted text-sm">
          <p>Documentacao do SGA - Sistema de Gestao de Ativos</p>
          <p className="mt-1">Faiston NEXO &copy; 2026</p>
        </div>
      </main>
    </div>
  );
}
