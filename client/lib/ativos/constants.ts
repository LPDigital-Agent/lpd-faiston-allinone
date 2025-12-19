/**
 * Constants for Gestão de Ativos (Asset Management) module
 *
 * Contains navigation configuration, status colors, labels,
 * and other constants used throughout the module.
 */

import {
  LayoutDashboard,
  Package,
  Truck,
  RotateCcw,
  MapPin,
  MessageSquare,
  FileText,
} from "lucide-react";
import type { AssetNavModule, AssetStatus, AssetCategory } from "./types";

// =============================================================================
// Navigation Modules
// =============================================================================

/**
 * Asset management navigation modules (horizontal tabs)
 */
export const ASSET_NAV_MODULES: AssetNavModule[] = [
  {
    id: "dashboard",
    label: "Dashboards",
    labelShort: "Dash",
    href: "/ferramentas/ativos/dashboard",
    icon: LayoutDashboard,
  },
  {
    id: "estoque",
    label: "Gestão de Estoque",
    labelShort: "Estoque",
    href: "/ferramentas/ativos/estoque",
    icon: Package,
  },
  {
    id: "expedicao",
    label: "Expedição",
    labelShort: "Exped.",
    href: "/ferramentas/ativos/expedicao",
    icon: Truck,
  },
  {
    id: "reversa",
    label: "Reversa e Rastreabilidade",
    labelShort: "Reversa",
    href: "/ferramentas/ativos/reversa",
    icon: RotateCcw,
  },
  {
    id: "tracking",
    label: "Tracking e Logística",
    labelShort: "Tracking",
    href: "/ferramentas/ativos/tracking",
    icon: MapPin,
  },
  {
    id: "comunicacao",
    label: "Comunicação",
    labelShort: "Comunic.",
    href: "/ferramentas/ativos/comunicacao",
    icon: MessageSquare,
  },
  {
    id: "fiscal",
    label: "Fiscal e Contábil",
    labelShort: "Fiscal",
    href: "/ferramentas/ativos/fiscal",
    icon: FileText,
  },
];

// =============================================================================
// Status Configuration
// =============================================================================

/**
 * Asset status labels in Portuguese
 */
export const ASSET_STATUS_LABELS: Record<AssetStatus, string> = {
  disponivel: "Disponível",
  em_uso: "Em Uso",
  manutencao: "Manutenção",
  em_transito: "Em Trânsito",
  baixado: "Baixado",
};

/**
 * Asset status colors (CSS classes)
 */
export const ASSET_STATUS_COLORS: Record<AssetStatus, string> = {
  disponivel: "bg-green-500/20 text-green-400 border-green-500/30",
  em_uso: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  manutencao: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  em_transito: "bg-magenta-mid/20 text-magenta-light border-magenta-mid/30",
  baixado: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

/**
 * Asset status dot colors for indicators
 */
export const ASSET_STATUS_DOT_COLORS: Record<AssetStatus, string> = {
  disponivel: "bg-green-500",
  em_uso: "bg-blue-500",
  manutencao: "bg-yellow-500",
  em_transito: "bg-magenta-mid",
  baixado: "bg-zinc-500",
};

// =============================================================================
// Category Configuration
// =============================================================================

/**
 * Asset category labels in Portuguese
 */
export const ASSET_CATEGORY_LABELS: Record<AssetCategory, string> = {
  hardware: "Hardware",
  mobiliario: "Mobiliário",
  veiculos: "Veículos",
  equipamentos: "Equipamentos",
  software: "Software",
  outros: "Outros",
};

/**
 * Asset category colors
 */
export const ASSET_CATEGORY_COLORS: Record<AssetCategory, string> = {
  hardware: "bg-blue-500/20 text-blue-400",
  mobiliario: "bg-amber-500/20 text-amber-400",
  veiculos: "bg-emerald-500/20 text-emerald-400",
  equipamentos: "bg-purple-500/20 text-purple-400",
  software: "bg-cyan-500/20 text-cyan-400",
  outros: "bg-zinc-500/20 text-zinc-400",
};

// =============================================================================
// Alert Configuration
// =============================================================================

/**
 * Alert level colors
 */
export const ALERT_LEVEL_COLORS = {
  info: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
};

/**
 * Alert level icons (icon names from lucide-react)
 */
export const ALERT_LEVEL_ICONS = {
  info: "Info",
  warning: "AlertTriangle",
  error: "AlertCircle",
};

// =============================================================================
// Shipping Configuration
// =============================================================================

/**
 * Shipping status labels
 */
export const SHIPPING_STATUS_LABELS = {
  pendente: "Pendente",
  em_preparo: "Em Preparo",
  enviado: "Enviado",
  entregue: "Entregue",
  cancelado: "Cancelado",
};

/**
 * Shipping status colors
 */
export const SHIPPING_STATUS_COLORS = {
  pendente: "bg-zinc-500/20 text-zinc-400",
  em_preparo: "bg-yellow-500/20 text-yellow-400",
  enviado: "bg-blue-500/20 text-blue-400",
  entregue: "bg-green-500/20 text-green-400",
  cancelado: "bg-red-500/20 text-red-400",
};

// =============================================================================
// Fiscal Configuration
// =============================================================================

/**
 * Fiscal document type labels
 */
export const FISCAL_DOC_TYPE_LABELS = {
  nfe: "NF-e",
  nfse: "NFS-e",
  cte: "CT-e",
};

/**
 * Fiscal status labels
 */
export const FISCAL_STATUS_LABELS = {
  autorizado: "Autorizado",
  pendente: "Pendente",
  cancelado: "Cancelado",
  denegado: "Denegado",
};

/**
 * Fiscal status colors
 */
export const FISCAL_STATUS_COLORS = {
  autorizado: "bg-green-500/20 text-green-400",
  pendente: "bg-yellow-500/20 text-yellow-400",
  cancelado: "bg-zinc-500/20 text-zinc-400",
  denegado: "bg-red-500/20 text-red-400",
};

// =============================================================================
// Message Configuration
// =============================================================================

/**
 * Message priority labels
 */
export const MESSAGE_PRIORITY_LABELS = {
  alta: "Alta Prioridade",
  normal: "Normal",
  baixa: "Baixa Prioridade",
};

/**
 * Message priority colors
 */
export const MESSAGE_PRIORITY_COLORS = {
  alta: "bg-red-500/20 text-red-400",
  normal: "bg-zinc-500/20 text-zinc-400",
  baixa: "bg-blue-500/20 text-blue-400",
};

// =============================================================================
// Pagination Defaults
// =============================================================================

export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

// =============================================================================
// Format Helpers
// =============================================================================

/**
 * Format currency value to BRL
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

/**
 * Format percentage
 */
export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

/**
 * Format large numbers with abbreviations
 */
export function formatCompactNumber(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toString();
}
