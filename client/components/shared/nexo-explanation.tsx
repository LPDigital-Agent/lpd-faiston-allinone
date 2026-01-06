"use client";

import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ChevronDown, Lightbulb, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { useState, forwardRef } from "react";

/**
 * NexoExplanation - NEXO AI contextual explanation component
 *
 * Provides inline educational insights following the NEXO philosophy:
 * "Observant, Thoughtful, and Collaborative"
 *
 * Features:
 * - Summary always visible (1-2 sentences)
 * - Expandable details section ("Saiba mais")
 * - Optional action guidance
 * - Variant styling (info, tip, warning, success)
 * - Glassmorphism with Faiston brand gradients
 */

export interface NexoExplanationProps {
  /** Brief summary always visible (1-2 sentences) */
  summary: string;
  /** Expandable detailed explanation */
  details?: string;
  /** Action guidance or recommendation */
  action?: string;
  /** Visual variant */
  variant?: "info" | "tip" | "warning" | "success";
  /** Compact mode for inline use */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Default expanded state */
  defaultExpanded?: boolean;
}

const variantConfig = {
  info: {
    icon: Info,
    gradient: "from-faiston-blue-dark/20 to-faiston-blue-light/20",
    border: "border-faiston-blue-light/30",
    iconColor: "text-faiston-blue-light",
    label: "NEXO",
  },
  tip: {
    icon: Lightbulb,
    gradient: "from-faiston-magenta-dark/20 to-faiston-magenta-light/20",
    border: "border-faiston-magenta-light/30",
    iconColor: "text-faiston-magenta-light",
    label: "Dica NEXO",
  },
  warning: {
    icon: AlertTriangle,
    gradient: "from-amber-500/20 to-orange-500/20",
    border: "border-amber-400/30",
    iconColor: "text-amber-400",
    label: "Atenção",
  },
  success: {
    icon: CheckCircle,
    gradient: "from-emerald-500/20 to-teal-500/20",
    border: "border-emerald-400/30",
    iconColor: "text-emerald-400",
    label: "Pronto",
  },
};

export const NexoExplanation = forwardRef<HTMLDivElement, NexoExplanationProps>(
  (
    {
      summary,
      details,
      action,
      variant = "info",
      compact = false,
      className,
      defaultExpanded = false,
    },
    ref
  ) => {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);
    const config = variantConfig[variant];
    const IconComponent = config.icon;

    const hasExpandableContent = !!(details || action);

    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={cn(
          // Base glassmorphism
          "relative overflow-hidden rounded-lg",
          "bg-gradient-to-r",
          config.gradient,
          "backdrop-blur-sm",
          "border",
          config.border,
          // Padding based on compact mode
          compact ? "p-2.5" : "p-3",
          // Transition
          "transition-all duration-200",
          className
        )}
      >
        {/* Sparkle decoration (top-right corner) */}
        <div className="absolute top-1 right-1 pointer-events-none opacity-30">
          <Sparkles className="w-3 h-3 text-faiston-magenta-light" />
        </div>

        {/* Header with icon and summary */}
        <div
          className={cn(
            "flex items-start gap-2",
            hasExpandableContent && "cursor-pointer select-none"
          )}
          onClick={() => hasExpandableContent && setIsExpanded(!isExpanded)}
          onKeyDown={(e) => {
            if (hasExpandableContent && (e.key === "Enter" || e.key === " ")) {
              e.preventDefault();
              setIsExpanded(!isExpanded);
            }
          }}
          tabIndex={hasExpandableContent ? 0 : undefined}
          role={hasExpandableContent ? "button" : undefined}
          aria-expanded={hasExpandableContent ? isExpanded : undefined}
        >
          {/* Icon */}
          <div className={cn("flex-shrink-0 mt-0.5", config.iconColor)}>
            <IconComponent className={compact ? "w-3.5 h-3.5" : "w-4 h-4"} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Label and summary */}
            <div className={cn("text-text-secondary", compact ? "text-xs" : "text-sm")}>
              <span className={cn("font-medium", config.iconColor)}>
                {config.label}:
              </span>{" "}
              <span className="text-text-primary/90">{summary}</span>
            </div>
          </div>

          {/* Expand indicator */}
          {hasExpandableContent && (
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
              className="flex-shrink-0 mt-0.5"
            >
              <ChevronDown
                className={cn(
                  "text-text-muted",
                  compact ? "w-3.5 h-3.5" : "w-4 h-4"
                )}
              />
            </motion.div>
          )}
        </div>

        {/* Expandable content */}
        <AnimatePresence initial={false}>
          {isExpanded && hasExpandableContent && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className={cn("pt-2 mt-2 border-t border-white/5", compact ? "pl-5" : "pl-6")}>
                {/* Details */}
                {details && (
                  <p
                    className={cn(
                      "text-text-secondary whitespace-pre-line",
                      compact ? "text-xs" : "text-sm"
                    )}
                  >
                    {details}
                  </p>
                )}

                {/* Action */}
                {action && (
                  <div
                    className={cn(
                      "mt-2 flex items-center gap-1.5",
                      "text-faiston-magenta-light font-medium",
                      compact ? "text-xs" : "text-sm"
                    )}
                  >
                    <span aria-hidden>→</span>
                    <span>{action}</span>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }
);

NexoExplanation.displayName = "NexoExplanation";

export default NexoExplanation;
