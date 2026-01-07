# SGA Equipment Documentation Knowledge Base Setup

This guide explains how to create the Bedrock Knowledge Base for equipment documentation after the infrastructure has been deployed via Terraform.

## Prerequisites

- Terraform has been applied successfully (S3 bucket and IAM roles created)
- You have access to AWS Console with Bedrock permissions

## Infrastructure Created by Terraform

| Resource | Name | Purpose |
|----------|------|---------|
| S3 Bucket | `faiston-one-sga-equipment-docs-prod` | Document storage for KB |
| IAM Role | `faiston-one-bedrock-kb-equipment-role` | KB execution role |
| IAM Policies | S3 access + Titan Embeddings invocation | KB permissions |

## Step 1: Access Bedrock Console

1. Go to [AWS Bedrock Console](https://us-east-2.console.aws.amazon.com/bedrock/home?region=us-east-2)
2. In the left menu, click **Knowledge bases**

## Step 2: Create Knowledge Base

1. Click **Create knowledge base**
2. Fill in the basic information:
   - **Name**: `faiston-sga-equipment-docs`
   - **Description**: `Equipment manuals, datasheets, and specifications for SGA inventory`
   - **IAM Role**: Select **Use an existing role** → `faiston-one-bedrock-kb-equipment-role`

## Step 3: Configure Data Source

1. **Data source name**: `s3-equipment-docs`
2. **S3 URI**: `s3://faiston-one-sga-equipment-docs-prod/`
3. **Chunking strategy**: Fixed-size chunking
   - **Max tokens**: 512
   - **Overlap percentage**: 20%
4. **Metadata file extension**: `.metadata.json`
5. Leave other settings as default

## Step 4: Select Embedding Model

1. **Embeddings model**: `Amazon Titan Text Embeddings v2`
   - Model ID: `amazon.titan-embed-text-v2:0`
   - Dimensions: 1024

## Step 5: Configure Vector Store

1. **Vector store**: Select **Quick create a new vector store**
   - Bedrock will automatically provision an OpenSearch Serverless collection
2. **Encryption**: Use AWS owned key (default)

## Step 6: Review and Create

1. Review all settings
2. Click **Create knowledge base**
3. Wait for creation to complete (2-5 minutes)

## Step 7: Copy Knowledge Base ID

After creation:
1. Click on the knowledge base name
2. Copy the **Knowledge base ID** (format: `XXXXXXXXXX`)
3. This ID is needed for the environment variable

## Step 8: Configure Environment Variable

Add the KB ID to AgentCore deployment:

```bash
# Add to SSM Parameter Store
aws ssm put-parameter \
  --name "/faiston-one/sga/equipment-kb-id" \
  --value "YOUR_KB_ID_HERE" \
  --type "String" \
  --overwrite

# Or set directly in AgentCore environment
EQUIPMENT_KB_ID=YOUR_KB_ID_HERE
```

## Step 9: Sync Data Source

1. In the KB details page, go to **Data source**
2. Select the S3 data source
3. Click **Sync**
4. Wait for sync to complete

The sync will process any documents already in the S3 bucket and make them searchable.

## Automatic Document Ingestion

Documents uploaded by the `EquipmentResearchAgent` follow this structure:

```
equipment-docs/{part_number}/{doc_type}/{filename}
equipment-docs/{part_number}/{doc_type}/{filename}.metadata.json
```

The `.metadata.json` sidecar files contain:
```json
{
  "part_number": "ABC-123",
  "document_type": "manual",
  "manufacturer": "Cisco",
  "description": "User manual for ABC-123 router",
  "source_url": "https://...",
  "upload_timestamp": "2026-01-07T..."
}
```

## Triggering KB Sync

After new documents are uploaded, sync the KB:

1. **Manual**: Click "Sync" in AWS Console
2. **Scheduled**: Set up EventBridge rule (optional)
3. **Automatic**: Enable S3 event notifications (coming soon)

## Testing the KB

Test via AWS Console:
1. Go to KB details
2. Click **Test knowledge base**
3. Enter a query like: `What is the installation procedure for part ABC-123?`

Test via NexoCopilot:
1. Open the Estoque module
2. Click the NEXO assistant
3. Ask: `Onde encontro o manual do ABC-123?`

## Troubleshooting

### KB returns no results
- Ensure documents are in S3 bucket
- Run a sync
- Check documents have valid content (not empty)

### Authorization errors
- Verify IAM role has correct policies
- Check S3 bucket policy allows Bedrock access

### Embedding errors
- Ensure Titan v2 model is enabled in Bedrock
- Check region (us-east-2)

## Architecture Reference

```
Import Equipment → EquipmentResearchAgent
                           ↓
               Gemini 3.0 + google_search
                           ↓
               Download PDFs/datasheets
                           ↓
               Upload to S3 + metadata.json
                           ↓
               Bedrock KB sync (manual/scheduled)
                           ↓
               Vector embeddings stored
                           ↓
User query → knowledge_base_retrieval_tool
                           ↓
               RAG answer + citations
                           ↓
               NexoCopilot displays results
```

---

Created: 2026-01-07
Module: SGA - Gestão de Estoque
Feature: Equipment Documentation Knowledge Base
