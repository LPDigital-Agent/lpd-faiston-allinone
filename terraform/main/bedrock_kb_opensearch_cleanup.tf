# =============================================================================
# Orphaned State Cleanup - OpenSearch Serverless Resources
# =============================================================================
# This file uses Terraform 1.7+ `removed` blocks to safely remove orphaned
# resources from state without attempting to destroy them.
#
# Background:
# - The Knowledge Base was migrated from OpenSearch Serverless to S3 Vectors
# - OpenSearch Serverless resources still exist in Terraform state
# - These `removed` blocks tell Terraform to forget about them without destroying
#
# Note: The actual AWS resources may need to be deleted manually via console
# or CLI if they exist. Run these after confirming the new S3 Vectors KB works:
#
# aws opensearchserverless delete-collection \
#   --id <collection-id> --profile faiston-aio
#
# Reference: https://developer.hashicorp.com/terraform/language/resources/syntax#removing-resources
# =============================================================================

# -----------------------------------------------------------------------------
# Remove OpenSearch Serverless Collection
# -----------------------------------------------------------------------------
removed {
  from = aws_opensearchserverless_collection.equipment_kb

  lifecycle {
    destroy = false
  }
}

# -----------------------------------------------------------------------------
# Remove OpenSearch Serverless Security Policies
# -----------------------------------------------------------------------------
removed {
  from = aws_opensearchserverless_security_policy.kb_encryption

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_opensearchserverless_security_policy.kb_network

  lifecycle {
    destroy = false
  }
}

# -----------------------------------------------------------------------------
# Remove OpenSearch Serverless Access Policy
# -----------------------------------------------------------------------------
removed {
  from = aws_opensearchserverless_access_policy.kb_data_access

  lifecycle {
    destroy = false
  }
}

# -----------------------------------------------------------------------------
# Remove time_sleep resource (was used to wait for AOSS collection)
# -----------------------------------------------------------------------------
removed {
  from = time_sleep.wait_for_collection

  lifecycle {
    destroy = false
  }
}

# -----------------------------------------------------------------------------
# Remove old AOSS IAM policy from bedrock_knowledge_base.tf
# -----------------------------------------------------------------------------
removed {
  from = aws_iam_role_policy.bedrock_kb_aoss

  lifecycle {
    destroy = false
  }
}
