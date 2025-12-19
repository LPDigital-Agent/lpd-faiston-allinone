"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/shared/glass-card";
import { GradientText } from "@/components/shared/gradient-text";
import { Button } from "@/components/ui/button";
import { Calendar, MessageSquare, Newspaper, ArrowRight } from "lucide-react";
import { getGreeting } from "@/lib/utils";
import { nexoConversation } from "@/mocks/mock-data";
import { useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";

// MANDATORY: All NEXO images must use the official avatar
const NEXO_AVATAR_PATH = "/Avatars/nexo-avatar.png";

/**
 * NEXOHero - Main AI assistant widget for the dashboard
 *
 * Displays:
 * - Personalized greeting
 * - Daily summary
 * - Quick suggestion chips
 */

export function NEXOHero() {
  const { user } = useAuth();
  const greeting = getGreeting();
  const firstName = user?.name ? user.name.split(" ")[0] : "Usuário";
  const summary = nexoConversation.messages[1];

  return (
    <GlassCard className="h-full p-6 flex flex-col" hoverGlow={false}>
      {/* Header with NEXO Avatar - MANDATORY: Use official avatar */}
      <div className="flex items-center gap-3 mb-4">
        <motion.div
          className="w-14 h-14 rounded-full overflow-hidden border-2 border-cyan-400/50"
          animate={{
            boxShadow: [
              "0 0 15px rgba(0, 250, 251, 0.3)",
              "0 0 25px rgba(0, 250, 251, 0.5)",
              "0 0 15px rgba(0, 250, 251, 0.3)",
            ],
          }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <Image
            src={NEXO_AVATAR_PATH}
            alt="NEXO Avatar"
            width={56}
            height={56}
            className="w-full h-full object-cover"
            priority
          />
        </motion.div>
        <div>
          <GradientText variant="nexo" size="lg" bold>
            NEXO
          </GradientText>
          <p className="text-xs text-text-muted">Seu assistente de IA</p>
        </div>
      </div>

      {/* Greeting */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mb-4"
      >
        <h2 className="text-h1 text-text-primary">
          {greeting}, <span className="gradient-text-action">{firstName}</span>! 👋
        </h2>
      </motion.div>

      {/* Daily Summary */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex-1 mb-4"
      >
        <p className="text-sm text-text-secondary mb-3">
          Aqui está seu resumo do dia:
        </p>
        <ul className="space-y-2">
          <SummaryItem
            icon={Calendar}
            text="3 reuniões agendadas"
            highlight="próxima: Daily em 15min"
            color="blue"
          />
          <SummaryItem
            icon={MessageSquare}
            text="5 mensagens não lidas"
            highlight="no Teams"
            color="magenta"
          />
          <SummaryItem
            icon={Newspaper}
            text="2 notícias importantes"
            highlight="sobre AWS e Google AI"
            color="blue"
          />
        </ul>
      </motion.div>

      {/* Quick Suggestions */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="flex flex-wrap gap-2"
      >
        {nexoConversation.suggestions.map((suggestion, index) => (
          <Button
            key={index}
            variant="outline"
            size="sm"
            className={cn(
              "bg-white/5 border-border hover:bg-white/10",
              "text-text-secondary hover:text-text-primary",
              "transition-all duration-150"
            )}
          >
            {suggestion}
            <ArrowRight className="w-3 h-3 ml-1" />
          </Button>
        ))}
      </motion.div>
    </GlassCard>
  );
}

interface SummaryItemProps {
  icon: React.ElementType;
  text: string;
  highlight: string;
  color: "blue" | "magenta";
}

function SummaryItem({ icon: Icon, text, highlight, color }: SummaryItemProps) {
  return (
    <li className="flex items-center gap-3 text-sm">
      <div
        className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center",
          color === "blue" ? "bg-blue-mid/20" : "bg-magenta-mid/20"
        )}
      >
        <Icon
          className={cn(
            "w-4 h-4",
            color === "blue" ? "text-blue-light" : "text-magenta-light"
          )}
        />
      </div>
      <span className="text-text-primary">
        {text}{" "}
        <span className="text-text-muted">({highlight})</span>
      </span>
    </li>
  );
}

export default NEXOHero;
