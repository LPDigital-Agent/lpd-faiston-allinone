'use client';

// =============================================================================
// NovaOrdemModal - SGA Expedicao Module
// =============================================================================
// Apple TV-style frosted glass modal for creating new shipping orders.
// Multi-step flow: Form -> Quote Selection -> Order Creation
//
// Design: Frosted dark glass effect (backdrop-blur + rgba background)
// Pattern: Two-phase interaction (get quotes, then create order)
// =============================================================================

import { useState, useCallback } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Package,
  MapPin,
  Scale,
  Ruler,
  DollarSign,
  AlertCircle,
  Loader2,
  Truck,
  Clock,
  Star,
  Bot,
  ChevronRight,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { getShippingQuotes } from '@/services/sgaAgentcore';
import type {
  SGAGetQuotesRequest,
  SGAShippingQuote,
  SGACarrierRecommendation,
  SGAExpeditionUrgency,
} from '@/lib/ativos/types';

// =============================================================================
// Types
// =============================================================================

/**
 * Shipping order structure for the created order
 */
interface ShippingOrder {
  id: string;
  codigo: string;
  cliente: string;
  destino: { nome: string; cep: string };
  status: 'aguardando' | 'em_transito' | 'entregue';
  prioridade: string;
  responsavel: { nome: string };
  itens: Array<{
    ativoId: string;
    ativoCodigo: string;
    ativoNome: string;
    quantidade: number;
  }>;
  dataCriacao: string;
  dataPrevista: string;
  carrier: string;
  trackingCode?: string;
  price: number;
}

interface NovaOrdemModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal should close */
  onOpenChange: (open: boolean) => void;
  /** Callback when order is created */
  onOrderCreated: (order: ShippingOrder) => void;
}

type ModalStep = 'form' | 'quotes' | 'creating';

type UrgencyOption = {
  value: SGAExpeditionUrgency;
  label: string;
  description: string;
};

// =============================================================================
// Constants
// =============================================================================

const FAISTON_HQ_CEP = '04548005';

const URGENCY_OPTIONS: UrgencyOption[] = [
  { value: 'NORMAL', label: 'Normal', description: '3-5 dias uteis' },
  { value: 'HIGH', label: 'Alta', description: '1-2 dias uteis' },
  { value: 'URGENT', label: 'Urgente', description: 'Mesmo dia ou proximo' },
];

const DEFAULT_DIMENSIONS = { length: 30, width: 20, height: 10 };

// =============================================================================
// Form State Interface
// =============================================================================

interface FormState {
  destinoCep: string;
  peso: string;
  comprimento: string;
  largura: string;
  altura: string;
  valorDeclarado: string;
  urgencia: SGAExpeditionUrgency;
}

interface FormErrors {
  destinoCep?: string;
  peso?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatCEP(value: string): string {
  const digits = value.replace(/\D/g, '');
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5, 8)}`;
}

function parseCEP(value: string): string {
  return value.replace(/\D/g, '');
}

function formatCurrency(value: number): string {
  return value.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

function generateOrderCode(): string {
  const now = new Date();
  const year = now.getFullYear();
  const seq = String(Math.floor(Math.random() * 9999) + 1).padStart(4, '0');
  return `EXP-${year}-${seq}`;
}

function generateOrderId(): string {
  return `ord_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// =============================================================================
// Component
// =============================================================================

export function NovaOrdemModal({
  open,
  onOpenChange,
  onOrderCreated,
}: NovaOrdemModalProps) {
  // Form state
  const [formState, setFormState] = useState<FormState>({
    destinoCep: '',
    peso: '',
    comprimento: String(DEFAULT_DIMENSIONS.length),
    largura: String(DEFAULT_DIMENSIONS.width),
    altura: String(DEFAULT_DIMENSIONS.height),
    valorDeclarado: '',
    urgencia: 'NORMAL',
  });

  const [formErrors, setFormErrors] = useState<FormErrors>({});

  // Step and loading states
  const [step, setStep] = useState<ModalStep>('form');
  const [isLoadingQuotes, setIsLoadingQuotes] = useState(false);
  const [isCreatingOrder, setIsCreatingOrder] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Quotes state
  const [quotes, setQuotes] = useState<SGAShippingQuote[]>([]);
  const [recommendation, setRecommendation] = useState<SGACarrierRecommendation | null>(null);
  const [selectedQuote, setSelectedQuote] = useState<SGAShippingQuote | null>(null);

  // =============================================================================
  // Form Handlers
  // =============================================================================

  const updateFormField = useCallback(
    <K extends keyof FormState>(field: K, value: FormState[K]) => {
      setFormState((prev) => ({ ...prev, [field]: value }));
      // Clear error when field is updated
      if (field in formErrors) {
        setFormErrors((prev) => ({ ...prev, [field]: undefined }));
      }
    },
    [formErrors]
  );

  const validateForm = useCallback((): boolean => {
    const errors: FormErrors = {};
    const cep = parseCEP(formState.destinoCep);

    if (!cep || cep.length !== 8) {
      errors.destinoCep = 'CEP deve ter 8 digitos';
    }

    const peso = parseFloat(formState.peso);
    if (!formState.peso || isNaN(peso) || peso <= 0) {
      errors.peso = 'Peso deve ser maior que zero';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formState.destinoCep, formState.peso]);

  // =============================================================================
  // API Handlers
  // =============================================================================

  const handleGetQuotes = useCallback(async () => {
    if (!validateForm()) return;

    setIsLoadingQuotes(true);
    setApiError(null);

    try {
      const request: SGAGetQuotesRequest = {
        origin_cep: FAISTON_HQ_CEP,
        destination_cep: parseCEP(formState.destinoCep),
        weight_kg: parseFloat(formState.peso),
        dimensions: {
          length: parseFloat(formState.comprimento) || DEFAULT_DIMENSIONS.length,
          width: parseFloat(formState.largura) || DEFAULT_DIMENSIONS.width,
          height: parseFloat(formState.altura) || DEFAULT_DIMENSIONS.height,
        },
        value: formState.valorDeclarado ? parseFloat(formState.valorDeclarado) : 0,
        urgency: formState.urgencia,
      };

      const response = await getShippingQuotes(request);

      if (response.data.success && response.data.quotes.length > 0) {
        setQuotes(response.data.quotes);
        setRecommendation(response.data.recommendation);
        // Pre-select the recommended carrier if available
        const recommendedQuote = response.data.quotes.find(
          (q) =>
            q.carrier === response.data.recommendation?.carrier &&
            q.available
        );
        if (recommendedQuote) {
          setSelectedQuote(recommendedQuote);
        }
        setStep('quotes');
      } else {
        setApiError(
          response.data.error || 'Nenhuma cotacao disponivel para este destino'
        );
      }
    } catch (error) {
      console.error('[NovaOrdemModal] Failed to get quotes:', error);
      setApiError('Erro ao consultar cotacoes. Tente novamente.');
    } finally {
      setIsLoadingQuotes(false);
    }
  }, [formState, validateForm]);

  const handleCreateOrder = useCallback(async () => {
    if (!selectedQuote) return;

    setIsCreatingOrder(true);
    setStep('creating');

    try {
      // Simulate order creation delay
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const now = new Date();
      const deliveryDate = new Date();
      deliveryDate.setDate(deliveryDate.getDate() + selectedQuote.delivery_days);

      const newOrder: ShippingOrder = {
        id: generateOrderId(),
        codigo: generateOrderCode(),
        cliente: 'Cliente Faiston', // MVP: Could be expanded to include client selection
        destino: {
          nome: 'Destino',
          cep: parseCEP(formState.destinoCep),
        },
        status: 'aguardando',
        prioridade: formState.urgencia.toLowerCase(),
        responsavel: { nome: 'Usuario Atual' }, // MVP: Could integrate with auth
        itens: [], // MVP: Empty for now, could be expanded
        dataCriacao: now.toISOString(),
        dataPrevista: deliveryDate.toISOString(),
        carrier: selectedQuote.carrier,
        price: selectedQuote.price,
      };

      onOrderCreated(newOrder);
      handleClose();
    } catch (error) {
      console.error('[NovaOrdemModal] Failed to create order:', error);
      setApiError('Erro ao criar postagem. Tente novamente.');
      setStep('quotes');
    } finally {
      setIsCreatingOrder(false);
    }
  }, [selectedQuote, formState.destinoCep, formState.urgencia, onOrderCreated]);

  // =============================================================================
  // Modal Handlers
  // =============================================================================

  const handleClose = useCallback(() => {
    if (isLoadingQuotes || isCreatingOrder) return;

    // Reset all state
    setFormState({
      destinoCep: '',
      peso: '',
      comprimento: String(DEFAULT_DIMENSIONS.length),
      largura: String(DEFAULT_DIMENSIONS.width),
      altura: String(DEFAULT_DIMENSIONS.height),
      valorDeclarado: '',
      urgencia: 'NORMAL',
    });
    setFormErrors({});
    setStep('form');
    setQuotes([]);
    setRecommendation(null);
    setSelectedQuote(null);
    setApiError(null);
    onOpenChange(false);
  }, [isLoadingQuotes, isCreatingOrder, onOpenChange]);

  const handleBack = useCallback(() => {
    setStep('form');
    setSelectedQuote(null);
    setApiError(null);
  }, []);

  // =============================================================================
  // Render Helpers
  // =============================================================================

  const renderFormStep = () => (
    <div className="space-y-6">
      {/* CEP Destino */}
      <div className="space-y-2">
        <Label htmlFor="destinoCep" className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <MapPin className="w-4 h-4 text-[#00FAFB]" />
          CEP Destino <span className="text-[#FD5665]">*</span>
        </Label>
        <Input
          id="destinoCep"
          type="text"
          placeholder="00000-000"
          value={formatCEP(formState.destinoCep)}
          onChange={(e) => updateFormField('destinoCep', e.target.value)}
          maxLength={9}
          className={cn(
            'bg-white/5 border-white/10 text-white placeholder:text-gray-500',
            'focus:border-[#00FAFB] focus:ring-[#00FAFB]/20',
            formErrors.destinoCep && 'border-[#FD5665] focus:border-[#FD5665]'
          )}
          aria-invalid={!!formErrors.destinoCep}
        />
        {formErrors.destinoCep && (
          <p className="text-xs text-[#FD5665] flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {formErrors.destinoCep}
          </p>
        )}
      </div>

      {/* Peso */}
      <div className="space-y-2">
        <Label htmlFor="peso" className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Scale className="w-4 h-4 text-[#00FAFB]" />
          Peso (kg) <span className="text-[#FD5665]">*</span>
        </Label>
        <Input
          id="peso"
          type="number"
          step="0.1"
          min="0"
          placeholder="0.5"
          value={formState.peso}
          onChange={(e) => updateFormField('peso', e.target.value)}
          className={cn(
            'bg-white/5 border-white/10 text-white placeholder:text-gray-500',
            'focus:border-[#00FAFB] focus:ring-[#00FAFB]/20',
            formErrors.peso && 'border-[#FD5665] focus:border-[#FD5665]'
          )}
          aria-invalid={!!formErrors.peso}
        />
        {formErrors.peso && (
          <p className="text-xs text-[#FD5665] flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {formErrors.peso}
          </p>
        )}
      </div>

      {/* Dimensoes */}
      <div className="space-y-2">
        <Label className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Ruler className="w-4 h-4 text-[#00FAFB]" />
          Dimensoes (cm)
          <span className="text-xs text-gray-500 font-normal ml-1">opcional</span>
        </Label>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Input
              type="number"
              min="0"
              placeholder="Comp."
              value={formState.comprimento}
              onChange={(e) => updateFormField('comprimento', e.target.value)}
              className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-[#00FAFB]"
              aria-label="Comprimento"
            />
            <span className="text-xs text-gray-500 mt-1 block">Comprimento</span>
          </div>
          <div>
            <Input
              type="number"
              min="0"
              placeholder="Larg."
              value={formState.largura}
              onChange={(e) => updateFormField('largura', e.target.value)}
              className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-[#00FAFB]"
              aria-label="Largura"
            />
            <span className="text-xs text-gray-500 mt-1 block">Largura</span>
          </div>
          <div>
            <Input
              type="number"
              min="0"
              placeholder="Alt."
              value={formState.altura}
              onChange={(e) => updateFormField('altura', e.target.value)}
              className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-[#00FAFB]"
              aria-label="Altura"
            />
            <span className="text-xs text-gray-500 mt-1 block">Altura</span>
          </div>
        </div>
      </div>

      {/* Valor Declarado */}
      <div className="space-y-2">
        <Label htmlFor="valorDeclarado" className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-[#00FAFB]" />
          Valor Declarado (R$)
          <span className="text-xs text-gray-500 font-normal ml-1">opcional</span>
        </Label>
        <Input
          id="valorDeclarado"
          type="number"
          step="0.01"
          min="0"
          placeholder="0.00"
          value={formState.valorDeclarado}
          onChange={(e) => updateFormField('valorDeclarado', e.target.value)}
          className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-[#00FAFB]"
        />
      </div>

      {/* Urgencia */}
      <div className="space-y-2">
        <Label className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#00FAFB]" />
          Urgencia
        </Label>
        <div className="grid grid-cols-3 gap-2">
          {URGENCY_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updateFormField('urgencia', option.value)}
              className={cn(
                'p-3 rounded-xl border transition-all text-left',
                formState.urgencia === option.value
                  ? 'bg-[#00FAFB]/10 border-[#00FAFB]/50 text-white'
                  : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:bg-white/[0.04] hover:border-white/10'
              )}
            >
              <span className="text-sm font-medium block">{option.label}</span>
              <span className="text-xs text-gray-500 block mt-0.5">
                {option.description}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* API Error */}
      {apiError && (
        <div className="p-3 rounded-lg bg-[#FD5665]/10 border border-[#FD5665]/20 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-[#FD5665] mt-0.5 shrink-0" />
          <p className="text-sm text-[#FD5665]">{apiError}</p>
        </div>
      )}
    </div>
  );

  const renderQuotesStep = () => (
    <div className="space-y-4">
      {/* AI Recommendation Banner */}
      {recommendation && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-[#960A9C]/10 to-[#2226C0]/10 border border-white/[0.06]">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-[#A855F7]/20">
              <Bot className="w-5 h-5 text-[#A855F7]" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-white">Recomendacao NEXO</span>
                <Badge className="bg-[#A855F7]/20 text-[#A855F7] border-[#A855F7]/30 text-xs">
                  IA
                </Badge>
              </div>
              <p className="text-sm text-gray-400">{recommendation.reason}</p>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span>Confianca: {Math.round(recommendation.confidence * 100)}%</span>
                {recommendation.delivery_days && (
                  <span>Entrega: {recommendation.delivery_days} dia(s)</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quotes Grid */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2">
          <Truck className="w-4 h-4" />
          Cotacoes Disponiveis ({quotes.filter((q) => q.available).length})
        </h3>

        <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
          {quotes.map((quote, index) => {
            const isRecommended =
              recommendation?.carrier === quote.carrier &&
              recommendation?.modal === quote.modal;
            const isSelected =
              selectedQuote?.carrier === quote.carrier &&
              selectedQuote?.modal === quote.modal;

            return (
              <button
                key={`${quote.carrier}-${quote.modal}-${index}`}
                type="button"
                disabled={!quote.available}
                onClick={() => setSelectedQuote(quote)}
                className={cn(
                  'w-full p-4 rounded-xl border transition-all text-left relative',
                  quote.available
                    ? isSelected
                      ? 'bg-[#00FAFB]/10 border-[#00FAFB]/50'
                      : 'bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04] hover:border-white/10'
                    : 'bg-white/[0.01] border-white/[0.03] opacity-50 cursor-not-allowed'
                )}
              >
                {/* Recommended Badge */}
                {isRecommended && quote.available && (
                  <div className="absolute -top-2 right-3">
                    <Badge className="bg-[#A855F7] text-white text-xs gap-1">
                      <Star className="w-3 h-3" />
                      Recomendado
                    </Badge>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {/* Selection Indicator */}
                    <div
                      className={cn(
                        'w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors',
                        isSelected
                          ? 'border-[#00FAFB] bg-[#00FAFB]'
                          : 'border-white/20 bg-transparent'
                      )}
                    >
                      {isSelected && <CheckCircle2 className="w-3 h-3 text-[#151720]" />}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">
                          {quote.carrier}
                        </span>
                        <Badge
                          variant="outline"
                          className="text-xs text-gray-400 border-white/10"
                        >
                          {quote.modal}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {quote.delivery_days} dia(s)
                        </span>
                        {!quote.available && quote.reason && (
                          <span className="text-[#FD5665]">{quote.reason}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-lg font-semibold text-white">
                      {formatCurrency(quote.price)}
                    </span>
                    <p className="text-xs text-gray-500">
                      Entrega: {quote.delivery_date}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selection Info */}
      {selectedQuote && (
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center gap-3">
          <Info className="w-4 h-4 text-[#00FAFB] shrink-0" />
          <p className="text-sm text-gray-400">
            Selecionado: <span className="text-white font-medium">{selectedQuote.carrier}</span> -{' '}
            {formatCurrency(selectedQuote.price)} (entrega em {selectedQuote.delivery_days} dia(s))
          </p>
        </div>
      )}

      {/* API Error */}
      {apiError && (
        <div className="p-3 rounded-lg bg-[#FD5665]/10 border border-[#FD5665]/20 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-[#FD5665] mt-0.5 shrink-0" />
          <p className="text-sm text-[#FD5665]">{apiError}</p>
        </div>
      )}
    </div>
  );

  const renderCreatingStep = () => (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#00FAFB]/20 to-[#2226C0]/20 flex items-center justify-center">
          <Package className="w-8 h-8 text-[#00FAFB]" />
        </div>
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-[#00FAFB]/50"
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
      <p className="text-lg font-medium text-white mt-6">Criando postagem...</p>
      <p className="text-sm text-gray-400 mt-2">
        {selectedQuote?.carrier} - {formatCurrency(selectedQuote?.price || 0)}
      </p>
    </div>
  );

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <Dialog.Root open={open} onOpenChange={handleClose}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            {/* Overlay - Frosted Glass Effect */}
            <Dialog.Overlay asChild>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 z-50 bg-[#151720]/85 backdrop-blur-[24px]"
              />
            </Dialog.Overlay>

            {/* Modal Content */}
            <Dialog.Content asChild>
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className={cn(
                  'fixed left-1/2 top-1/2 z-50 w-full max-w-[560px] -translate-x-1/2 -translate-y-1/2',
                  'bg-[#1a1d28]/90 backdrop-blur-xl',
                  'border border-white/[0.06] rounded-2xl shadow-2xl',
                  'p-6 max-h-[90vh] overflow-y-auto'
                )}
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                  <Dialog.Title className="text-xl font-semibold text-white flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-gradient-to-br from-[#960A9C]/20 to-[#2226C0]/20 border border-white/[0.04]">
                      <Package className="w-5 h-5 text-[#00FAFB]" />
                    </div>
                    Nova Ordem de Expedicao
                  </Dialog.Title>
                  <Dialog.Close asChild>
                    <button
                      className="p-2 rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50"
                      disabled={isLoadingQuotes || isCreatingOrder}
                      aria-label="Fechar"
                    >
                      <X className="w-5 h-5 text-gray-400" />
                    </button>
                  </Dialog.Close>
                </div>

                {/* Step Indicator */}
                {step !== 'creating' && (
                  <div className="flex items-center gap-2 mb-6">
                    <div
                      className={cn(
                        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
                        step === 'form'
                          ? 'bg-[#00FAFB]/10 text-[#00FAFB]'
                          : 'text-gray-500'
                      )}
                    >
                      <span className="w-5 h-5 rounded-full bg-current/20 flex items-center justify-center text-xs font-medium">
                        1
                      </span>
                      Dados
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-600" />
                    <div
                      className={cn(
                        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
                        step === 'quotes'
                          ? 'bg-[#00FAFB]/10 text-[#00FAFB]'
                          : 'text-gray-500'
                      )}
                    >
                      <span className="w-5 h-5 rounded-full bg-current/20 flex items-center justify-center text-xs font-medium">
                        2
                      </span>
                      Cotacoes
                    </div>
                  </div>
                )}

                {/* Content */}
                {step === 'form' && renderFormStep()}
                {step === 'quotes' && renderQuotesStep()}
                {step === 'creating' && renderCreatingStep()}

                {/* Action Buttons */}
                {step !== 'creating' && (
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/[0.04]">
                    {step === 'quotes' ? (
                      <Button
                        variant="outline"
                        onClick={handleBack}
                        disabled={isCreatingOrder}
                        className="bg-transparent border-white/10 text-gray-400 hover:bg-white/5 hover:text-white"
                      >
                        Voltar
                      </Button>
                    ) : (
                      <div /> // Spacer
                    )}

                    <div className="flex items-center gap-3">
                      <Button
                        variant="outline"
                        onClick={handleClose}
                        disabled={isLoadingQuotes || isCreatingOrder}
                        className="bg-transparent border-white/10 text-gray-400 hover:bg-white/5 hover:text-white"
                      >
                        Cancelar
                      </Button>

                      {step === 'form' ? (
                        <Button
                          onClick={handleGetQuotes}
                          disabled={isLoadingQuotes}
                          className={cn(
                            'bg-gradient-to-r from-[#00FAFB] to-[#2226C0]',
                            'text-white font-medium',
                            'hover:opacity-90 transition-opacity',
                            'disabled:opacity-50'
                          )}
                        >
                          {isLoadingQuotes ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Consultando...
                            </>
                          ) : (
                            <>
                              Consultar Cotacoes
                              <ChevronRight className="w-4 h-4 ml-1" />
                            </>
                          )}
                        </Button>
                      ) : (
                        <Button
                          onClick={handleCreateOrder}
                          disabled={!selectedQuote || isCreatingOrder}
                          className={cn(
                            'bg-gradient-to-r from-[#00FAFB] to-[#2226C0]',
                            'text-white font-medium',
                            'hover:opacity-90 transition-opacity',
                            'disabled:opacity-50'
                          )}
                        >
                          {isCreatingOrder ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Criando...
                            </>
                          ) : (
                            <>
                              <Truck className="w-4 h-4 mr-2" />
                              Criar Postagem
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}

export default NovaOrdemModal;
