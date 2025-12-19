"use client";

import { motion } from "framer-motion";
import { PenSquare, Construction, Users, Clock, Heart, MessageSquare } from "lucide-react";

/**
 * Blog Page - Internal Company Blog
 *
 * Placeholder page for the corporate blog.
 * This will feature company news, employee stories,
 * culture content, and internal announcements.
 */
export default function BlogPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-md"
      >
        {/* Icon */}
        <div className="relative mx-auto mb-6">
          <div className="w-24 h-24 rounded-2xl gradient-nexo flex items-center justify-center">
            <PenSquare className="w-12 h-12 text-white" />
          </div>
          <div className="absolute -bottom-2 -right-2 w-10 h-10 rounded-full bg-yellow-500/20 flex items-center justify-center">
            <Construction className="w-5 h-5 text-yellow-400" />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-bold text-text-primary mb-3">
          Blog Faiston
        </h1>

        {/* Description */}
        <p className="text-text-secondary mb-6">
          Histórias, novidades e cultura da nossa empresa.
          Fique por dentro de tudo que acontece na Faiston
          e conecte-se com seus colegas.
        </p>

        {/* Coming Soon Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-yellow-500/10 border border-yellow-500/30">
          <Construction className="w-4 h-4 text-yellow-400" />
          <span className="text-sm font-medium text-yellow-400">
            Em Desenvolvimento
          </span>
        </div>

        {/* Feature Preview */}
        <div className="mt-8 grid grid-cols-2 gap-3 text-left">
          <div className="p-3 rounded-lg bg-white/5 border border-border">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-blue-light" />
              <p className="text-sm font-medium text-text-primary">Histórias</p>
            </div>
            <p className="text-xs text-text-muted">Colaboradores</p>
          </div>
          <div className="p-3 rounded-lg bg-white/5 border border-border">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-magenta-light" />
              <p className="text-sm font-medium text-text-primary">Novidades</p>
            </div>
            <p className="text-xs text-text-muted">Últimas notícias</p>
          </div>
          <div className="p-3 rounded-lg bg-white/5 border border-border">
            <div className="flex items-center gap-2 mb-1">
              <Heart className="w-4 h-4 text-red-400" />
              <p className="text-sm font-medium text-text-primary">Cultura</p>
            </div>
            <p className="text-xs text-text-muted">Valores e missão</p>
          </div>
          <div className="p-3 rounded-lg bg-white/5 border border-border">
            <div className="flex items-center gap-2 mb-1">
              <MessageSquare className="w-4 h-4 text-green-400" />
              <p className="text-sm font-medium text-text-primary">Comentários</p>
            </div>
            <p className="text-xs text-text-muted">Interação</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
