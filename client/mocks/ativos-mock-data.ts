/**
 * Mock data for Gestão de Ativos (Asset Management) module
 *
 * Realistic mock data for development and demonstration purposes.
 * All data is in Brazilian Portuguese with proper formatting.
 */

import type {
  Asset,
  AssetMovement,
  DashboardStats,
  DashboardAlert,
  CategoryBreakdown,
  StatusBreakdown,
  ShippingOrder,
  ReturnRequest,
  FiscalDocument,
  TaxObligation,
  InternalMessage,
  AssetLocation,
  AssetResponsavel,
} from "@/lib/ativos/types";

// =============================================================================
// Locations
// =============================================================================

export const mockLocations: AssetLocation[] = [
  { id: "loc-001", nome: "Escritório São Paulo", tipo: "filial", cidade: "São Paulo", estado: "SP" },
  { id: "loc-002", nome: "Escritório Rio de Janeiro", tipo: "filial", cidade: "Rio de Janeiro", estado: "RJ" },
  { id: "loc-003", nome: "Estoque Central", tipo: "estoque", cidade: "São Paulo", estado: "SP" },
  { id: "loc-004", nome: "TI - Infraestrutura", tipo: "departamento", cidade: "São Paulo", estado: "SP" },
  { id: "loc-005", nome: "RH - Recursos Humanos", tipo: "departamento", cidade: "São Paulo", estado: "SP" },
  { id: "loc-006", nome: "Comercial", tipo: "departamento", cidade: "São Paulo", estado: "SP" },
  { id: "loc-007", nome: "Cliente Externo", tipo: "externo" },
];

// =============================================================================
// Users/Responsáveis
// =============================================================================

export const mockUsers: AssetResponsavel[] = [
  { id: "user-001", nome: "Fábio Santos", email: "fabio.santos@faiston.com", departamento: "TI" },
  { id: "user-002", nome: "Ana Silva", email: "ana.silva@faiston.com", departamento: "RH" },
  { id: "user-003", nome: "Carlos Oliveira", email: "carlos.oliveira@faiston.com", departamento: "Comercial" },
  { id: "user-004", nome: "Maria Costa", email: "maria.costa@faiston.com", departamento: "Financeiro" },
  { id: "user-005", nome: "Pedro Souza", email: "pedro.souza@faiston.com", departamento: "Operações" },
  { id: "user-006", nome: "Julia Ferreira", email: "julia.ferreira@faiston.com", departamento: "TI" },
];

// =============================================================================
// Assets
// =============================================================================

export const mockAssets: Asset[] = [
  {
    id: "asset-001",
    codigo: "FAI-NB-001",
    nome: "Notebook Dell XPS 15",
    categoria: "hardware",
    status: "em_uso",
    localizacao: mockLocations[0],
    responsavel: mockUsers[0],
    dataAquisicao: "2024-03-15",
    valorAquisicao: 12500,
    valorAtual: 10000,
    garantiaAte: "2027-03-15",
    numeroSerie: "SN-DELL-XPS-001234",
    fabricante: "Dell",
    modelo: "XPS 15 9530",
    notaFiscal: "NF-2024-001234",
    createdAt: "2024-03-15T10:00:00Z",
    updatedAt: "2024-12-10T14:30:00Z",
  },
  {
    id: "asset-002",
    codigo: "FAI-NB-002",
    nome: "MacBook Pro 14",
    categoria: "hardware",
    status: "em_uso",
    localizacao: mockLocations[0],
    responsavel: mockUsers[5],
    dataAquisicao: "2024-05-20",
    valorAquisicao: 18500,
    valorAtual: 16000,
    garantiaAte: "2026-05-20",
    numeroSerie: "SN-APPLE-MBP-005678",
    fabricante: "Apple",
    modelo: "MacBook Pro 14 M3",
    notaFiscal: "NF-2024-002345",
    createdAt: "2024-05-20T09:00:00Z",
    updatedAt: "2024-11-15T11:00:00Z",
  },
  {
    id: "asset-003",
    codigo: "FAI-MON-001",
    nome: "Monitor LG UltraWide 34\"",
    categoria: "hardware",
    status: "disponivel",
    localizacao: mockLocations[2],
    responsavel: mockUsers[4],
    dataAquisicao: "2024-02-10",
    valorAquisicao: 3200,
    valorAtual: 2800,
    garantiaAte: "2027-02-10",
    numeroSerie: "SN-LG-MON-003456",
    fabricante: "LG",
    modelo: "34WN80C-B",
    notaFiscal: "NF-2024-000567",
    createdAt: "2024-02-10T08:00:00Z",
    updatedAt: "2024-12-01T16:00:00Z",
  },
  {
    id: "asset-004",
    codigo: "FAI-NB-003",
    nome: "Notebook Lenovo ThinkPad",
    categoria: "hardware",
    status: "manutencao",
    localizacao: mockLocations[3],
    responsavel: mockUsers[2],
    dataAquisicao: "2023-08-15",
    valorAquisicao: 8500,
    valorAtual: 5500,
    garantiaAte: "2026-08-15",
    numeroSerie: "SN-LEN-TP-007890",
    fabricante: "Lenovo",
    modelo: "ThinkPad X1 Carbon",
    notaFiscal: "NF-2023-008901",
    observacoes: "Teclado com defeito - em manutenção",
    createdAt: "2023-08-15T11:00:00Z",
    updatedAt: "2024-12-18T09:00:00Z",
  },
  {
    id: "asset-005",
    codigo: "FAI-MESA-001",
    nome: "Mesa de Escritório Ergonômica",
    categoria: "mobiliario",
    status: "em_uso",
    localizacao: mockLocations[0],
    responsavel: mockUsers[0],
    dataAquisicao: "2024-01-10",
    valorAquisicao: 2800,
    valorAtual: 2500,
    fabricante: "Flexform",
    modelo: "Sigma Pro",
    notaFiscal: "NF-2024-000123",
    createdAt: "2024-01-10T10:00:00Z",
    updatedAt: "2024-06-15T14:00:00Z",
  },
  {
    id: "asset-006",
    codigo: "FAI-CAD-001",
    nome: "Cadeira Executiva Herman Miller",
    categoria: "mobiliario",
    status: "em_uso",
    localizacao: mockLocations[0],
    responsavel: mockUsers[1],
    dataAquisicao: "2024-01-10",
    valorAquisicao: 8500,
    valorAtual: 7800,
    fabricante: "Herman Miller",
    modelo: "Aeron",
    notaFiscal: "NF-2024-000124",
    createdAt: "2024-01-10T10:00:00Z",
    updatedAt: "2024-06-15T14:00:00Z",
  },
  {
    id: "asset-007",
    codigo: "FAI-VEI-001",
    nome: "Veículo Fiat Strada",
    categoria: "veiculos",
    status: "em_uso",
    localizacao: mockLocations[6],
    responsavel: mockUsers[4],
    dataAquisicao: "2023-06-01",
    valorAquisicao: 95000,
    valorAtual: 78000,
    numeroSerie: "9BD374127P0123456",
    fabricante: "Fiat",
    modelo: "Strada Freedom 1.3",
    notaFiscal: "NF-2023-005678",
    createdAt: "2023-06-01T08:00:00Z",
    updatedAt: "2024-12-01T10:00:00Z",
  },
  {
    id: "asset-008",
    codigo: "FAI-PROJ-001",
    nome: "Projetor Epson",
    categoria: "equipamentos",
    status: "disponivel",
    localizacao: mockLocations[2],
    responsavel: mockUsers[4],
    dataAquisicao: "2024-04-20",
    valorAquisicao: 4500,
    valorAtual: 4000,
    garantiaAte: "2027-04-20",
    numeroSerie: "SN-EPSON-PROJ-001",
    fabricante: "Epson",
    modelo: "PowerLite E20",
    notaFiscal: "NF-2024-003456",
    createdAt: "2024-04-20T09:00:00Z",
    updatedAt: "2024-10-10T15:00:00Z",
  },
  {
    id: "asset-009",
    codigo: "FAI-PHONE-001",
    nome: "iPhone 15 Pro",
    categoria: "hardware",
    status: "em_transito",
    localizacao: mockLocations[2],
    responsavel: mockUsers[2],
    dataAquisicao: "2024-11-01",
    valorAquisicao: 9500,
    valorAtual: 9200,
    garantiaAte: "2025-11-01",
    numeroSerie: "SN-APPLE-IP15-001",
    fabricante: "Apple",
    modelo: "iPhone 15 Pro 256GB",
    notaFiscal: "NF-2024-009876",
    createdAt: "2024-11-01T10:00:00Z",
    updatedAt: "2024-12-19T08:00:00Z",
  },
  {
    id: "asset-010",
    codigo: "FAI-NB-004",
    nome: "Notebook HP EliteBook",
    categoria: "hardware",
    status: "baixado",
    localizacao: mockLocations[2],
    responsavel: mockUsers[4],
    dataAquisicao: "2020-03-15",
    valorAquisicao: 6500,
    valorAtual: 0,
    numeroSerie: "SN-HP-EB-000123",
    fabricante: "HP",
    modelo: "EliteBook 840 G6",
    notaFiscal: "NF-2020-001234",
    observacoes: "Equipamento descontinuado por obsolescência",
    createdAt: "2020-03-15T10:00:00Z",
    updatedAt: "2024-12-01T11:00:00Z",
  },
];

// =============================================================================
// Asset Movements
// =============================================================================

export const mockMovements: AssetMovement[] = [
  {
    id: "mov-001",
    ativoId: "asset-001",
    tipo: "transferencia",
    origem: mockLocations[2],
    destino: mockLocations[0],
    responsavel: mockUsers[0],
    data: "2024-12-19T09:45:00Z",
    observacao: "Transferência para uso do colaborador",
  },
  {
    id: "mov-002",
    ativoId: "asset-003",
    tipo: "entrada",
    destino: mockLocations[2],
    responsavel: mockUsers[4],
    data: "2024-12-19T09:30:00Z",
    documentoRef: "NF-2024-012345",
  },
  {
    id: "mov-003",
    ativoId: "asset-009",
    tipo: "saida",
    origem: mockLocations[2],
    responsavel: mockUsers[2],
    data: "2024-12-19T09:15:00Z",
    observacao: "Envio para filial RJ",
  },
  {
    id: "mov-004",
    ativoId: "asset-004",
    tipo: "manutencao",
    origem: mockLocations[0],
    destino: mockLocations[3],
    responsavel: mockUsers[5],
    data: "2024-12-18T14:00:00Z",
    observacao: "Teclado com defeito",
  },
  {
    id: "mov-005",
    ativoId: "asset-010",
    tipo: "baixa",
    origem: mockLocations[0],
    responsavel: mockUsers[4],
    data: "2024-12-01T11:00:00Z",
    observacao: "Equipamento obsoleto - fim de vida útil",
  },
];

// =============================================================================
// Dashboard Statistics
// =============================================================================

export const mockDashboardAlerts: DashboardAlert[] = [
  {
    id: "alert-001",
    tipo: "warning",
    mensagem: "3 ativos sem localização definida",
    link: "/ferramentas/ativos/estoque?filter=sem_local",
    createdAt: "2024-12-19T08:00:00Z",
  },
  {
    id: "alert-002",
    tipo: "warning",
    mensagem: "5 garantias expiram neste mês",
    link: "/ferramentas/ativos/estoque?filter=garantia_expirando",
    createdAt: "2024-12-19T08:00:00Z",
  },
  {
    id: "alert-003",
    tipo: "info",
    mensagem: "Auditoria fiscal agendada para 25/12",
    link: "/ferramentas/ativos/fiscal",
    createdAt: "2024-12-18T10:00:00Z",
  },
  {
    id: "alert-004",
    tipo: "error",
    mensagem: "1 ativo em manutenção há mais de 30 dias",
    link: "/ferramentas/ativos/estoque?filter=manutencao_longa",
    createdAt: "2024-12-17T09:00:00Z",
  },
];

export const mockDashboardStats: DashboardStats = {
  totalAtivos: 1247,
  ativosDisponiveis: 823,
  ativosEmUso: 312,
  ativosEmTransito: 45,
  ativosManutencao: 42,
  ativosBaixados: 25,
  valorTotal: 2345678,
  valorDepreciacao: 456789,
  alertas: mockDashboardAlerts,
};

export const mockCategoryBreakdown: CategoryBreakdown[] = [
  { categoria: "hardware", quantidade: 687, valor: 1234567, percentual: 55.1 },
  { categoria: "mobiliario", quantidade: 312, valor: 456789, percentual: 25.0 },
  { categoria: "veiculos", quantidade: 45, valor: 456789, percentual: 3.6 },
  { categoria: "equipamentos", quantidade: 156, valor: 134567, percentual: 12.5 },
  { categoria: "software", quantidade: 32, valor: 45678, percentual: 2.6 },
  { categoria: "outros", quantidade: 15, valor: 17288, percentual: 1.2 },
];

export const mockStatusBreakdown: StatusBreakdown[] = [
  { status: "disponivel", quantidade: 823, percentual: 66.0 },
  { status: "em_uso", quantidade: 312, percentual: 25.0 },
  { status: "em_transito", quantidade: 45, percentual: 3.6 },
  { status: "manutencao", quantidade: 42, percentual: 3.4 },
  { status: "baixado", quantidade: 25, percentual: 2.0 },
];

// =============================================================================
// Shipping Orders
// =============================================================================

export const mockShippingOrders: ShippingOrder[] = [
  {
    id: "ship-001",
    codigo: "EXP-2024-001",
    cliente: "Empresa ABC Ltda",
    destino: mockLocations[1],
    status: "pendente",
    itens: [
      { ativoId: "asset-009", ativoCodigo: "FAI-PHONE-001", ativoNome: "iPhone 15 Pro", quantidade: 1 },
    ],
    dataCriacao: "2024-12-18T10:00:00Z",
    dataPrevista: "2024-12-20T18:00:00Z",
  },
  {
    id: "ship-002",
    codigo: "EXP-2024-002",
    cliente: "XYZ Tecnologia",
    destino: mockLocations[6],
    status: "em_preparo",
    itens: [
      { ativoId: "asset-003", ativoCodigo: "FAI-MON-001", ativoNome: "Monitor LG UltraWide 34\"", quantidade: 5 },
    ],
    dataCriacao: "2024-12-17T14:00:00Z",
    dataPrevista: "2024-12-21T12:00:00Z",
  },
  {
    id: "ship-003",
    codigo: "EXP-2024-003",
    cliente: "Tech Solutions",
    destino: mockLocations[6],
    status: "enviado",
    itens: [
      { ativoId: "asset-001", ativoCodigo: "FAI-NB-001", ativoNome: "Notebook Dell XPS 15", quantidade: 3 },
      { ativoId: "asset-002", ativoCodigo: "FAI-NB-002", ativoNome: "MacBook Pro 14", quantidade: 2 },
    ],
    dataCriacao: "2024-12-15T09:00:00Z",
    dataPrevista: "2024-12-19T18:00:00Z",
    dataEnvio: "2024-12-16T14:30:00Z",
    rastreio: "BR123456789SP",
  },
];

// =============================================================================
// Return Requests
// =============================================================================

export const mockReturnRequests: ReturnRequest[] = [
  {
    id: "ret-001",
    codigo: "REV-2024-001",
    ativoId: "asset-004",
    cliente: "Interno - Carlos Oliveira",
    motivo: "defeito",
    status: "em_analise",
    descricao: "Teclado com teclas falhando",
    dataSolicitacao: "2024-12-18T10:00:00Z",
    responsavel: mockUsers[5],
  },
  {
    id: "ret-002",
    codigo: "REV-2024-002",
    ativoId: "asset-008",
    cliente: "Cliente Externo XYZ",
    motivo: "troca",
    status: "aguardando",
    descricao: "Solicitação de upgrade para modelo superior",
    dataSolicitacao: "2024-12-17T15:00:00Z",
  },
];

// =============================================================================
// Fiscal Documents
// =============================================================================

export const mockFiscalDocuments: FiscalDocument[] = [
  {
    id: "fiscal-001",
    numero: "001234",
    tipo: "nfe",
    status: "autorizado",
    valor: 12500,
    dataEmissao: "2024-12-19T10:00:00Z",
    cliente: "Empresa ABC",
    chaveAcesso: "35241212345678000199550010000012341000012348",
  },
  {
    id: "fiscal-002",
    numero: "001235",
    tipo: "nfe",
    status: "autorizado",
    valor: 8200,
    dataEmissao: "2024-12-18T14:00:00Z",
    cliente: "XYZ Tech",
    chaveAcesso: "35241212345678000199550010000012351000012355",
  },
  {
    id: "fiscal-003",
    numero: "001236",
    tipo: "nfe",
    status: "pendente",
    valor: 45000,
    dataEmissao: "2024-12-19T09:00:00Z",
    cliente: "Tech Solutions",
  },
];

export const mockTaxObligations: TaxObligation[] = [
  {
    id: "tax-001",
    nome: "SPED Fiscal",
    prazo: "2024-12-25",
    status: "pendente",
    descricao: "Escrituração Fiscal Digital",
  },
  {
    id: "tax-002",
    nome: "DCTF",
    prazo: "2024-12-31",
    status: "enviado",
    descricao: "Declaração de Débitos e Créditos Tributários Federais",
  },
  {
    id: "tax-003",
    nome: "EFD-Contribuições",
    prazo: "2025-01-15",
    status: "pendente",
    descricao: "Escrituração Fiscal Digital das Contribuições",
  },
];

// =============================================================================
// Internal Messages
// =============================================================================

export const mockMessages: InternalMessage[] = [
  {
    id: "msg-001",
    assunto: "Atualização de Sistema - Manutenção Programada",
    conteudo: "Prezados colaboradores,\n\nInformamos que o sistema de gestão de ativos estará em manutenção programada no dia 21/12/2024, das 22h às 02h.\n\nDurante este período, o acesso ao sistema estará indisponível.\n\nAtenciosamente,\nEquipe de TI",
    remetente: mockUsers[0],
    departamento: "TI",
    prioridade: "alta",
    lida: false,
    favorita: false,
    dataEnvio: "2024-12-19T09:00:00Z",
  },
  {
    id: "msg-002",
    assunto: "Novo Processo de Requisição de Ativos",
    conteudo: "A partir de janeiro/2025, todas as requisições de novos ativos deverão ser feitas através do novo formulário eletrônico disponível no sistema.",
    remetente: mockUsers[1],
    departamento: "RH",
    prioridade: "normal",
    lida: true,
    favorita: false,
    dataEnvio: "2024-12-18T14:30:00Z",
  },
  {
    id: "msg-003",
    assunto: "Resultado Trimestral - Q4 2024",
    conteudo: "Compartilhamos os resultados do inventário trimestral de ativos. Acesse o relatório completo no anexo.",
    remetente: mockUsers[3],
    departamento: "Diretoria",
    prioridade: "normal",
    lida: true,
    favorita: true,
    dataEnvio: "2024-12-17T16:00:00Z",
    anexos: ["relatorio_q4_2024.pdf"],
  },
];

// =============================================================================
// Export all mock data
// =============================================================================

export const mockData = {
  locations: mockLocations,
  users: mockUsers,
  assets: mockAssets,
  movements: mockMovements,
  dashboardStats: mockDashboardStats,
  categoryBreakdown: mockCategoryBreakdown,
  statusBreakdown: mockStatusBreakdown,
  shippingOrders: mockShippingOrders,
  returnRequests: mockReturnRequests,
  fiscalDocuments: mockFiscalDocuments,
  taxObligations: mockTaxObligations,
  messages: mockMessages,
};

export default mockData;
