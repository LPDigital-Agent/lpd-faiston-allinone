# =============================================================================
# Amazon Bedrock Knowledge Base for Equipment Documentation (S3 Vectors)
# =============================================================================
# Creates a RAG-enabled Knowledge Base for equipment specifications, manuals,
# and datasheets. Used by NEXO Assistant to answer equipment-related questions.
#
# Architecture (S3 Vectors - Fully Managed by Bedrock):
# - S3 Source: faiston-one-sga-equipment-docs-prod (equipment docs)
# - Vector Store: S3 Vectors (fully managed, no index creation needed)
# - Embedding Model: Amazon Titan Embeddings V2 (1024 dimensions)
# - Chunking: Fixed-size 512 tokens, 20% overlap
#
# Data Flow:
# EnrichmentAgent -> S3 -> Bedrock KB -> NEXO Assistant (RetrieveAndGenerate)
#
# Why S3 Vectors over OpenSearch Serverless:
# - Zero manual index creation (Bedrock manages everything)
# - 80% less Terraform code (~50 lines vs ~250 lines)
# - Lower cost (S3 pricing vs OpenSearch pricing)
# - No security policies needed
# - Sub-second latency is acceptable for equipment doc queries
#
# Reference:
# - PRD: product-development/current-feature/PRD-tavily-enrichment.md
# - S3 Bucket: terraform/main/s3_sga_equipment_docs.tf
# - IAM Roles: terraform/main/iam_bedrock_kb.tf
# - AWS Docs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-bedrock-kb.html
# =============================================================================

# =============================================================================
# S3 Vectors Bucket for Equipment Knowledge Base
# =============================================================================
# S3 Vectors is a fully managed vector store. Bedrock automatically creates
# and manages the vector index within this bucket.

resource "aws_s3vectors_vector_bucket" "equipment_kb" {
  vector_bucket_name = "${var.project_name}-equipment-kb-vectors"

  encryption_configuration {
    sse_type = "AES256"
  }

  tags = {
    Name        = "Faiston Equipment KB Vector Bucket"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment RAG"
    Purpose     = "S3 Vectors storage for equipment embeddings"
  }
}

# =============================================================================
# S3 Vectors Index for Equipment Embeddings
# =============================================================================
# The index stores vector embeddings created by Titan Embeddings V2.
# Bedrock automatically writes embeddings here during ingestion.

resource "aws_s3vectors_index" "equipment_kb" {
  index_name         = "equipment-knowledge-index"
  vector_bucket_name = aws_s3vectors_vector_bucket.equipment_kb.vector_bucket_name

  # Titan Embeddings V2 configuration
  data_type       = "float32"
  dimension       = 1024
  distance_metric = "cosine"

  tags = {
    Name        = "Faiston Equipment KB Vector Index"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment RAG"
    Purpose     = "Vector index for semantic search"
  }
}

# =============================================================================
# Bedrock Knowledge Base with S3 Vectors
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
    type = "S3_VECTORS"

    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.equipment_kb.index_arn
    }
  }

  tags = {
    Name        = "Faiston Equipment Knowledge Base"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
    Purpose     = "RAG for equipment documentation queries"
  }

  # Wait for S3 Vectors index to be ready
  depends_on = [
    aws_s3vectors_index.equipment_kb
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
      # Note: All S3 content in this bucket is equipment-related by design
      # No inclusion_prefixes needed (AWS API limits to 1 element max anyway)
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
    knowledge_base_id  = aws_bedrockagent_knowledge_base.equipment.id
    knowledge_base_arn = aws_bedrockagent_knowledge_base.equipment.arn
    data_source_id     = aws_bedrockagent_data_source.equipment_docs.data_source_id
    s3_bucket          = aws_s3_bucket.sga_equipment_docs.id
    vector_bucket      = aws_s3vectors_vector_bucket.equipment_kb.vector_bucket_name
    vector_index       = aws_s3vectors_index.equipment_kb.index_name
    embedding_model    = "amazon.titan-embed-text-v2:0"
    storage_type       = "S3_VECTORS"
    region             = var.aws_region
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

output "equipment_kb_vector_bucket" {
  description = "S3 Vectors bucket name"
  value       = aws_s3vectors_vector_bucket.equipment_kb.vector_bucket_name
}

output "equipment_kb_vector_index" {
  description = "S3 Vectors index name"
  value       = aws_s3vectors_index.equipment_kb.index_name
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
