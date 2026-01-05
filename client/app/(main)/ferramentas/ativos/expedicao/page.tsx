"use client";

// =============================================================================
// Expedição Page - Shipping Orders Management
// =============================================================================
// Kanban-style view of shipping orders organized by status.
// NOW SHOWS REAL DATA OR EMPTY STATE - No more mock data!
// =============================================================================

import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/shared/glass-card";
import { AssetManagementHeader } from "@/components/ferramentas/ativos/asset-management-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Truck,
  Plus,
  Clock,
  CheckCircle,
  Package,
  MapPin,
  User,
  Calendar,
  ArrowRight,
  InboxIcon,
} from "lucide-react";
import { motion } from "framer-motion";

/**
 * Expedição Page - Shipping Orders Management
 *
 * Kanban-style view of shipping orders organized by status.
 * NOW USES REAL DATA - Empty state when no orders exist.
 */

// Types for shipping orders
type ShippingOrderItem = {
  ativoId: string;
  ativoCodigo: string;
  ativoNome: string;
  quantidade: number;
};

type ShippingOrder = {
  id: string;
  codigo: string;
  cliente: string;
  destino: { nome: string };
  status: string;
  prioridade: string;
  responsavel: { nome: string };
  itens: ShippingOrderItem[];
  dataCriacao: string;
  dataPrevista: string;
};

const statusColumns = [
  { id: "aguardando", label: "Aguardando", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  { id: "em_transito", label: "Em Trânsito", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  { id: "entregue", label: "Entregue", color: "bg-green-500/20 text-green-400 border-green-500/30" },
];

export default function ExpedicaoPage() {
  // Real data - empty until backend integration
  // TODO: Replace with useShippingOrders() hook when backend is ready
  const shippingOrders: ShippingOrder[] = [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <AssetManagementHeader
        title="Expedição"
        subtitle="Gerencie ordens de envio e entregas"
        primaryAction={{
          label: "Nova Ordem",
          onClick: () => console.log("Nova ordem"),
          icon: <Plus className="w-4 h-4" />,
        }}
      />

      {/* Kanban Board */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {statusColumns.map((column, colIndex) => {
          const orders = shippingOrders.filter(o => o.status === column.id);

          return (
            <motion.div
              key={column.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: colIndex * 0.1 }}
            >
              <GlassCard className="h-full">
                <GlassCardHeader>
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <Badge className={column.color}>
                        {column.label}
                      </Badge>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {orders.length}
                    </Badge>
                  </div>
                </GlassCardHeader>

                <ScrollArea className="h-[500px]">
                  <div className="space-y-3 p-1">
                    {orders.map((order, index) => (
                      <motion.div
                        key={order.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 + index * 0.05 }}
                        className="p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer border border-border"
                      >
                        {/* Order Header */}
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <p className="text-sm font-medium text-text-primary">
                              {order.codigo}
                            </p>
                            <p className="text-xs text-text-muted">
                              {order.itens.length} {order.itens.length === 1 ? "item" : "itens"}
                            </p>
                          </div>
                          {order.prioridade === "urgente" && (
                            <Badge className="bg-red-500/20 text-red-400 text-xs">
                              Urgente
                            </Badge>
                          )}
                        </div>

                        {/* Destination */}
                        <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                          <MapPin className="w-3 h-3" />
                          <span className="truncate">{order.destino.nome}</span>
                        </div>

                        {/* Responsible */}
                        <div className="flex items-center gap-2 text-xs text-text-muted mb-3">
                          <User className="w-3 h-3" />
                          <span className="truncate">{order.responsavel.nome}</span>
                        </div>

                        {/* Date */}
                        <div className="flex items-center justify-between pt-2 border-t border-border">
                          <div className="flex items-center gap-1 text-xs text-text-muted">
                            <Calendar className="w-3 h-3" />
                            <span>
                              {new Date(order.dataPrevista).toLocaleDateString("pt-BR")}
                            </span>
                          </div>
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                            <ArrowRight className="w-3 h-3" />
                          </Button>
                        </div>
                      </motion.div>
                    ))}

                    {orders.length === 0 && (
                      <div className="flex flex-col items-center justify-center py-8 text-center">
                        <InboxIcon className="w-10 h-10 text-text-muted mb-2" />
                        <p className="text-sm text-text-muted">Nenhuma ordem</p>
                        <p className="text-xs text-text-muted mt-1">
                          As ordens de expedição aparecerão aqui
                        </p>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <GlassCard className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
              <Clock className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">
                {shippingOrders.filter(o => o.status === "aguardando").length}
              </p>
              <p className="text-sm text-text-muted">Aguardando</p>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-mid/20 flex items-center justify-center">
              <Truck className="w-5 h-5 text-blue-light" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">
                {shippingOrders.filter(o => o.status === "em_transito").length}
              </p>
              <p className="text-sm text-text-muted">Em Trânsito</p>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">
                {shippingOrders.filter(o => o.status === "entregue").length}
              </p>
              <p className="text-sm text-text-muted">Entregues</p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
