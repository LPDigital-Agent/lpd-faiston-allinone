# =============================================================================
# Amazon Bedrock Knowledge Base for Equipment Documentation
# =============================================================================
# Creates a RAG-enabled Knowledge Base for equipment specifications, manuals,
# and datasheets. Used by NEXO Assistant to answer equipment-related questions.
#
# Architecture:
# - S3 Source: faiston-one-sga-equipment-docs-prod (equipment docs)
# - Vector Store: OpenSearch Serverless (managed by AWS)
# - Embedding Model: Amazon Titan Embeddings V2 (1024 dimensions)
# - Chunking: Fixed-size 512 tokens, 20% overlap
#
# Data Flow:
# EnrichmentAgent -> S3 -> Bedrock KB -> NEXO Assistant (RetrieveAndGenerate)
#
# Reference:
# - PRD: product-development/current-feature/PRD-tavily-enrichment.md
# - S3 Bucket: terraform/main/s3_sga_equipment_docs.tf
# - IAM Roles: terraform/main/iam_bedrock_kb.tf
# =============================================================================

# =============================================================================
# OpenSearch Serverless Collection for Vector Store
# =============================================================================
# Bedrock KB uses OpenSearch Serverless as the vector database.
# Three security policies are required before the collection can be created.

# -----------------------------------------------------------------------------
# 1. Encryption Security Policy
# -----------------------------------------------------------------------------
resource "aws_opensearchserverless_security_policy" "kb_encryption" {
  name        = "${var.project_name}-kb-encryption"
  type        = "encryption"
  description = "Encryption policy for Bedrock KB vector store"

  policy = jsonencode({
    Rules = [
      {
        Resource     = ["collection/${var.project_name}-equipment-kb"]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# -----------------------------------------------------------------------------
# 2. Network Security Policy
# -----------------------------------------------------------------------------
# Allow access from Bedrock service
resource "aws_opensearchserverless_security_policy" "kb_network" {
  name        = "${var.project_name}-kb-network"
  type        = "network"
  description = "Network policy for Bedrock KB access"

  policy = jsonencode([
    {
      Description = "Allow Bedrock access to collection"
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${var.project_name}-equipment-kb"]
        },
        {
          ResourceType = "dashboard"
          Resource     = ["collection/${var.project_name}-equipment-kb"]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# -----------------------------------------------------------------------------
# 3. Data Access Policy
# -----------------------------------------------------------------------------
# Grant Bedrock KB role AND Bedrock service principal access to read/write vectors
# IMPORTANT: Bedrock service principal MUST be included for automatic index creation
resource "aws_opensearchserverless_access_policy" "kb_data_access" {
  name        = "${var.project_name}-kb-data-access"
  type        = "data"
  description = "Data access policy for Bedrock KB"

  policy = jsonencode([
    {
      Description = "Bedrock KB data access"
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${var.project_name}-equipment-kb"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource     = ["index/${var.project_name}-equipment-kb/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
      Principal = [
        aws_iam_role.bedrock_kb_equipment.arn,
        aws_iam_role.sga_agentcore_execution.arn
      ]
    },
    # Bedrock service principal for automatic index creation
    # This allows Bedrock to create the vector index during KB setup
    {
      Description = "Bedrock service access for index creation"
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${var.project_name}-equipment-kb"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DescribeCollectionItems",
            "aoss:UpdateCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource     = ["index/${var.project_name}-equipment-kb/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DescribeIndex",
            "aoss:UpdateIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
      Principal = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-service-role/bedrock.amazonaws.com/AWSServiceRoleForAmazonBedrock"
      ]
    }
  ])
}

# -----------------------------------------------------------------------------
# OpenSearch Serverless Collection
# -----------------------------------------------------------------------------
resource "aws_opensearchserverless_collection" "equipment_kb" {
  name        = "${var.project_name}-equipment-kb"
  description = "Vector store for NEXO equipment knowledge base"
  type        = "VECTORSEARCH"

  # Disable standby replicas to reduce costs (can enable for prod)
  standby_replicas = "DISABLED"

  tags = {
    Name        = "Faiston Equipment Knowledge Base Vector Store"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment RAG"
    Purpose     = "Vector embeddings for equipment documentation"
  }

  depends_on = [
    aws_opensearchserverless_security_policy.kb_encryption,
    aws_opensearchserverless_security_policy.kb_network,
    aws_opensearchserverless_access_policy.kb_data_access
  ]
}

# -----------------------------------------------------------------------------
# Wait for Collection to be ACTIVE
# -----------------------------------------------------------------------------
# OpenSearch Serverless collections take time to become ACTIVE after creation.
# This wait ensures the collection is ready before Bedrock KB tries to create the index.
resource "time_sleep" "wait_for_collection" {
  depends_on = [aws_opensearchserverless_collection.equipment_kb]

  # Wait 120 seconds for collection to reach ACTIVE state
  # This is necessary because the collection status check happens asynchronously
  create_duration = "120s"
}

# =============================================================================
# IAM Policy for OpenSearch Serverless Access
# =============================================================================
# Allow Bedrock KB role to access the OpenSearch Serverless collection

data "aws_iam_policy_document" "bedrock_kb_aoss_access" {
  statement {
    sid    = "AllowAOSSAPIAccess"
    effect = "Allow"
    actions = [
      "aoss:APIAccessAll"
    ]
    resources = [
      aws_opensearchserverless_collection.equipment_kb.arn
    ]
  }

  statement {
    sid    = "AllowAOSSBatchAccess"
    effect = "Allow"
    actions = [
      "aoss:BatchGetCollection",
      "aoss:CreateSecurityPolicy",
      "aoss:GetSecurityPolicy",
      "aoss:UpdateSecurityPolicy"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "bedrock_kb_aoss" {
  name   = "${var.project_name}-bedrock-kb-aoss-policy"
  role   = aws_iam_role.bedrock_kb_equipment.id
  policy = data.aws_iam_policy_document.bedrock_kb_aoss_access.json
}

# =============================================================================
# Bedrock Knowledge Base
# =============================================================================
resource "aws_bedrockagent_knowledge_base" "equipment" {
  name        = "${var.project_name}-equipment-kb"
  description = "Equipment specifications, manuals, and datasheets for NEXO Assistant"
  role_arn    = aws_iam_role.bedrock_kb_equipment.arn

  knowledge_base_configuration {
    type = "VECTOR"

    vector_knowledge_base_configuration {
      # Amazon Titan Embeddings V2 - 1024 dimensions
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"

      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 1024
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"

    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.equipment_kb.arn
      vector_index_name = "equipment-knowledge-index"

      field_mapping {
        vector_field   = "equipment_vector"
        text_field     = "equipment_text"
        metadata_field = "equipment_metadata"
      }
    }
  }

  tags = {
    Name        = "Faiston Equipment Knowledge Base"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
    Purpose     = "RAG for equipment documentation queries"
  }

  # Wait for collection to be ACTIVE and IAM policies to be in place
  depends_on = [
    time_sleep.wait_for_collection,
    aws_iam_role_policy.bedrock_kb_aoss
  ]
}

# =============================================================================
# Bedrock Data Source (S3)
# =============================================================================
# Connect the equipment docs S3 bucket as a data source
resource "aws_bedrockagent_data_source" "equipment_docs" {
  knowledge_base_id    = aws_bedrockagent_knowledge_base.equipment.id
  name                 = "${var.project_name}-equipment-docs-source"
  description          = "Equipment documentation from S3 bucket"
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "S3"

    s3_configuration {
      bucket_arn = aws_s3_bucket.sga_equipment_docs.arn
      # Note: inclusion_prefixes removed - AWS API limits to 1 element max
      # All S3 content in this bucket is equipment-related by design
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"

      fixed_size_chunking_configuration {
        # 512 tokens per chunk - optimal for technical specs
        max_tokens = 512
        # 20% overlap - ensures context continuity
        overlap_percentage = 20
      }
    }
  }
}

# =============================================================================
# SSM Parameters for KB Configuration
# =============================================================================
# Store KB configuration for reference by agents

resource "aws_ssm_parameter" "equipment_kb_config" {
  name        = "/${var.project_name}/sga/knowledge-base/config"
  description = "Bedrock Knowledge Base configuration for equipment docs"
  type        = "String"
  value = jsonencode({
    knowledge_base_id   = aws_bedrockagent_knowledge_base.equipment.id
    knowledge_base_arn  = aws_bedrockagent_knowledge_base.equipment.arn
    data_source_id      = aws_bedrockagent_data_source.equipment_docs.data_source_id
    s3_bucket           = aws_s3_bucket.sga_equipment_docs.id
    collection_endpoint = aws_opensearchserverless_collection.equipment_kb.collection_endpoint
    embedding_model     = "amazon.titan-embed-text-v2:0"
    region              = var.aws_region
  })

  tags = {
    Name        = "${var.project_name}-kb-config"
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Knowledge Base"
    Description = "KB configuration stored for agent reference"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "equipment_kb_id" {
  description = "ID of the Equipment Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.equipment.id
}

output "equipment_kb_arn" {
  description = "ARN of the Equipment Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.equipment.arn
}

output "equipment_kb_data_source_id" {
  description = "ID of the S3 data source"
  value       = aws_bedrockagent_data_source.equipment_docs.data_source_id
}

output "equipment_kb_collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = aws_opensearchserverless_collection.equipment_kb.collection_endpoint
}

output "equipment_kb_config_ssm" {
  description = "SSM parameter path for KB configuration"
  value       = aws_ssm_parameter.equipment_kb_config.name
}

# =============================================================================
# Post-Deployment: Sync Knowledge Base
# =============================================================================
# After Terraform apply and uploading documents to S3, trigger KB sync:
#
# aws bedrock-agent start-ingestion-job \
#   --knowledge-base-id $(terraform output -raw equipment_kb_id) \
#   --data-source-id $(terraform output -raw equipment_kb_data_source_id) \
#   --profile faiston-aio
#
# Monitor sync status:
# aws bedrock-agent list-ingestion-jobs \
#   --knowledge-base-id $(terraform output -raw equipment_kb_id) \
#   --data-source-id $(terraform output -raw equipment_kb_data_source_id) \
#   --profile faiston-aio
# =============================================================================
