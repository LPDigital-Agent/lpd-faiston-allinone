"use client";

import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/shared/glass-card";
import { AssetManagementHeader } from "@/components/ferramentas/ativos/asset-management-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
  Package,
  Search,
  Filter,
  Plus,
  Download,
  MoreVertical,
  ChevronRight,
} from "lucide-react";
import {
  mockAssets,
} from "@/mocks/ativos-mock-data";
import {
  ASSET_STATUS_LABELS,
  ASSET_STATUS_COLORS,
  ASSET_CATEGORY_LABELS,
  formatCurrency,
} from "@/lib/ativos/constants";
import { motion } from "framer-motion";

/**
 * Gestão de Estoque Page - Asset Inventory Management
 *
 * Lists all assets with search, filtering, and CRUD operations.
 */

export default function EstoquePage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <AssetManagementHeader
        title="Gestão de Estoque"
        subtitle="Gerencie todos os ativos do seu inventário"
        primaryAction={{
          label: "Novo Ativo",
          onClick: () => console.log("Novo ativo"),
          icon: <Plus className="w-4 h-4" />,
        }}
        secondaryActions={[
          {
            label: "Exportar",
            onClick: () => console.log("Exportar"),
            icon: <Download className="w-4 h-4" />,
          },
        ]}
      />

      {/* Filters Bar */}
      <GlassCard className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <Input
              placeholder="Buscar por nome, código ou serial..."
              className="pl-10 bg-white/5 border-border"
            />
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="border-border">
              <Filter className="w-4 h-4 mr-2" />
              Filtros
            </Button>
          </div>
        </div>

        {/* Quick Filters */}
        <div className="flex gap-2 mt-4 overflow-x-auto pb-2">
          <Badge variant="outline" className="cursor-pointer hover:bg-white/10 whitespace-nowrap">
            Todos ({mockAssets.length})
          </Badge>
          <Badge variant="outline" className="cursor-pointer hover:bg-white/10 bg-green-500/10 text-green-400 border-green-500/30 whitespace-nowrap">
            Disponíveis ({mockAssets.filter(a => a.status === "disponivel").length})
          </Badge>
          <Badge variant="outline" className="cursor-pointer hover:bg-white/10 bg-blue-500/10 text-blue-400 border-blue-500/30 whitespace-nowrap">
            Em Uso ({mockAssets.filter(a => a.status === "em_uso").length})
          </Badge>
          <Badge variant="outline" className="cursor-pointer hover:bg-white/10 bg-yellow-500/10 text-yellow-400 border-yellow-500/30 whitespace-nowrap">
            Manutenção ({mockAssets.filter(a => a.status === "manutencao").length})
          </Badge>
        </div>
      </GlassCard>

      {/* Asset List */}
      <GlassCard>
        <GlassCardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <Package className="w-4 h-4 text-blue-light" />
              <GlassCardTitle>Lista de Ativos</GlassCardTitle>
            </div>
            <Badge variant="outline">{mockAssets.length} ativos</Badge>
          </div>
        </GlassCardHeader>

        {/* Table Header */}
        <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-3 border-b border-border text-xs font-medium text-text-muted uppercase tracking-wider">
          <div className="col-span-4">Ativo</div>
          <div className="col-span-2">Categoria</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-2">Valor</div>
          <div className="col-span-2 text-right">Ações</div>
        </div>

        {/* Table Body */}
        <ScrollArea className="max-h-[500px]">
          <div className="divide-y divide-border">
            {mockAssets.map((asset, index) => (
              <motion.div
                key={asset.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="grid grid-cols-1 md:grid-cols-12 gap-4 px-4 py-4 hover:bg-white/5 transition-colors cursor-pointer items-center"
              >
                {/* Asset Info */}
                <div className="col-span-4 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-mid/20 flex items-center justify-center shrink-0">
                    <Package className="w-5 h-5 text-blue-light" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {asset.nome}
                    </p>
                    <p className="text-xs text-text-muted truncate">
                      {asset.codigo} • {asset.localizacao.nome}
                    </p>
                  </div>
                </div>

                {/* Category */}
                <div className="col-span-2">
                  <Badge variant="outline" className="text-xs">
                    {ASSET_CATEGORY_LABELS[asset.categoria]}
                  </Badge>
                </div>

                {/* Status */}
                <div className="col-span-2">
                  <Badge className={ASSET_STATUS_COLORS[asset.status]}>
                    {ASSET_STATUS_LABELS[asset.status]}
                  </Badge>
                </div>

                {/* Value */}
                <div className="col-span-2">
                  <p className="text-sm text-text-primary">
                    {formatCurrency(asset.valorAtual)}
                  </p>
                  <p className="text-xs text-text-muted">
                    Aquisição: {formatCurrency(asset.valorAquisicao)}
                  </p>
                </div>

                {/* Actions */}
                <div className="col-span-2 flex items-center justify-end gap-2">
                  <Button variant="ghost" size="sm" className="text-text-muted hover:text-text-primary">
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </motion.div>
            ))}
          </div>
        </ScrollArea>

        {/* Pagination */}
        <div className="flex items-center justify-between p-4 border-t border-border">
          <p className="text-sm text-text-muted">
            Mostrando 1-{mockAssets.length} de {mockAssets.length} ativos
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled>
              Anterior
            </Button>
            <Button variant="outline" size="sm" disabled>
              Próximo
            </Button>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
