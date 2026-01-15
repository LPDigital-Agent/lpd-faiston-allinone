"use client";

// =============================================================================
// Expedição Page - Shipping Orders Management
// =============================================================================
// Kanban-style view of shipping orders organized by status.
// Includes Nova Ordem modal for creating shipping orders with carrier quotes.
// Uses localStorage for MVP state persistence (DB integration planned).
// =============================================================================

import { useState, useEffect, useCallback } from "react";
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
  ChevronRight,
  MoreVertical,
  Play,
  Check,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { NovaOrdemModal } from "@/components/ferramentas/ativos/modals/NovaOrdemModal";
import { toast } from "@/components/ui/use-toast";

/**
 * Expedição Page - Shipping Orders Management
 *
 * Kanban-style view with status columns: Aguardando → Em Trânsito → Entregue
 * Includes Nova Ordem modal for creating orders with Correios/TRB quotes.
 */

// Types for shipping orders
export type ShippingOrderStatus = "aguardando" | "em_transito" | "entregue";

export type ShippingOrderItem = {
  ativoId: string;
  ativoCodigo: string;
  ativoNome: string;
  quantidade: number;
};

export type ShippingOrder = {
  id: string;
  codigo: string;
  cliente: string;
  destino: { nome: string; cep?: string };
  status: ShippingOrderStatus;
  prioridade: string;
  responsavel: { nome: string };
  itens: ShippingOrderItem[];
  dataCriacao: string;
  dataPrevista: string;
  carrier?: string;
  trackingCode?: string;
  price?: number;
};

const statusColumns = [
  { id: "aguardando" as const, label: "Aguardando", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", icon: Clock },
  { id: "em_transito" as const, label: "Em Trânsito", color: "bg-blue-500/20 text-blue-400 border-blue-500/30", icon: Truck },
  { id: "entregue" as const, label: "Entregue", color: "bg-green-500/20 text-green-400 border-green-500/30", icon: CheckCircle },
];

// LocalStorage key for MVP persistence
const STORAGE_KEY = "faiston_expedition_orders";

export default function ExpedicaoPage() {
  // State for shipping orders (localStorage-backed for MVP)
  const [shippingOrders, setShippingOrders] = useState<ShippingOrder[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load orders from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const orders = JSON.parse(stored);
        setShippingOrders(orders);
      }
    } catch (e) {
      console.error("Failed to load orders from localStorage:", e);
    }
    setIsLoaded(true);
  }, []);

  // Save orders to localStorage when changed
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(shippingOrders));
      } catch (e) {
        console.error("Failed to save orders to localStorage:", e);
      }
    }
  }, [shippingOrders, isLoaded]);

  // Handle new order created from modal
  const handleOrderCreated = useCallback((order: ShippingOrder) => {
    setShippingOrders((prev) => [...prev, order]);
    toast({
      title: "Postagem criada com sucesso!",
      description: `Código: ${order.codigo}`,
    });
  }, []);

  // Move order to next status
  const moveToNextStatus = useCallback((orderId: string) => {
    setShippingOrders((prev) =>
      prev.map((order) => {
        if (order.id !== orderId) return order;

        const nextStatus: Record<ShippingOrderStatus, ShippingOrderStatus> = {
          aguardando: "em_transito",
          em_transito: "entregue",
          entregue: "entregue",
        };

        const newStatus = nextStatus[order.status];

        if (newStatus !== order.status) {
          toast({
            title: `Status atualizado para "${newStatus === 'em_transito' ? 'Em Trânsito' : 'Entregue'}"`,
            description: `Pedido: ${order.codigo}`,
          });
        }

        return {
          ...order,
          status: newStatus,
        };
      })
    );
  }, []);

  // Delete order
  const deleteOrder = useCallback((orderId: string) => {
    setShippingOrders((prev) => prev.filter((o) => o.id !== orderId));
    toast({ title: "Ordem removida" });
  }, []);

  // Clear all orders (for testing)
  const clearAllOrders = useCallback(() => {
    setShippingOrders([]);
    toast({ title: "Todas as ordens foram removidas" });
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <AssetManagementHeader
        title="Expedição"
        subtitle="Gerencie ordens de envio e entregas"
        primaryAction={{
          label: "Nova Ordem",
          onClick: () => setIsModalOpen(true),
          icon: <Plus className="w-4 h-4" />,
        }}
        secondaryActions={
          shippingOrders.length > 0
            ? [
                {
                  label: "Limpar Tudo",
                  onClick: clearAllOrders,
                },
              ]
            : undefined
        }
      />

      {/* Nova Ordem Modal */}
      <NovaOrdemModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        onOrderCreated={handleOrderCreated}
      />

      {/* Kanban Board */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {statusColumns.map((column, colIndex) => {
          const orders = shippingOrders.filter((o) => o.status === column.id);
          const StatusIcon = column.icon;

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
                        <StatusIcon className="w-3 h-3 mr-1" />
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
                    <AnimatePresence mode="popLayout">
                      {orders.map((order, index) => (
                        <motion.div
                          key={order.id}
                          layout
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          transition={{ delay: index * 0.05 }}
                          className="p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors border border-border group"
                        >
                          {/* Order Header */}
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <p className="text-sm font-medium text-text-primary">
                                {order.codigo}
                              </p>
                              <p className="text-xs text-text-muted">
                                {order.carrier || "Correios"} • R$ {order.price?.toFixed(2) || "0.00"}
                              </p>
                            </div>
                            <div className="flex items-center gap-1">
                              {order.prioridade === "URGENT" && (
                                <Badge className="bg-red-500/20 text-red-400 text-xs">
                                  Urgente
                                </Badge>
                              )}
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                                  >
                                    <MoreVertical className="w-3 h-3" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  {order.status !== "entregue" && (
                                    <DropdownMenuItem onClick={() => moveToNextStatus(order.id)}>
                                      {order.status === "aguardando" ? (
                                        <>
                                          <Play className="w-3 h-3 mr-2" />
                                          Mover para Em Trânsito
                                        </>
                                      ) : (
                                        <>
                                          <Check className="w-3 h-3 mr-2" />
                                          Marcar como Entregue
                                        </>
                                      )}
                                    </DropdownMenuItem>
                                  )}
                                  <DropdownMenuItem
                                    onClick={() => deleteOrder(order.id)}
                                    className="text-red-400"
                                  >
                                    Remover
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </div>

                          {/* Destination */}
                          <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                            <MapPin className="w-3 h-3" />
                            <span className="truncate">{order.destino.nome}</span>
                          </div>

                          {/* Tracking Code (if exists) */}
                          {order.trackingCode && (
                            <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                              <Package className="w-3 h-3" />
                              <span className="font-mono">{order.trackingCode}</span>
                            </div>
                          )}

                          {/* Responsible */}
                          <div className="flex items-center gap-2 text-xs text-text-muted mb-3">
                            <User className="w-3 h-3" />
                            <span className="truncate">{order.responsavel.nome}</span>
                          </div>

                          {/* Footer with date and action */}
                          <div className="flex items-center justify-between pt-2 border-t border-border">
                            <div className="flex items-center gap-1 text-xs text-text-muted">
                              <Calendar className="w-3 h-3" />
                              <span>
                                {new Date(order.dataPrevista).toLocaleDateString("pt-BR")}
                              </span>
                            </div>
                            {order.status !== "entregue" && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 px-2 text-xs"
                                onClick={() => moveToNextStatus(order.id)}
                              >
                                {order.status === "aguardando" ? "Enviar" : "Entregar"}
                                <ChevronRight className="w-3 h-3 ml-1" />
                              </Button>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>

                    {orders.length === 0 && (
                      <div className="flex flex-col items-center justify-center py-8 text-center">
                        <InboxIcon className="w-10 h-10 text-text-muted mb-2" />
                        <p className="text-sm text-text-muted">Nenhuma ordem</p>
                        <p className="text-xs text-text-muted mt-1">
                          {column.id === "aguardando"
                            ? 'Clique em "Nova Ordem" para criar'
                            : "As ordens aparecerão aqui"}
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
                {shippingOrders.filter((o) => o.status === "aguardando").length}
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
                {shippingOrders.filter((o) => o.status === "em_transito").length}
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
                {shippingOrders.filter((o) => o.status === "entregue").length}
              </p>
              <p className="text-sm text-text-muted">Entregues</p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
