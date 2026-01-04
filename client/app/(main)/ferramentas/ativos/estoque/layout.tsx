'use client';

// =============================================================================
// Estoque Layout - SGA Inventory Module
// =============================================================================
// Provides context providers for the entire estoque section.
// =============================================================================

import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  AssetManagementProvider,
  TaskInboxProvider,
  NexoEstoqueProvider,
  InventoryOperationsProvider,
  InventoryCountProvider,
  OfflineSyncProvider,
} from '@/contexts/ativos';

// Create a client instance (singleton for the module)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      refetchOnWindowFocus: false,
    },
  },
});

interface EstoqueLayoutProps {
  children: ReactNode;
}

export default function EstoqueLayout({ children }: EstoqueLayoutProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AssetManagementProvider>
        <InventoryOperationsProvider>
          <TaskInboxProvider>
            <NexoEstoqueProvider>
              <InventoryCountProvider>
                <OfflineSyncProvider>
                  {children}
                </OfflineSyncProvider>
              </InventoryCountProvider>
            </NexoEstoqueProvider>
          </TaskInboxProvider>
        </InventoryOperationsProvider>
      </AssetManagementProvider>
    </QueryClientProvider>
  );
}
