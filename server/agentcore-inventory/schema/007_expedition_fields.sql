-- =============================================================================
-- Migration: 007_expedition_fields.sql
-- =============================================================================
-- Add expedition-specific fields to pending_entry_items table
-- to support Smart Import of expedition CSV files (SOLICITAÇÕES DE EXPEDIÇÃO)
--
-- New Columns:
--   - request_date: DATA SOLICITAÇÃO (DATE)
--   - expedition_date: DATA EXPEDIÇÃO (DATE)
--   - tflux_ticket: N° TICKET (VARCHAR)
--   - responsible_person: RESPONSABILIDADE (VARCHAR)
--   - replacement_info: REPOSIÇÃO (VARCHAR)
--   - stock_validated: VALIDADO NO ESTOQUE (VARCHAR)
--
-- Author: Claude Code
-- Date: 2026-01-12
-- =============================================================================

-- Set search path
SET search_path TO sga, public;

-- =============================================================================
-- Add New Columns to pending_entry_items
-- =============================================================================

-- Add expedition fields (all nullable to maintain backwards compatibility)
ALTER TABLE sga.pending_entry_items
ADD COLUMN IF NOT EXISTS request_date DATE,
ADD COLUMN IF NOT EXISTS expedition_date DATE,
ADD COLUMN IF NOT EXISTS tflux_ticket VARCHAR(50),
ADD COLUMN IF NOT EXISTS responsible_person VARCHAR(100),
ADD COLUMN IF NOT EXISTS replacement_info VARCHAR(255),
ADD COLUMN IF NOT EXISTS stock_validated VARCHAR(50);

-- =============================================================================
-- Add Column Comments for Documentation
-- =============================================================================

COMMENT ON COLUMN sga.pending_entry_items.request_date
    IS 'Request date from expedition CSV (DATA SOLICITAÇÃO)';

COMMENT ON COLUMN sga.pending_entry_items.expedition_date
    IS 'Expedition/shipment date from expedition CSV (DATA EXPEDIÇÃO)';

COMMENT ON COLUMN sga.pending_entry_items.tflux_ticket
    IS 'TFLUX support ticket number (N° TICKET)';

COMMENT ON COLUMN sga.pending_entry_items.responsible_person
    IS 'Person responsible for the expedition (RESPONSABILIDADE)';

COMMENT ON COLUMN sga.pending_entry_items.replacement_info
    IS 'Replacement information if applicable (REPOSIÇÃO)';

COMMENT ON COLUMN sga.pending_entry_items.stock_validated
    IS 'Stock validation status: VALIDADO or empty (VALIDADO NO ESTOQUE)';

-- =============================================================================
-- Add Indexes for Query Optimization
-- =============================================================================

-- Index on TFLUX ticket for lookup queries
CREATE INDEX IF NOT EXISTS idx_pending_entry_items_tflux
    ON sga.pending_entry_items(tflux_ticket);

-- Index on request_date for date-range queries
CREATE INDEX IF NOT EXISTS idx_pending_entry_items_request_date
    ON sga.pending_entry_items(request_date);

-- Index on responsible_person for filtering by responsible
CREATE INDEX IF NOT EXISTS idx_pending_entry_items_responsible
    ON sga.pending_entry_items(responsible_person);

-- =============================================================================
-- End of migration
-- =============================================================================
