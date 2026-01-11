'use client';

/**
 * Agent Room Skeleton Components
 *
 * Loading placeholders for each Agent Room panel.
 * Uses consistent styling with the Apple TV frosted glass design.
 */

import { cn } from '@/lib/utils';

// =============================================================================
// Base Skeleton Component
// =============================================================================

interface SkeletonProps {
  className?: string;
}

function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-white/10',
        className
      )}
      aria-hidden="true"
    />
  );
}

// =============================================================================
// Live Feed Skeleton
// =============================================================================

export function LiveFeedSkeleton() {
  return (
    <div
      className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4"
      role="status"
      aria-label="Carregando feed ao vivo..."
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Skeleton className="w-4 h-4 rounded-full" />
          <Skeleton className="w-20 h-4" />
          <Skeleton className="w-16 h-3" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="w-16 h-7 rounded-md" />
          <Skeleton className="w-20 h-7 rounded-md" />
        </div>
      </div>

      {/* Messages */}
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex gap-3 p-3 rounded-lg bg-white/5">
            <Skeleton className="w-4 h-4 rounded-full shrink-0 mt-0.5" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Skeleton className="w-16 h-3" />
                <Skeleton className="w-8 h-3" />
              </div>
              <Skeleton className="w-full h-4" />
              <Skeleton className="w-2/3 h-4" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Carregando mensagens ao vivo</span>
    </div>
  );
}

// =============================================================================
// Agent Team Skeleton
// =============================================================================

export function AgentTeamSkeleton() {
  return (
    <div
      className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4"
      role="status"
      aria-label="Carregando equipe de agentes..."
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Skeleton className="w-4 h-4 rounded-full" />
        <Skeleton className="w-32 h-4" />
      </div>

      {/* Agent Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="flex flex-col items-center p-4 rounded-lg bg-white/5 border border-white/10"
          >
            <Skeleton className="w-14 h-14 rounded-full mb-3" />
            <Skeleton className="w-16 h-4 mb-1" />
            <Skeleton className="w-12 h-3" />
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flex justify-center mt-4">
        <Skeleton className="w-64 h-3" />
      </div>
      <span className="sr-only">Carregando equipe de agentes</span>
    </div>
  );
}

// =============================================================================
// Learning Stories Skeleton
// =============================================================================

export function LearningStoriesSkeleton() {
  return (
    <div
      className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4"
      role="status"
      aria-label="Carregando aprendizados..."
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Skeleton className="w-4 h-4 rounded-full" />
        <Skeleton className="w-36 h-4" />
      </div>

      {/* Stories */}
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="flex gap-3 p-3 rounded-lg bg-white/5 border border-white/10"
          >
            <Skeleton className="w-8 h-8 rounded-full shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <Skeleton className="w-20 h-3" />
                <Skeleton className="w-12 h-3" />
              </div>
              <Skeleton className="w-full h-4" />
              <Skeleton className="w-3/4 h-4" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Carregando aprendizados dos agentes</span>
    </div>
  );
}

// =============================================================================
// Workflow Timeline Skeleton
// =============================================================================

export function WorkflowTimelineSkeleton() {
  return (
    <div
      className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4"
      role="status"
      aria-label="Carregando fluxo de trabalho..."
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Skeleton className="w-4 h-4 rounded-full" />
        <Skeleton className="w-24 h-4" />
      </div>

      {/* Timeline Steps */}
      <div className="flex items-center justify-between px-4 py-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex flex-col items-center relative">
            <Skeleton className="w-10 h-10 rounded-full" />
            <Skeleton className="w-16 h-3 mt-2" />
            {i < 4 && (
              <Skeleton className="absolute top-5 left-full w-8 sm:w-12 h-0.5 -ml-1" />
            )}
          </div>
        ))}
      </div>
      <span className="sr-only">Carregando fluxo de trabalho atual</span>
    </div>
  );
}

// =============================================================================
// Pending Decisions Skeleton
// =============================================================================

export function PendingDecisionsSkeleton() {
  return (
    <div
      className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4"
      role="status"
      aria-label="Carregando decisoes pendentes..."
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Skeleton className="w-4 h-4 rounded-full" />
        <Skeleton className="w-28 h-4" />
        <Skeleton className="w-6 h-5 rounded-full" />
      </div>

      {/* Decision Cards */}
      <div className="space-y-3">
        {[...Array(2)].map((_, i) => (
          <div
            key={i}
            className="p-4 rounded-lg bg-white/5 border border-white/10"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <Skeleton className="w-4 h-4 rounded-full" />
                <Skeleton className="w-16 h-3" />
              </div>
              <Skeleton className="w-8 h-3" />
            </div>
            <Skeleton className="w-full h-4 mb-1" />
            <Skeleton className="w-2/3 h-4 mb-4" />
            <div className="flex gap-2">
              <Skeleton className="w-20 h-8 rounded-md" />
              <Skeleton className="w-16 h-8 rounded-md" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Carregando decisoes pendentes</span>
    </div>
  );
}

// =============================================================================
// X-Ray Skeleton
// =============================================================================

export function AgentXRaySkeleton() {
  return (
    <div
      className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4"
      role="status"
      aria-label="Carregando X-Ray..."
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Skeleton className="w-4 h-4 rounded-full" />
          <Skeleton className="w-16 h-4" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="w-16 h-6 rounded-full" />
          <Skeleton className="w-20 h-6 rounded-full" />
        </div>
      </div>

      {/* Session Groups */}
      <div className="space-y-3">
        {[...Array(2)].map((_, i) => (
          <div
            key={i}
            className="rounded-lg bg-white/5 border border-white/10 overflow-hidden"
          >
            {/* Session Header */}
            <div className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Skeleton className="w-4 h-4" />
                <Skeleton className="w-32 h-4" />
              </div>
              <div className="flex items-center gap-2">
                <Skeleton className="w-12 h-4" />
                <Skeleton className="w-16 h-5 rounded-full" />
              </div>
            </div>

            {/* Events */}
            <div className="border-t border-white/10 p-3 space-y-2">
              {[...Array(3)].map((_, j) => (
                <div key={j} className="flex items-center gap-2 p-2 rounded-lg bg-white/3">
                  <Skeleton className="w-6 h-6 rounded-full shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <Skeleton className="w-16 h-3" />
                      <Skeleton className="w-8 h-3" />
                    </div>
                    <Skeleton className="w-3/4 h-3" />
                  </div>
                  <Skeleton className="w-12 h-4 shrink-0" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Carregando traces X-Ray</span>
    </div>
  );
}

// =============================================================================
// Full Page Skeleton
// =============================================================================

export function AgentRoomPageSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Carregando Agent Room...">
      {/* Header Skeleton */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Skeleton className="w-5 h-5 rounded-full" />
            <Skeleton className="w-28 h-6" />
            <Skeleton className="w-16 h-5 rounded-full" />
          </div>
          <Skeleton className="w-64 h-4 mt-2" />
        </div>
      </div>

      {/* Live Feed */}
      <LiveFeedSkeleton />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <AgentTeamSkeleton />
          <WorkflowTimelineSkeleton />
        </div>
        <div className="space-y-6">
          <LearningStoriesSkeleton />
          <PendingDecisionsSkeleton />
        </div>
      </div>
      <span className="sr-only">Carregando painel de transparencia</span>
    </div>
  );
}
