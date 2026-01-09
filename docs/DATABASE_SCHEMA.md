# Database Schema Documentation - Faiston NEXO

Complete database architecture for the Faiston NEXO platform, covering Aurora PostgreSQL and DynamoDB.

## Table of Contents

1. [Overview](#1-overview)
2. [Aurora PostgreSQL Schema](#2-aurora-postgresql-schema)
3. [DynamoDB Tables](#3-dynamodb-tables)
4. [Single-Table Design](#4-single-table-design)
5. [Access Patterns](#5-access-patterns)
6. [Data Migration](#6-data-migration)

---

## 1. Overview

### Database Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Faiston NEXO Data Layer                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────┐  ┌──────────────────────────┐    │
│  │  Aurora PostgreSQL       │  │  DynamoDB                │    │
│  │  (Relational Data)       │  │  (Event Sourcing)        │    │
│  ├──────────────────────────┤  ├──────────────────────────┤    │
│  │  • Part Numbers          │  │  • Inventory Events      │    │
│  │  • Assets                │  │  • HIL Tasks             │    │
│  │  • Locations             │  │  • Audit Logs            │    │
│  │  • Movements             │  │  • Sessions              │    │
│  │  • Balances              │  │  • Academy Trainings     │    │
│  │  • Reservations          │  │                          │    │
│  └──────────────────────────┘  └──────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Store Responsibilities

| Data Store | Purpose | Use Cases |
|------------|---------|-----------|
| **Aurora PostgreSQL** | ACID transactions, complex queries | Inventory master data, movements, reconciliation |
| **DynamoDB** | Event sourcing, high-throughput | Audit logs, sessions, real-time events |

### Connection Details

| Resource | Value |
|----------|-------|
| **Aurora Cluster** | `faiston-one-sga-postgres-prod` |
| **Database Name** | `sga_inventory` |
| **Port** | 5432 |
| **RDS Proxy** | `faiston-one-sga-proxy-prod` |
| **Engine** | Aurora PostgreSQL Serverless v2 (15.x) |

---

## 2. Aurora PostgreSQL Schema

### Entity Relationship Diagram

```
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  part_numbers │       │    assets     │       │   locations   │
├───────────────┤       ├───────────────┤       ├───────────────┤
│ PK pn_id      │◄──────│ FK pn_id      │       │ PK location_id│
│    pn_code    │       │ PK asset_id   │──────►│    name       │
│    description│       │    serial_no  │       │    type       │
│    uom        │       │ FK location_id│       │    parent_id  │
│    category   │       │    status     │       │    address    │
└───────────────┘       │    condition  │       └───────────────┘
                        └───────┬───────┘
                                │
                                │
                        ┌───────▼───────┐
                        │   movements   │
                        ├───────────────┤
                        │ PK movement_id│
                        │ FK asset_id   │
                        │    type       │
                        │    quantity   │
                        │ FK from_loc   │
                        │ FK to_loc     │
                        │    timestamp  │
                        └───────────────┘
```

### Table: `part_numbers`

Master catalog of all part numbers (inventory items).

```sql
CREATE TABLE part_numbers (
    pn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pn_code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    uom VARCHAR(20) NOT NULL DEFAULT 'UN',
    category VARCHAR(50),
    subcategory VARCHAR(50),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    minimum_stock INTEGER DEFAULT 0,
    maximum_stock INTEGER,
    reorder_point INTEGER,
    lead_time_days INTEGER,
    cost_center VARCHAR(50),
    is_serialized BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

CREATE INDEX idx_pn_code ON part_numbers(pn_code);
CREATE INDEX idx_pn_category ON part_numbers(category);
CREATE INDEX idx_pn_active ON part_numbers(is_active);
```

### Table: `assets`

Individual serialized items with lifecycle tracking.

```sql
CREATE TYPE asset_status AS ENUM (
    'available',
    'in_use',
    'maintenance',
    'reserved',
    'scrapped',
    'lost',
    'returned'
);

CREATE TYPE asset_condition AS ENUM (
    'new',
    'good',
    'fair',
    'poor',
    'damaged',
    'refurbished'
);

CREATE TABLE assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pn_id UUID NOT NULL REFERENCES part_numbers(pn_id),
    serial_number VARCHAR(100) UNIQUE,
    batch_number VARCHAR(100),
    location_id UUID REFERENCES locations(location_id),
    status asset_status NOT NULL DEFAULT 'available',
    condition asset_condition NOT NULL DEFAULT 'new',
    acquisition_date DATE,
    acquisition_cost DECIMAL(15,2),
    warranty_expiry DATE,
    last_maintenance DATE,
    next_maintenance DATE,
    assigned_to VARCHAR(100),
    project_id VARCHAR(50),
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

CREATE INDEX idx_asset_pn ON assets(pn_id);
CREATE INDEX idx_asset_serial ON assets(serial_number);
CREATE INDEX idx_asset_location ON assets(location_id);
CREATE INDEX idx_asset_status ON assets(status);
CREATE INDEX idx_asset_project ON assets(project_id);
```

### Table: `locations`

Hierarchical location structure.

```sql
CREATE TYPE location_type AS ENUM (
    'warehouse',
    'shelf',
    'bin',
    'project_site',
    'vehicle',
    'external',
    'transit'
);

CREATE TABLE locations (
    location_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE,
    type location_type NOT NULL,
    parent_id UUID REFERENCES locations(location_id),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50) DEFAULT 'Brazil',
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    capacity INTEGER,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_location_parent ON locations(parent_id);
CREATE INDEX idx_location_type ON locations(type);
CREATE INDEX idx_location_code ON locations(code);
```

### Table: `movements`

Immutable movement history (event sourcing pattern).

```sql
CREATE TYPE movement_type AS ENUM (
    'entrada',        -- Inbound (purchase, return)
    'saida',          -- Outbound (consumption, shipment)
    'transferencia',  -- Transfer between locations
    'ajuste',         -- Inventory adjustment
    'reserva',        -- Reservation
    'liberacao',      -- Reservation release
    'devolucao'       -- Return
);

CREATE TABLE movements (
    movement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(asset_id),
    pn_id UUID NOT NULL REFERENCES part_numbers(pn_id),
    type movement_type NOT NULL,
    quantity INTEGER NOT NULL,
    from_location_id UUID REFERENCES locations(location_id),
    to_location_id UUID REFERENCES locations(location_id),
    document_ref VARCHAR(100),
    document_type VARCHAR(50),
    project_id VARCHAR(50),
    cost_center VARCHAR(50),
    unit_cost DECIMAL(15,2),
    total_cost DECIMAL(15,2),
    reason TEXT,
    approved_by VARCHAR(100),
    approval_date TIMESTAMPTZ,
    confidence_score DECIMAL(3,2),
    hil_task_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE INDEX idx_movement_asset ON movements(asset_id);
CREATE INDEX idx_movement_pn ON movements(pn_id);
CREATE INDEX idx_movement_type ON movements(type);
CREATE INDEX idx_movement_date ON movements(created_at);
CREATE INDEX idx_movement_project ON movements(project_id);
CREATE INDEX idx_movement_document ON movements(document_ref);
```

### Table: `balances`

Materialized view of current stock levels (denormalized for performance).

```sql
CREATE TABLE balances (
    balance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pn_id UUID NOT NULL REFERENCES part_numbers(pn_id),
    location_id UUID NOT NULL REFERENCES locations(location_id),
    quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    available_quantity INTEGER GENERATED ALWAYS AS (quantity - reserved_quantity) STORED,
    last_movement_id UUID REFERENCES movements(movement_id),
    last_updated TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(pn_id, location_id)
);

CREATE INDEX idx_balance_pn ON balances(pn_id);
CREATE INDEX idx_balance_location ON balances(location_id);
CREATE INDEX idx_balance_available ON balances(available_quantity);
```

### Table: `reservations`

Temporary stock reservations with TTL.

```sql
CREATE TYPE reservation_status AS ENUM (
    'active',
    'fulfilled',
    'cancelled',
    'expired'
);

CREATE TABLE reservations (
    reservation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pn_id UUID NOT NULL REFERENCES part_numbers(pn_id),
    location_id UUID NOT NULL REFERENCES locations(location_id),
    quantity INTEGER NOT NULL,
    status reservation_status NOT NULL DEFAULT 'active',
    project_id VARCHAR(50),
    requested_by VARCHAR(100) NOT NULL,
    reason TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    fulfilled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    movement_id UUID REFERENCES movements(movement_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reservation_pn ON reservations(pn_id);
CREATE INDEX idx_reservation_status ON reservations(status);
CREATE INDEX idx_reservation_expires ON reservations(expires_at);
```

### Triggers

```sql
-- Auto-update balances on movement insert
CREATE OR REPLACE FUNCTION update_balance_on_movement()
RETURNS TRIGGER AS $$
BEGIN
    -- Handle outbound (subtract from source)
    IF NEW.from_location_id IS NOT NULL THEN
        UPDATE balances
        SET quantity = quantity - NEW.quantity,
            last_movement_id = NEW.movement_id,
            last_updated = NOW()
        WHERE pn_id = NEW.pn_id AND location_id = NEW.from_location_id;
    END IF;

    -- Handle inbound (add to destination)
    IF NEW.to_location_id IS NOT NULL THEN
        INSERT INTO balances (pn_id, location_id, quantity, last_movement_id)
        VALUES (NEW.pn_id, NEW.to_location_id, NEW.quantity, NEW.movement_id)
        ON CONFLICT (pn_id, location_id)
        DO UPDATE SET
            quantity = balances.quantity + NEW.quantity,
            last_movement_id = NEW.movement_id,
            last_updated = NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_movement_balance
AFTER INSERT ON movements
FOR EACH ROW
EXECUTE FUNCTION update_balance_on_movement();

-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_part_numbers_timestamp
BEFORE UPDATE ON part_numbers
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_assets_timestamp
BEFORE UPDATE ON assets
FOR EACH ROW EXECUTE FUNCTION update_timestamp();
```

---

## 3. DynamoDB Tables

### Table: `faiston-one-sga-inventory-prod`

Event sourcing table for inventory events.

| Attribute | Type | Description |
|-----------|------|-------------|
| `PK` | String | Partition key (entity prefix + ID) |
| `SK` | String | Sort key (event type + timestamp) |
| `entity_type` | String | Type: `MOVEMENT`, `BALANCE`, `ASSET` |
| `data` | Map | Event payload |
| `created_at` | String | ISO timestamp |
| `TTL` | Number | Expiration timestamp (optional) |

**Key Design:**
```
PK: ASSET#<asset_id>
SK: EVENT#<timestamp>#<event_type>

PK: PN#<pn_code>
SK: BALANCE#<location_id>

PK: LOC#<location_id>
SK: ASSET#<asset_id>
```

### Table: `faiston-one-sga-hil-tasks-prod`

Human-in-the-Loop approval tasks.

| Attribute | Type | Description |
|-----------|------|-------------|
| `task_id` | String | Primary key (UUID) |
| `type` | String | Task type: `approval`, `review`, `classification` |
| `status` | String | `pending`, `approved`, `rejected`, `escalated` |
| `payload` | Map | Task data |
| `confidence_score` | Number | AI confidence (0.0-1.0) |
| `assigned_to` | String | Approver email |
| `created_at` | String | ISO timestamp |
| `updated_at` | String | ISO timestamp |
| `TTL` | Number | Auto-expire after 30 days |

**GSI:** `status-created_at-index`
- PK: `status`
- SK: `created_at`

### Table: `faiston-one-sga-audit-log-prod`

Immutable audit trail.

| Attribute | Type | Description |
|-----------|------|-------------|
| `PK` | String | Entity type + ID |
| `SK` | String | Timestamp + action |
| `action` | String | `create`, `update`, `delete`, `approve` |
| `actor` | String | User email or agent name |
| `changes` | Map | Before/after values |
| `ip_address` | String | Client IP |
| `user_agent` | String | Browser/agent info |
| `created_at` | String | ISO timestamp |

### Table: `faiston-one-sga-sessions-prod`

AgentCore session management.

| Attribute | Type | Description |
|-----------|------|-------------|
| `session_id` | String | Primary key |
| `user_id` | String | Cognito user sub |
| `agent_name` | String | Active agent |
| `memory` | Map | Session memory |
| `created_at` | String | ISO timestamp |
| `expires_at` | String | Session expiry |
| `TTL` | Number | Auto-cleanup |

### Table: `faiston-one-academy-trainings-prod`

Custom training content.

| Attribute | Type | Description |
|-----------|------|-------------|
| `training_id` | String | Primary key (UUID) |
| `title` | String | Training title |
| `description` | String | Description |
| `type` | String | `course`, `lesson`, `quiz` |
| `content_url` | String | S3 URL |
| `duration_minutes` | Number | Duration |
| `created_by` | String | Creator email |
| `created_at` | String | ISO timestamp |
| `status` | String | `draft`, `published`, `archived` |

---

## 4. Single-Table Design

### Entity Prefixes

| Prefix | Entity | Example |
|--------|--------|---------|
| `PN#` | Part Number | `PN#ABC123` |
| `ASSET#` | Asset | `ASSET#uuid-here` |
| `LOC#` | Location | `LOC#warehouse-1` |
| `BALANCE#` | Balance | `BALANCE#PN#ABC123#LOC#wh1` |
| `MOVE#` | Movement | `MOVE#uuid-here` |
| `RESERVE#` | Reservation | `RESERVE#uuid-here` |
| `TASK#` | HIL Task | `TASK#uuid-here` |
| `DIV#` | Divergence | `DIV#uuid-here` |
| `DOC#` | Document | `DOC#nf-123456` |

### Access Pattern Examples

```python
# Get all assets for a part number
response = table.query(
    KeyConditionExpression=Key('PK').eq(f'PN#{pn_code}') & Key('SK').begins_with('ASSET#')
)

# Get asset timeline (all events)
response = table.query(
    KeyConditionExpression=Key('PK').eq(f'ASSET#{asset_id}') & Key('SK').begins_with('EVENT#')
)

# Get pending HIL tasks
response = table.query(
    IndexName='status-created_at-index',
    KeyConditionExpression=Key('status').eq('pending')
)

# Get balance for location
response = table.query(
    KeyConditionExpression=Key('PK').eq(f'LOC#{location_id}') & Key('SK').begins_with('BALANCE#')
)
```

---

## 5. Access Patterns

### PostgreSQL Queries

```sql
-- Get inventory by location with balances
SELECT
    pn.pn_code,
    pn.description,
    l.name as location,
    b.quantity,
    b.reserved_quantity,
    b.available_quantity
FROM balances b
JOIN part_numbers pn ON b.pn_id = pn.pn_id
JOIN locations l ON b.location_id = l.location_id
WHERE l.location_id = $1
ORDER BY pn.pn_code;

-- Get asset movement history
SELECT
    m.movement_id,
    m.type,
    m.quantity,
    fl.name as from_location,
    tl.name as to_location,
    m.document_ref,
    m.created_at,
    m.created_by
FROM movements m
LEFT JOIN locations fl ON m.from_location_id = fl.location_id
LEFT JOIN locations tl ON m.to_location_id = tl.location_id
WHERE m.asset_id = $1
ORDER BY m.created_at DESC;

-- Low stock report
SELECT
    pn.pn_code,
    pn.description,
    COALESCE(SUM(b.available_quantity), 0) as total_available,
    pn.minimum_stock,
    pn.reorder_point
FROM part_numbers pn
LEFT JOIN balances b ON pn.pn_id = b.pn_id
WHERE pn.is_active = true
GROUP BY pn.pn_id
HAVING COALESCE(SUM(b.available_quantity), 0) < pn.reorder_point
ORDER BY (COALESCE(SUM(b.available_quantity), 0) - pn.reorder_point);
```

### Lambda MCP Tools

The PostgreSQL database is accessed through Lambda-based MCP tools:

| Tool | Function | Query Pattern |
|------|----------|---------------|
| `sga_list_inventory` | List assets with filters | Paginated SELECT with JOINs |
| `sga_get_balance` | Get stock for PN | SUM by part number |
| `sga_search_assets` | Search by serial/description | ILIKE with text search |
| `sga_get_asset_timeline` | Full asset history | ORDER BY timestamp DESC |
| `sga_get_movements` | Movement history | Filter by date/type |
| `sga_create_movement` | Create new movement | INSERT with trigger |
| `sga_get_schema_metadata` | Schema introspection | information_schema queries |

---

## 6. Data Migration

### Schema Migration Files

Location: `server/agentcore-inventory/schema/`

```
schema/
├── 001_initial_schema.sql
├── 002_add_reservations.sql
├── 003_add_audit_columns.sql
├── 004_add_hil_support.sql
└── migrations.json
```

### Migration Lambda

The `faiston-one-sga-schema-migrator-prod` Lambda runs migrations:

```python
# server/agentcore-inventory/lambda_schema_migrator.py
def handler(event, context):
    """
    Run pending database migrations.
    Triggered by:
    - Manual invocation
    - Deployment workflow
    """
    migrations = load_pending_migrations()
    for migration in migrations:
        execute_migration(migration)
        record_migration(migration)
    return {"applied": len(migrations)}
```

### Backup Strategy

| Backup Type | Frequency | Retention |
|-------------|-----------|-----------|
| Aurora PITR | Continuous | 7 days |
| Aurora Snapshots | Daily | 30 days |
| DynamoDB PITR | Continuous | 35 days |
| DynamoDB On-Demand Backup | Weekly | 90 days |

---

## Related Documentation

- [Infrastructure](INFRASTRUCTURE.md)
- [AgentCore Implementation Guide](AgentCore/IMPLEMENTATION_GUIDE.md)
- [SGA Architecture](architecture/SGA_ESTOQUE_ARCHITECTURE.md)

---

**Last Updated:** January 2026
**Platform:** Faiston NEXO
