"use client";

import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/shared/glass-card";
import { AssetManagementHeader } from "@/components/ferramentas/ativos/asset-management-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
  MessageSquare,
  Search,
  Plus,
  Mail,
  MailOpen,
  Star,
  Clock,
  Paperclip,
  Send,
  User,
  ChevronRight,
  Inbox,
  Archive,
  Trash2,
} from "lucide-react";
import {
  mockMessages,
  mockUsers,
} from "@/mocks/ativos-mock-data";
import { motion } from "framer-motion";

/**
 * Comunicação Page - Internal Messaging System
 *
 * Inbox-style view for internal asset-related communications.
 */

const categoryLabels: Record<string, { label: string; color: string }> = {
  geral: { label: "Geral", color: "bg-blue-500/20 text-blue-400" },
  solicitacao: { label: "Solicitação", color: "bg-magenta-mid/20 text-magenta-light" },
  aprovacao: { label: "Aprovação", color: "bg-green-500/20 text-green-400" },
  alerta: { label: "Alerta", color: "bg-yellow-500/20 text-yellow-400" },
};

const priorityColors: Record<string, string> = {
  baixa: "text-text-muted",
  normal: "text-text-secondary",
  alta: "text-yellow-400",
  urgente: "text-red-400",
};

export default function ComunicacaoPage() {
  const unreadCount = mockMessages.filter(m => !m.lida).length;
  const starredCount = mockMessages.filter(m => m.favorita).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <AssetManagementHeader
        title="Comunicação"
        subtitle="Mensagens e notificações internas"
        primaryAction={{
          label: "Nova Mensagem",
          onClick: () => console.log("Nova mensagem"),
          icon: <Plus className="w-4 h-4" />,
        }}
      />

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <GlassCard className="p-4">
            <div className="space-y-1">
              <Button
                variant="ghost"
                className="w-full justify-start text-text-primary bg-white/10"
              >
                <Inbox className="w-4 h-4 mr-2" />
                Caixa de Entrada
                {unreadCount > 0 && (
                  <Badge className="ml-auto bg-magenta-mid/30 text-magenta-light">
                    {unreadCount}
                  </Badge>
                )}
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start text-text-muted hover:text-text-primary"
              >
                <Star className="w-4 h-4 mr-2" />
                Favoritas
                {starredCount > 0 && (
                  <Badge variant="outline" className="ml-auto text-xs">
                    {starredCount}
                  </Badge>
                )}
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start text-text-muted hover:text-text-primary"
              >
                <Send className="w-4 h-4 mr-2" />
                Enviadas
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start text-text-muted hover:text-text-primary"
              >
                <Archive className="w-4 h-4 mr-2" />
                Arquivadas
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start text-text-muted hover:text-text-primary"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Lixeira
              </Button>
            </div>

            <div className="border-t border-border mt-4 pt-4">
              <p className="text-xs text-text-muted mb-2 px-2">Categorias</p>
              <div className="space-y-1">
                {Object.entries(categoryLabels).map(([key, config]) => (
                  <Button
                    key={key}
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start text-text-muted hover:text-text-primary"
                  >
                    <div className={`w-2 h-2 rounded-full mr-2 ${config.color.split(" ")[0]}`} />
                    {config.label}
                    <Badge variant="outline" className="ml-auto text-xs">
                      {mockMessages.filter(m => m.categoria === key).length}
                    </Badge>
                  </Button>
                ))}
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Message List */}
        <div className="lg:col-span-3">
          <GlassCard className="h-full">
            <GlassCardHeader>
              <div className="flex items-center justify-between w-full gap-4">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-blue-light" />
                  <GlassCardTitle>Caixa de Entrada</GlassCardTitle>
                </div>
                <div className="flex-1 max-w-md">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <Input
                      placeholder="Buscar mensagens..."
                      className="pl-10 bg-white/5 border-border h-9"
                    />
                  </div>
                </div>
              </div>
            </GlassCardHeader>

            <ScrollArea className="h-[500px]">
              <div className="divide-y divide-border">
                {mockMessages.map((message, index) => {
                  const category = categoryLabels[message.categoria];
                  const priorityColor = priorityColors[message.prioridade];
                  const remetente = mockUsers.find(u => u.id === message.remetenteId);

                  return (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className={`p-4 hover:bg-white/5 transition-colors cursor-pointer ${
                        !message.lida ? "bg-white/5" : ""
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Read/Unread Indicator */}
                        <div className="mt-1.5">
                          {message.lida ? (
                            <MailOpen className="w-4 h-4 text-text-muted" />
                          ) : (
                            <Mail className="w-4 h-4 text-blue-light" />
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <p className={`text-sm font-medium truncate ${
                                  !message.lida ? "text-text-primary" : "text-text-secondary"
                                }`}>
                                  {message.assunto}
                                </p>
                                {message.favorita && (
                                  <Star className="w-3 h-3 text-yellow-400 fill-yellow-400 shrink-0" />
                                )}
                              </div>
                              <p className="text-xs text-text-muted mt-0.5">
                                {remetente?.name || "Usuário desconhecido"}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <Badge className={category.color}>{category.label}</Badge>
                            </div>
                          </div>

                          {/* Preview */}
                          <p className="text-sm text-text-muted mt-2 line-clamp-2">
                            {message.conteudo}
                          </p>

                          {/* Footer */}
                          <div className="flex items-center justify-between mt-2 pt-2">
                            <div className="flex items-center gap-3 text-xs text-text-muted">
                              <div className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                <span>
                                  {new Date(message.dataEnvio).toLocaleDateString("pt-BR", {
                                    day: "2-digit",
                                    month: "short",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </span>
                              </div>
                              {message.anexos && message.anexos.length > 0 && (
                                <div className="flex items-center gap-1">
                                  <Paperclip className="w-3 h-3" />
                                  <span>{message.anexos.length}</span>
                                </div>
                              )}
                              {message.prioridade !== "normal" && (
                                <span className={priorityColor}>
                                  {message.prioridade.charAt(0).toUpperCase() + message.prioridade.slice(1)}
                                </span>
                              )}
                            </div>
                            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                              <ChevronRight className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </ScrollArea>

            {/* Footer */}
            <div className="p-4 border-t border-border">
              <p className="text-sm text-text-muted text-center">
                Mostrando {mockMessages.length} mensagens
              </p>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
