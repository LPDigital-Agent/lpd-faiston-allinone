"use client";

import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/shared/glass-card";
import { AssetManagementHeader } from "@/components/ferramentas/ativos/asset-management-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
  MapPin,
  Search,
  Truck,
  Navigation,
  Clock,
  Package,
  RefreshCcw,
  Maximize2,
  Signal,
  Battery,
} from "lucide-react";
import {
  mockShippingOrders,
  mockAssets,
  mockLocations,
} from "@/mocks/ativos-mock-data";
import { motion } from "framer-motion";

/**
 * Tracking Page - Real-time Asset and Vehicle Tracking
 *
 * Displays map view with active shipments and vehicle locations.
 */

// Mock tracking data for vehicles
const mockVehicles = [
  {
    id: "v-001",
    placa: "ABC-1234",
    motorista: "Carlos Silva",
    status: "em_rota",
    ultimaAtualizacao: new Date().toISOString(),
    bateria: 85,
    sinal: "forte",
    destino: "Filial São Paulo",
    etaMinutos: 45,
  },
  {
    id: "v-002",
    placa: "DEF-5678",
    motorista: "João Santos",
    status: "parado",
    ultimaAtualizacao: new Date(Date.now() - 15 * 60000).toISOString(),
    bateria: 72,
    sinal: "medio",
    destino: "Cliente XYZ",
    etaMinutos: 120,
  },
  {
    id: "v-003",
    placa: "GHI-9012",
    motorista: "Pedro Oliveira",
    status: "em_rota",
    ultimaAtualizacao: new Date(Date.now() - 5 * 60000).toISOString(),
    bateria: 95,
    sinal: "forte",
    destino: "Centro de Distribuição",
    etaMinutos: 20,
  },
];

const statusLabels: Record<string, { label: string; color: string }> = {
  em_rota: { label: "Em Rota", color: "bg-green-500/20 text-green-400" },
  parado: { label: "Parado", color: "bg-yellow-500/20 text-yellow-400" },
  offline: { label: "Offline", color: "bg-red-500/20 text-red-400" },
};

const signalLabels: Record<string, { label: string; color: string }> = {
  forte: { label: "Forte", color: "text-green-400" },
  medio: { label: "Médio", color: "text-yellow-400" },
  fraco: { label: "Fraco", color: "text-red-400" },
};

export default function TrackingPage() {
  const activeShipments = mockShippingOrders.filter(o => o.status === "em_transito");

  return (
    <div className="space-y-6">
      {/* Header */}
      <AssetManagementHeader
        title="Tracking e Logística"
        subtitle="Rastreamento em tempo real de veículos e entregas"
        secondaryActions={[
          {
            label: "Atualizar",
            onClick: () => console.log("Atualizar"),
            icon: <RefreshCcw className="w-4 h-4" />,
          },
        ]}
      />

      {/* Map Placeholder + Vehicle List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Area */}
        <div className="lg:col-span-2">
          <GlassCard className="h-[500px] relative overflow-hidden">
            <GlassCardHeader>
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-blue-light" />
                  <GlassCardTitle>Mapa de Rastreamento</GlassCardTitle>
                </div>
                <Button variant="ghost" size="sm">
                  <Maximize2 className="w-4 h-4" />
                </Button>
              </div>
            </GlassCardHeader>

            {/* Map Placeholder */}
            <div className="absolute inset-0 mt-14 flex items-center justify-center bg-gradient-to-br from-blue-dark/20 to-magenta-dark/20">
              <div className="text-center">
                <MapPin className="w-16 h-16 mx-auto mb-4 text-text-muted opacity-50" />
                <p className="text-text-muted">Integração com mapa em desenvolvimento</p>
                <p className="text-sm text-text-muted mt-1">Google Maps / Mapbox</p>
              </div>

              {/* Mock Vehicle Markers */}
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 }}
                className="absolute top-1/3 left-1/4 w-10 h-10 rounded-full bg-green-500/30 border-2 border-green-400 flex items-center justify-center"
              >
                <Truck className="w-5 h-5 text-green-400" />
              </motion.div>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.4 }}
                className="absolute top-1/2 right-1/3 w-10 h-10 rounded-full bg-yellow-500/30 border-2 border-yellow-400 flex items-center justify-center"
              >
                <Truck className="w-5 h-5 text-yellow-400" />
              </motion.div>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.5 }}
                className="absolute bottom-1/3 right-1/4 w-10 h-10 rounded-full bg-green-500/30 border-2 border-green-400 flex items-center justify-center"
              >
                <Truck className="w-5 h-5 text-green-400" />
              </motion.div>
            </div>
          </GlassCard>
        </div>

        {/* Vehicle List */}
        <div className="lg:col-span-1">
          <GlassCard className="h-[500px] flex flex-col">
            <GlassCardHeader>
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Truck className="w-4 h-4 text-magenta-light" />
                  <GlassCardTitle>Veículos</GlassCardTitle>
                </div>
                <Badge variant="outline" className="text-xs">
                  {mockVehicles.length} ativos
                </Badge>
              </div>
            </GlassCardHeader>

            {/* Search */}
            <div className="px-4 pb-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <Input
                  placeholder="Buscar veículo..."
                  className="pl-10 bg-white/5 border-border h-9 text-sm"
                />
              </div>
            </div>

            <ScrollArea className="flex-1">
              <div className="space-y-2 px-4 pb-4">
                {mockVehicles.map((vehicle, index) => {
                  const status = statusLabels[vehicle.status];
                  const sinal = signalLabels[vehicle.sinal];

                  return (
                    <motion.div
                      key={vehicle.id}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer border border-border"
                    >
                      {/* Header */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${status.color.replace("text-", "bg-").replace("400", "500/20")}`}>
                            <Truck className={`w-4 h-4 ${status.color.split(" ")[1]}`} />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-text-primary">{vehicle.placa}</p>
                            <p className="text-xs text-text-muted">{vehicle.motorista}</p>
                          </div>
                        </div>
                        <Badge className={status.color}>{status.label}</Badge>
                      </div>

                      {/* Destination */}
                      <div className="flex items-center gap-1 text-xs text-text-muted mb-2">
                        <Navigation className="w-3 h-3" />
                        <span className="truncate">{vehicle.destino}</span>
                      </div>

                      {/* Stats */}
                      <div className="flex items-center justify-between text-xs text-text-muted pt-2 border-t border-border">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-1">
                            <Battery className="w-3 h-3" />
                            <span>{vehicle.bateria}%</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Signal className={`w-3 h-3 ${sinal.color}`} />
                            <span className={sinal.color}>{sinal.label}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>{vehicle.etaMinutos} min</span>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </ScrollArea>
          </GlassCard>
        </div>
      </div>

      {/* Active Shipments */}
      <GlassCard>
        <GlassCardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <Package className="w-4 h-4 text-blue-light" />
              <GlassCardTitle>Entregas em Andamento</GlassCardTitle>
            </div>
            <Badge variant="outline">{activeShipments.length} entregas</Badge>
          </div>
        </GlassCardHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
          {activeShipments.map((shipment, index) => (
            <motion.div
              key={shipment.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="p-4 rounded-lg bg-white/5 border border-border"
            >
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-medium text-text-primary">{shipment.codigo}</p>
                <Badge className="bg-blue-500/20 text-blue-400">Em Trânsito</Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                <MapPin className="w-3 h-3" />
                <span className="truncate">{shipment.destino.nome}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Clock className="w-3 h-3" />
                <span>Previsão: {new Date(shipment.dataPrevista).toLocaleDateString("pt-BR")}</span>
              </div>
            </motion.div>
          ))}

          {activeShipments.length === 0 && (
            <div className="col-span-full text-center py-8 text-text-muted">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Nenhuma entrega em andamento</p>
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );
}
