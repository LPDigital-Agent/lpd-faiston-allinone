"use client";

import { BentoGrid, BentoItem } from "@/components/dashboard/bento-grid";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/shared/glass-card";
import { AssetStatsCard } from "@/components/ferramentas/ativos/asset-stats-card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Package,
  PackageCheck,
  Truck,
  Wrench,
  AlertTriangle,
  TrendingUp,
  ArrowRight,
  Clock,
  MapPin,
  User,
  Plus,
  FileText,
  RefreshCcw,
} from "lucide-react";
import { formatCurrency } from "@/lib/ativos/constants";
import {
  mockDashboardStats,
  mockMovements,
  mockAssets,
  mockUsers,
  mockLocations,
} from "@/mocks/ativos-mock-data";
import { motion } from "framer-motion";

/**
 * Dashboard Page - Gestão de Ativos
 *
 * Main dashboard showing KPIs, recent movements, alerts,
 * and quick actions for asset management.
 */

export default function AssetDashboardPage() {
  const stats = mockDashboardStats;

  return (
    <div className="space-y-6">
      {/* KPI Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <AssetStatsCard
          title="Total de Ativos"
          value={stats.totalAtivos}
          icon={<Package className="w-5 h-5" />}
          trend={{ value: 5.2, direction: "up", label: "vs. mês anterior" }}
          color="blue"
          delay={0}
        />
        <AssetStatsCard
          title="Disponíveis"
          value={stats.ativosDisponiveis}
          icon={<PackageCheck className="w-5 h-5" />}
          trend={{ value: 2.1, direction: "up" }}
          color="green"
          delay={1}
        />
        <AssetStatsCard
          title="Em Trânsito"
          value={stats.ativosEmTransito}
          icon={<Truck className="w-5 h-5" />}
          trend={{ value: 12.5, direction: "up" }}
          color="magenta"
          delay={2}
        />
        <AssetStatsCard
          title="Manutenção"
          value={stats.ativosManutencao}
          icon={<Wrench className="w-5 h-5" />}
          trend={{ value: 3.4, direction: "down" }}
          color="yellow"
          delay={3}
        />
      </div>

      {/* Main Content Grid */}
      <BentoGrid>
        {/* Value Summary - 2 cols */}
        <BentoItem colSpan={2} delay={4}>
          <GlassCard className="h-full">
            <GlassCardHeader>
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-400" />
                <GlassCardTitle>Valor do Patrimônio</GlassCardTitle>
              </div>
            </GlassCardHeader>
            <GlassCardContent>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-3xl font-bold text-text-primary">
                    {formatCurrency(stats.valorTotal)}
                  </p>
                  <p className="text-sm text-text-muted mt-1">Valor total dos ativos</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-yellow-400">
                    {formatCurrency(stats.valorDepreciacao)}
                  </p>
                  <p className="text-sm text-text-muted mt-1">Depreciação acumulada</p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-border">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-text-muted">Taxa de utilização</span>
                  <span className="text-text-primary font-medium">
                    {((stats.ativosEmUso / stats.totalAtivos) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 h-2 bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(stats.ativosEmUso / stats.totalAtivos) * 100}%` }}
                    transition={{ delay: 0.5, duration: 0.8, ease: "easeOut" }}
                    className="h-full gradient-nexo rounded-full"
                  />
                </div>
              </div>
            </GlassCardContent>
          </GlassCard>
        </BentoItem>

        {/* Quick Actions - 2 cols */}
        <BentoItem colSpan={2} delay={5}>
          <GlassCard className="h-full">
            <GlassCardHeader>
              <GlassCardTitle>Ações Rápidas</GlassCardTitle>
            </GlassCardHeader>
            <GlassCardContent>
              <div className="grid grid-cols-2 gap-3">
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2 border-border hover:bg-white/5 hover:border-blue-mid/30"
                >
                  <div className="w-10 h-10 rounded-lg bg-blue-mid/20 flex items-center justify-center">
                    <Plus className="w-5 h-5 text-blue-light" />
                  </div>
                  <span className="text-sm">Novo Ativo</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2 border-border hover:bg-white/5 hover:border-magenta-mid/30"
                >
                  <div className="w-10 h-10 rounded-lg bg-magenta-mid/20 flex items-center justify-center">
                    <RefreshCcw className="w-5 h-5 text-magenta-light" />
                  </div>
                  <span className="text-sm">Transferir</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2 border-border hover:bg-white/5 hover:border-green-500/30"
                >
                  <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-green-400" />
                  </div>
                  <span className="text-sm">Relatório</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2 border-border hover:bg-white/5 hover:border-yellow-500/30"
                >
                  <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                    <Package className="w-5 h-5 text-yellow-400" />
                  </div>
                  <span className="text-sm">Inventário</span>
                </Button>
              </div>
            </GlassCardContent>
          </GlassCard>
        </BentoItem>

        {/* Recent Movements - 2 cols, 2 rows */}
        <BentoItem colSpan={2} rowSpan={2} delay={6}>
          <GlassCard className="h-full flex flex-col">
            <GlassCardHeader>
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-light" />
                  <GlassCardTitle>Movimentações Recentes</GlassCardTitle>
                </div>
                <Badge variant="outline" className="text-xs">
                  Hoje
                </Badge>
              </div>
            </GlassCardHeader>
            <ScrollArea className="flex-1">
              <div className="space-y-3 p-1">
                {mockMovements.slice(0, 5).map((movement, index) => {
                  const asset = mockAssets.find(a => a.id === movement.ativoId);
                  const typeColors: Record<string, string> = {
                    entrada: "bg-green-500/20 text-green-400",
                    saida: "bg-red-500/20 text-red-400",
                    transferencia: "bg-blue-500/20 text-blue-400",
                    baixa: "bg-zinc-500/20 text-zinc-400",
                    manutencao: "bg-yellow-500/20 text-yellow-400",
                  };
                  const typeLabels: Record<string, string> = {
                    entrada: "Entrada",
                    saida: "Saída",
                    transferencia: "Transferência",
                    baixa: "Baixa",
                    manutencao: "Manutenção",
                  };

                  return (
                    <motion.div
                      key={movement.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.6 + index * 0.1 }}
                      className="flex items-center gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
                    >
                      <div className="text-xs text-text-muted w-12 shrink-0">
                        {new Date(movement.data).toLocaleTimeString("pt-BR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-text-primary truncate">
                          {asset?.nome || "Ativo desconhecido"}
                        </p>
                        <p className="text-xs text-text-muted truncate">
                          {movement.observacao || `${movement.origem?.nome || ""} → ${movement.destino?.nome || ""}`}
                        </p>
                      </div>
                      <Badge className={typeColors[movement.tipo]}>
                        {typeLabels[movement.tipo]}
                      </Badge>
                    </motion.div>
                  );
                })}
              </div>
            </ScrollArea>
            <div className="p-3 border-t border-border">
              <Button variant="ghost" size="sm" className="w-full text-text-muted hover:text-text-primary">
                Ver todas as movimentações
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </GlassCard>
        </BentoItem>

        {/* Alerts - 2 cols, 2 rows */}
        <BentoItem colSpan={2} rowSpan={2} delay={7}>
          <GlassCard className="h-full flex flex-col">
            <GlassCardHeader>
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400" />
                  <GlassCardTitle>Alertas</GlassCardTitle>
                </div>
                <Badge variant="outline" className="text-xs bg-yellow-500/10 text-yellow-400 border-yellow-500/30">
                  {stats.alertas.length}
                </Badge>
              </div>
            </GlassCardHeader>
            <ScrollArea className="flex-1">
              <div className="space-y-2 p-1">
                {stats.alertas.map((alert, index) => {
                  const alertColors = {
                    info: "border-l-blue-500 bg-blue-500/5",
                    warning: "border-l-yellow-500 bg-yellow-500/5",
                    error: "border-l-red-500 bg-red-500/5",
                  };
                  const alertIcons = {
                    info: "text-blue-400",
                    warning: "text-yellow-400",
                    error: "text-red-400",
                  };

                  return (
                    <motion.div
                      key={alert.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.7 + index * 0.1 }}
                      className={`p-3 rounded-lg border-l-4 ${alertColors[alert.tipo]} cursor-pointer hover:bg-white/5 transition-colors`}
                    >
                      <div className="flex items-start gap-2">
                        <AlertTriangle className={`w-4 h-4 mt-0.5 ${alertIcons[alert.tipo]}`} />
                        <div className="flex-1">
                          <p className="text-sm text-text-primary">{alert.mensagem}</p>
                          <p className="text-xs text-text-muted mt-1">
                            {new Date(alert.createdAt).toLocaleDateString("pt-BR")}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </ScrollArea>
            <div className="p-3 border-t border-border">
              <Button variant="ghost" size="sm" className="w-full text-text-muted hover:text-text-primary">
                Ver todos os alertas
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </GlassCard>
        </BentoItem>
      </BentoGrid>
    </div>
  );
}
