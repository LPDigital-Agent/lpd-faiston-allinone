'use client';

// =============================================================================
// Estoque Page - SGA Inventory Module (Operations Hub)
// =============================================================================
// Operational hub for inventory management.
// Features: Task Inbox, Quick Actions, Recent Assets, Module Navigation
// Note: KPIs moved to Dashboard page for unified asset overview
// =============================================================================

import { useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import {
  Package,
  Search,
  Plus,
  FileUp,
  ArrowRightLeft,
  ClipboardCheck,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Inbox,
  Truck,
  RotateCcw,
  BarChart3,
  FileSearch,
} from 'lucide-react';
import { useAssets, useTaskInbox } from '@/hooks/ativos';
import {
  SGA_STATUS_LABELS,
  SGA_STATUS_COLORS,
  HIL_TASK_TYPE_LABELS,
  PRIORITY_LABELS,
  PRIORITY_COLORS,
} from '@/lib/ativos/constants';

// =============================================================================
// Dashboard Components
// =============================================================================

function TaskInboxSection() {
  const {
    tasks,
    tasksLoading: isLoading,
    refreshTasks,
  } = useTaskInbox();

  const pendingCount = tasks.filter(t => t.status === 'PENDING').length;

  const displayedTasks = tasks.slice(0, 5);

  return (
    <GlassCard>
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Inbox className="w-4 h-4 text-magenta-mid" />
            <GlassCardTitle>Tarefas Pendentes</GlassCardTitle>
            {pendingCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {pendingCount}
              </Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refreshTasks()}
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </GlassCardHeader>

      <GlassCardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-text-muted animate-spin" />
          </div>
        ) : displayedTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-green-400 mb-3" />
            <p className="text-sm text-text-muted">
              Nenhuma tarefa pendente
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {displayedTasks.map((task) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
              >
                <div className={`p-2 rounded-lg ${
                  task.priority === 'URGENT' ? 'bg-red-500/20' :
                  task.priority === 'HIGH' ? 'bg-orange-500/20' :
                  'bg-blue-mid/20'
                }`}>
                  {task.type === 'ADJUSTMENT_APPROVAL' ? (
                    <ClipboardCheck className="w-4 h-4 text-blue-light" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-yellow-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {HIL_TASK_TYPE_LABELS[task.type] || task.type}
                  </p>
                  <p className="text-xs text-text-muted truncate">
                    {task.description || 'Aguardando ação'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={PRIORITY_COLORS[task.priority] || 'bg-blue-500/20'}>
                    {PRIORITY_LABELS[task.priority] || task.priority}
                  </Badge>
                  <ArrowRight className="w-4 h-4 text-text-muted" />
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {tasks.length > 5 && (
          <div className="mt-4 text-center">
            <Button variant="outline" size="sm" asChild>
              <Link href="/ferramentas/ativos/estoque/tarefas">
                Ver todas as tarefas ({tasks.length})
              </Link>
            </Button>
          </div>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}

function QuickActions() {
  const actions = [
    {
      label: 'Nova Entrada',
      icon: FileUp,
      href: '/ferramentas/ativos/estoque/movimentacoes/entrada',
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
    },
    {
      label: 'Expedição',
      icon: Truck,
      href: '/ferramentas/ativos/estoque/expedicao',
      color: 'text-blue-light',
      bgColor: 'bg-blue-mid/20',
    },
    {
      label: 'Reversa',
      icon: RotateCcw,
      href: '/ferramentas/ativos/estoque/reversa',
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/20',
    },
    {
      label: 'Analytics',
      icon: BarChart3,
      href: '/ferramentas/ativos/estoque/analytics',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/20',
    },
    {
      label: 'Reconciliação SAP',
      icon: FileSearch,
      href: '/ferramentas/ativos/estoque/reconciliacao/sap',
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/20',
    },
  ];

  return (
    <GlassCard>
      <GlassCardHeader className="py-2">
        <div className="flex items-center gap-2">
          <Plus className="w-4 h-4 text-blue-light" />
          <GlassCardTitle className="text-sm">Ações Rápidas</GlassCardTitle>
        </div>
      </GlassCardHeader>

      <GlassCardContent className="py-2">
        <div className="grid grid-cols-3 lg:grid-cols-5 gap-2">
          {actions.map((action, index) => (
            <motion.div
              key={action.label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
            >
              <Link href={action.href}>
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-transparent hover:border-border transition-all cursor-pointer group">
                  <div className={`p-1.5 rounded-md ${action.bgColor} shrink-0`}>
                    <action.icon className={`w-4 h-4 ${action.color}`} />
                  </div>
                  <span className="text-xs font-medium text-text-primary group-hover:text-blue-light transition-colors truncate">
                    {action.label}
                  </span>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </GlassCardContent>
    </GlassCard>
  );
}

function RecentAssets() {
  const { assets, isLoading } = useAssets();
  const recentAssets = assets.slice(0, 5);

  return (
    <GlassCard>
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-blue-light" />
            <GlassCardTitle>Ativos Recentes</GlassCardTitle>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/ferramentas/ativos/estoque/lista">
              Ver todos
            </Link>
          </Button>
        </div>
      </GlassCardHeader>

      <GlassCardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-text-muted animate-spin" />
          </div>
        ) : recentAssets.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Package className="w-12 h-12 text-text-muted mb-3" />
            <p className="text-sm text-text-muted">
              Nenhum ativo cadastrado
            </p>
          </div>
        ) : (
          <ScrollArea className="max-h-[300px]">
            <div className="space-y-2">
              {recentAssets.map((asset) => (
                <Link
                  key={asset.id}
                  href={`/ferramentas/ativos/estoque/${asset.id}`}
                >
                  <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
                    <div className="w-10 h-10 rounded-lg bg-blue-mid/20 flex items-center justify-center shrink-0">
                      <Package className="w-5 h-5 text-blue-light" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {asset.serial_number || asset.id}
                      </p>
                      <p className="text-xs text-text-muted truncate">
                        {asset.part_number_id}
                      </p>
                    </div>
                    <Badge className={SGA_STATUS_COLORS[asset.status] || 'bg-gray-500/20'}>
                      {SGA_STATUS_LABELS[asset.status] || asset.status}
                    </Badge>
                  </div>
                </Link>
              ))}
            </div>
          </ScrollArea>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function EstoquePage() {
  const [searchTerm, setSearchTerm] = useState('');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">
            Estoque
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Central de operações do inventário
          </p>
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <Input
              placeholder="Buscar serial ou PN..."
              className="pl-10 w-64 bg-white/5 border-border"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Quick Actions - Full Width */}
      <QuickActions />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Task Inbox */}
        <div className="lg:col-span-2 space-y-6">
          <TaskInboxSection />
        </div>

        {/* Right Column - Recent Assets */}
        <div className="space-y-6">
          <RecentAssets />
        </div>
      </div>

      {/* Navigation Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link href="/ferramentas/ativos/estoque/cadastros">
          <GlassCard className="p-4 hover:border-blue-mid/50 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-mid/20">
                <Package className="w-5 h-5 text-blue-light" />
              </div>
              <div>
                <p className="text-sm font-medium text-text-primary">Cadastros</p>
                <p className="text-xs text-text-muted">PN, Locais, Projetos</p>
              </div>
            </div>
          </GlassCard>
        </Link>

        <Link href="/ferramentas/ativos/estoque/lista">
          <GlassCard className="p-4 hover:border-blue-mid/50 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <Search className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-text-primary">Lista de Ativos</p>
                <p className="text-xs text-text-muted">Consultar inventário</p>
              </div>
            </div>
          </GlassCard>
        </Link>

        <Link href="/ferramentas/ativos/estoque/movimentacoes">
          <GlassCard className="p-4 hover:border-blue-mid/50 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-magenta-dark/20">
                <ArrowRightLeft className="w-5 h-5 text-magenta-mid" />
              </div>
              <div>
                <p className="text-sm font-medium text-text-primary">Movimentações</p>
                <p className="text-xs text-text-muted">Entrada, Saída, Transferência</p>
              </div>
            </div>
          </GlassCard>
        </Link>

        <Link href="/ferramentas/ativos/estoque/inventario">
          <GlassCard className="p-4 hover:border-blue-mid/50 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-500/20">
                <ClipboardCheck className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-text-primary">Inventário</p>
                <p className="text-xs text-text-muted">Contagem e reconciliação</p>
              </div>
            </div>
          </GlassCard>
        </Link>
      </div>
    </div>
  );
}
