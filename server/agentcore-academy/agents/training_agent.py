# =============================================================================
# Training Agent - Custom Training Management
# =============================================================================
# Handles CRUD operations for custom trainings (Sasha Tutor feature).
#
# Framework: Google ADK with native Gemini 3.0 Pro
#
# Operations:
# - create_training: Create new training with title/description
# - get_training: Fetch training by ID
# - list_trainings: List user's trainings
# - delete_training: Delete training
# - process_source: Process document/URL/YouTube source
# - consolidate_content: Merge all sources into unified content
# - generate_summary: AI-generated content summary
#
# Storage:
# - DynamoDB: hive-academy-trainings-prod (single-table design)
# - S3: hive-academy-trainings-prod (documents, thumbnails)
# =============================================================================

import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

import boto3
from botocore.exceptions import ClientError

# Lazy imports for tools (reduce cold start)
_document_processor = None
_web_scraper = None
_content_consolidator = None


def _get_document_processor():
    """Lazy load document processor."""
    global _document_processor
    if _document_processor is None:
        from tools import document_processor
        _document_processor = document_processor
    return _document_processor


def _get_web_scraper():
    """Lazy load web scraper."""
    global _web_scraper
    if _web_scraper is None:
        from tools import web_scraper
        _web_scraper = web_scraper
    return _web_scraper


def _get_content_consolidator():
    """Lazy load content consolidator."""
    global _content_consolidator
    if _content_consolidator is None:
        from tools import content_consolidator
        _content_consolidator = content_consolidator
    return _content_consolidator


# =============================================================================
# Configuration
# =============================================================================

AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
TRAININGS_TABLE = os.getenv("TRAININGS_TABLE", "hive-academy-trainings-prod")
TRAININGS_BUCKET = os.getenv("TRAININGS_BUCKET", "hive-academy-trainings-prod")


# =============================================================================
# DynamoDB Client
# =============================================================================


def get_dynamodb():
    """Get DynamoDB resource."""
    return boto3.resource("dynamodb", region_name=AWS_REGION)


def get_table():
    """Get trainings table."""
    dynamodb = get_dynamodb()
    return dynamodb.Table(TRAININGS_TABLE)


# =============================================================================
# Training CRUD Operations
# =============================================================================


class TrainingAgent:
    """
    Training Agent - Manages custom trainings lifecycle.

    Handles creation, retrieval, updates, and deletion of trainings.
    Orchestrates source processing and content consolidation.
    """

    def __init__(self):
        """Initialize the training agent."""
        self.table = get_table()
        print(f"[TrainingAgent] Initialized with table: {TRAININGS_TABLE}")

    def _generate_id(self) -> str:
        """Generate unique training ID."""
        return f"tr_{uuid.uuid4().hex[:12]}"

    def _now_iso(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat() + "Z"

    async def create_training(
        self,
        user_id: str,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new training.

        Args:
            user_id: User creating the training
            tenant_id: Tenant/organization ID
            title: Training title
            description: Optional description
            category: Optional category

        Returns:
            Created training object
        """
        training_id = self._generate_id()
        now = self._now_iso()

        training = {
            "PK": f"TRAINING#{training_id}",
            "SK": "METADATA",
            "GSI1PK": f"USER#{user_id}",
            "GSI1SK": now,
            "GSI2PK": f"TENANT#{tenant_id}",
            "GSI2SK": now,
            "id": training_id,
            "userId": user_id,
            "tenantId": tenant_id,
            "title": title,
            "description": description or "",
            "category": category or "",
            "sources": [],
            "status": "draft",
            "createdAt": now,
            "updatedAt": now,
        }

        try:
            self.table.put_item(Item=training)
            print(f"[TrainingAgent] Created training: {training_id}")

            # Return clean response
            return {
                "success": True,
                "training": {
                    "id": training_id,
                    "userId": user_id,
                    "tenantId": tenant_id,
                    "title": title,
                    "description": description or "",
                    "category": category or "",
                    "sources": [],
                    "status": "draft",
                    "createdAt": now,
                    "updatedAt": now,
                },
            }

        except ClientError as e:
            print(f"[TrainingAgent] Create error: {e}")
            return {"success": False, "error": str(e)}

    async def get_training(
        self,
        training_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get training by ID.

        Args:
            training_id: Training ID
            user_id: Optional user ID for access check

        Returns:
            Training object or error
        """
        try:
            response = self.table.get_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                }
            )

            item = response.get("Item")
            if not item:
                return {"success": False, "error": "Training not found"}

            # Access check
            if user_id and item.get("userId") != user_id:
                return {"success": False, "error": "Access denied"}

            # Clean response
            training = {
                "id": item["id"],
                "userId": item["userId"],
                "tenantId": item["tenantId"],
                "title": item["title"],
                "description": item.get("description", ""),
                "category": item.get("category", ""),
                "sources": item.get("sources", []),
                "consolidatedContent": item.get("consolidatedContent"),
                "contentSummary": item.get("contentSummary"),
                "charCount": item.get("charCount"),
                "contentHash": item.get("contentHash"),
                "thumbnail": item.get("thumbnail"),
                "status": item["status"],
                "progress": item.get("progress"),
                "error": item.get("error"),
                "createdAt": item["createdAt"],
                "updatedAt": item["updatedAt"],
                "readyAt": item.get("readyAt"),
                "lastAccessedAt": item.get("lastAccessedAt"),
                "viewCount": item.get("viewCount", 0),
            }

            # Update last accessed
            self._update_last_accessed(training_id)

            return {"success": True, "training": training}

        except ClientError as e:
            print(f"[TrainingAgent] Get error: {e}")
            return {"success": False, "error": str(e)}

    def _update_last_accessed(self, training_id: str) -> None:
        """Update last accessed timestamp (fire and forget)."""
        try:
            self.table.update_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                },
                UpdateExpression="SET lastAccessedAt = :now, viewCount = if_not_exists(viewCount, :zero) + :one",
                ExpressionAttributeValues={
                    ":now": self._now_iso(),
                    ":zero": 0,
                    ":one": 1,
                },
            )
        except Exception:
            pass  # Non-critical

    async def list_trainings(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        start_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List trainings for a user.

        Args:
            user_id: User ID
            tenant_id: Optional tenant filter
            status: Optional status filter
            limit: Max results (default 50)
            start_key: Pagination cursor

        Returns:
            List of trainings with pagination
        """
        try:
            # Query by user (GSI1)
            query_params = {
                "IndexName": "GSI1",
                "KeyConditionExpression": "GSI1PK = :pk",
                "ExpressionAttributeValues": {
                    ":pk": f"USER#{user_id}",
                },
                "ScanIndexForward": False,  # Most recent first
                "Limit": limit,
            }

            # Add status filter if provided
            if status:
                query_params["FilterExpression"] = "#status = :status"
                query_params["ExpressionAttributeNames"] = {"#status": "status"}
                query_params["ExpressionAttributeValues"][":status"] = status

            # Add pagination
            if start_key:
                query_params["ExclusiveStartKey"] = json.loads(start_key)

            response = self.table.query(**query_params)

            trainings = []
            for item in response.get("Items", []):
                trainings.append({
                    "id": item["id"],
                    "title": item["title"],
                    "description": item.get("description", ""),
                    "category": item.get("category", ""),
                    "thumbnail": item.get("thumbnail"),
                    "status": item["status"],
                    "sourceCount": len(item.get("sources", [])),
                    "charCount": item.get("charCount"),
                    "createdAt": item["createdAt"],
                    "updatedAt": item["updatedAt"],
                    "lastAccessedAt": item.get("lastAccessedAt"),
                })

            result = {
                "success": True,
                "trainings": trainings,
                "count": len(trainings),
            }

            # Add pagination cursor
            if "LastEvaluatedKey" in response:
                result["nextKey"] = json.dumps(response["LastEvaluatedKey"])

            return result

        except ClientError as e:
            print(f"[TrainingAgent] List error: {e}")
            return {"success": False, "error": str(e), "trainings": []}

    async def delete_training(
        self,
        training_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a training.

        Args:
            training_id: Training ID
            user_id: User ID for access check

        Returns:
            Success or error
        """
        # First check ownership
        get_result = await self.get_training(training_id, user_id)
        if not get_result.get("success"):
            return get_result

        try:
            # Delete from DynamoDB
            self.table.delete_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                }
            )

            # Also delete any source items
            # (In single-table design, sources might be stored as separate items)
            # For now, sources are embedded in the training item

            # TODO: Delete S3 objects (documents, thumbnails)

            print(f"[TrainingAgent] Deleted training: {training_id}")
            return {"success": True, "deleted": training_id}

        except ClientError as e:
            print(f"[TrainingAgent] Delete error: {e}")
            return {"success": False, "error": str(e)}

    async def update_training_status(
        self,
        training_id: str,
        status: str,
        progress: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update training status and progress.

        Args:
            training_id: Training ID
            status: New status
            progress: Optional progress info
            error: Optional error message

        Returns:
            Success or error
        """
        try:
            update_expr = "SET #status = :status, updatedAt = :now"
            expr_values = {
                ":status": status,
                ":now": self._now_iso(),
            }
            expr_names = {"#status": "status"}

            if progress:
                update_expr += ", progress = :progress"
                expr_values[":progress"] = progress

            if error:
                update_expr += ", #error = :error"
                expr_values[":error"] = error
                expr_names["#error"] = "error"

            if status == "ready":
                update_expr += ", readyAt = :now"

            self.table.update_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                },
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names,
            )

            return {"success": True}

        except ClientError as e:
            print(f"[TrainingAgent] Status update error: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Source Processing
    # =========================================================================

    async def add_document_source(
        self,
        training_id: str,
        user_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
    ) -> Dict[str, Any]:
        """
        Add a document source and get upload URL.

        Args:
            training_id: Training ID
            user_id: User ID for access check
            file_name: Original filename
            file_type: MIME type
            file_size: File size in bytes

        Returns:
            Upload URL and source info
        """
        document_processor = _get_document_processor()

        source_id = f"src_{uuid.uuid4().hex[:8]}"
        safe_filename = "".join(c for c in file_name if c.isalnum() or c in "._-")
        s3_key = f"trainings/{training_id}/documents/{source_id}/{safe_filename}"

        # Generate pre-signed upload URL using the tool's function
        upload_result = document_processor.generate_presigned_upload_url(
            training_id=training_id,
            filename=file_name,
            version=1,
            expires_in=3600,  # 1 hour
        )

        upload_url = upload_result.get("upload_url", "")

        # Use the s3_key from the upload result if available
        actual_s3_key = upload_result.get("s3_key", s3_key)

        source = {
            "id": source_id,
            "type": "document",
            "name": file_name,
            "filename": file_name,
            "fileSize": file_size,
            "mimeType": file_type,
            "s3Key": actual_s3_key,
            "status": "pending",
            "createdAt": self._now_iso(),
        }

        # Add to training's sources array
        try:
            self.table.update_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                },
                UpdateExpression="SET sources = list_append(if_not_exists(sources, :empty), :source), updatedAt = :now",
                ExpressionAttributeValues={
                    ":source": [source],
                    ":empty": [],
                    ":now": self._now_iso(),
                },
            )

            return {
                "success": True,
                "source": source,
                "uploadUrl": upload_url,
            }

        except ClientError as e:
            print(f"[TrainingAgent] Add document error: {e}")
            return {"success": False, "error": str(e)}

    async def add_url_source(
        self,
        training_id: str,
        user_id: str,
        url: str,
    ) -> Dict[str, Any]:
        """
        Add a URL source and start scraping.

        Args:
            training_id: Training ID
            user_id: User ID for access check
            url: URL to scrape

        Returns:
            Source info with extracted content
        """
        web_scraper = _get_web_scraper()

        source_id = f"src_{uuid.uuid4().hex[:8]}"

        # Check if YouTube
        if web_scraper.is_youtube_url(url):
            return await self.add_youtube_source(training_id, user_id, url)

        source = {
            "id": source_id,
            "type": "url",
            "name": url,
            "url": url,
            "status": "processing",
            "createdAt": self._now_iso(),
        }

        # Add source first (as processing)
        try:
            self.table.update_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                },
                UpdateExpression="SET sources = list_append(if_not_exists(sources, :empty), :source), updatedAt = :now",
                ExpressionAttributeValues={
                    ":source": [source],
                    ":empty": [],
                    ":now": self._now_iso(),
                },
            )
        except ClientError as e:
            return {"success": False, "error": str(e)}

        # Scrape URL
        try:
            result = web_scraper.scrape_url(url)

            # Update source with result
            source["status"] = "completed"
            source["text"] = result["text"]
            source["charCount"] = result["char_count"]
            source["title"] = result.get("title")
            source["domain"] = result.get("domain")
            source["description"] = result.get("description")
            source["processedAt"] = self._now_iso()

            # Update in DynamoDB (replace source in array)
            await self._update_source(training_id, source_id, source)

            return {"success": True, "source": source}

        except Exception as e:
            # Update source with error
            source["status"] = "error"
            source["error"] = str(e)
            await self._update_source(training_id, source_id, source)

            return {"success": False, "error": str(e), "source": source}

    async def add_youtube_source(
        self,
        training_id: str,
        user_id: str,
        youtube_url: str,
    ) -> Dict[str, Any]:
        """
        Add a YouTube source and extract transcript.

        Args:
            training_id: Training ID
            user_id: User ID for access check
            youtube_url: YouTube URL

        Returns:
            Source info with transcript
        """
        web_scraper = _get_web_scraper()
        url = youtube_url  # Alias for compatibility

        video_id = web_scraper.extract_youtube_id(url)
        if not video_id:
            return {"success": False, "error": "Invalid YouTube URL"}

        source_id = f"src_{uuid.uuid4().hex[:8]}"

        source = {
            "id": source_id,
            "type": "youtube",
            "name": f"YouTube: {video_id}",
            "url": url,
            "videoId": video_id,
            "status": "processing",
            "createdAt": self._now_iso(),
        }

        # Add source first
        try:
            self.table.update_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                },
                UpdateExpression="SET sources = list_append(if_not_exists(sources, :empty), :source), updatedAt = :now",
                ExpressionAttributeValues={
                    ":source": [source],
                    ":empty": [],
                    ":now": self._now_iso(),
                },
            )
        except ClientError as e:
            return {"success": False, "error": str(e)}

        # TODO: Extract YouTube transcript using youtube_transcript_api
        # For now, return as pending (user needs to wait for processing)
        source["status"] = "pending"
        source["text"] = f"[YouTube transcript for {video_id} - processing...]"

        return {"success": True, "source": source}

    async def _update_source(
        self,
        training_id: str,
        source_id: str,
        updated_source: Dict[str, Any],
    ) -> None:
        """Update a specific source in the sources array."""
        # Get current training
        response = self.table.get_item(
            Key={
                "PK": f"TRAINING#{training_id}",
                "SK": "METADATA",
            }
        )

        item = response.get("Item")
        if not item:
            return

        # Find and update source
        sources = item.get("sources", [])
        for i, source in enumerate(sources):
            if source.get("id") == source_id:
                sources[i] = updated_source
                break

        # Update training
        self.table.update_item(
            Key={
                "PK": f"TRAINING#{training_id}",
                "SK": "METADATA",
            },
            UpdateExpression="SET sources = :sources, updatedAt = :now",
            ExpressionAttributeValues={
                ":sources": sources,
                ":now": self._now_iso(),
            },
        )

    async def process_document_source(
        self,
        training_id: str,
        source_id: str,
    ) -> Dict[str, Any]:
        """
        Process an uploaded document and extract text.

        Args:
            training_id: Training ID
            source_id: Source ID

        Returns:
            Extracted content info
        """
        document_processor = _get_document_processor()

        # Get training and source
        get_result = await self.get_training(training_id)
        if not get_result.get("success"):
            return get_result

        training = get_result["training"]
        source = None
        for s in training.get("sources", []):
            if s.get("id") == source_id:
                source = s
                break

        if not source:
            return {"success": False, "error": "Source not found"}

        if source.get("type") != "document":
            return {"success": False, "error": "Not a document source"}

        s3_key = source.get("s3Key")
        if not s3_key:
            return {"success": False, "error": "No S3 key for source"}

        # Update status to processing
        source["status"] = "processing"
        await self._update_source(training_id, source_id, source)

        try:
            # Download and process document
            result = document_processor.process_document_from_s3(s3_key)

            source["status"] = "completed"
            source["text"] = result["text"]
            source["charCount"] = result["char_count"]
            source["processedAt"] = self._now_iso()

            await self._update_source(training_id, source_id, source)

            return {"success": True, "source": source}

        except Exception as e:
            source["status"] = "error"
            source["error"] = str(e)
            await self._update_source(training_id, source_id, source)

            return {"success": False, "error": str(e)}

    # =========================================================================
    # Content Consolidation
    # =========================================================================

    async def consolidate_content(
        self,
        training_id: str,
        user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Consolidate all sources into unified training content.

        Args:
            training_id: Training ID
            user_id: User ID for access check (None skips check)

        Returns:
            Consolidation result
        """
        content_consolidator = _get_content_consolidator()

        # Get training (user_id=None skips ownership check for read operations)
        get_result = await self.get_training(training_id, user_id=None)
        if not get_result.get("success"):
            return get_result

        training = get_result["training"]

        # Check all sources are processed
        sources = training.get("sources", [])
        ready_sources = [s for s in sources if s.get("status") == "completed"]

        if not ready_sources:
            return {"success": False, "error": "No processed sources available"}

        # Update status
        await self.update_training_status(
            training_id,
            "consolidating",
            progress={"step": "Consolidando conteudo...", "percentage": 50},
        )

        try:
            # Prepare sources for consolidation
            consolidation_sources = []
            for source in ready_sources:
                consolidation_sources.append({
                    "type": source.get("type"),
                    "text": source.get("text", ""),
                    "filename": source.get("filename"),
                    "url": source.get("url"),
                    "title": source.get("title"),
                    "video_id": source.get("videoId"),
                    "char_count": source.get("charCount", 0),
                })

            # Consolidate
            result = content_consolidator.consolidate_content(
                sources=consolidation_sources,
                training_title=training.get("title"),
                training_id=training_id,
            )

            # Update training with consolidated content
            self.table.update_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                },
                UpdateExpression="""
                    SET consolidatedContent = :content,
                        charCount = :charCount,
                        contentHash = :hash,
                        #status = :status,
                        updatedAt = :now
                """,
                ExpressionAttributeValues={
                    ":content": result["consolidated_text"],
                    ":charCount": result["char_count"],
                    ":hash": result["content_hash"],
                    ":status": "ready",
                    ":now": self._now_iso(),
                },
                ExpressionAttributeNames={"#status": "status"},
            )

            return {
                "success": True,
                "charCount": result["char_count"],
                "sourceCount": result["source_count"],
                "contentHash": result["content_hash"],
            }

        except Exception as e:
            await self.update_training_status(
                training_id,
                "error",
                error=str(e),
            )
            return {"success": False, "error": str(e)}

    async def generate_summary(
        self,
        training_id: str,
        user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generate AI summary of consolidated content.

        Args:
            training_id: Training ID
            user_id: User ID for access check (None skips check)

        Returns:
            Generated summary
        """
        # Get training (user_id=None skips ownership check for read operations)
        get_result = await self.get_training(training_id, user_id=None)
        if not get_result.get("success"):
            return get_result

        training = get_result["training"]
        content = training.get("consolidatedContent")

        if not content:
            return {"success": False, "error": "No consolidated content"}

        # Lazy import Gemini agent
        from agents.sasha_agent import SashaAgent
        agent = SashaAgent()

        prompt = f"""
Analise o seguinte conteudo de treinamento e gere um resumo executivo em portugues.

O resumo deve:
1. Ter 3-5 paragrafos
2. Destacar os principais topicos abordados
3. Identificar os objetivos de aprendizagem
4. Ser escrito em tom profissional e acessivel

Conteudo:
{content[:10000]}

Retorne apenas o resumo, sem introducao ou explicacao adicional.
"""

        try:
            summary = await agent.invoke(prompt, "system", f"summary-{training_id}")

            # Update training
            self.table.update_item(
                Key={
                    "PK": f"TRAINING#{training_id}",
                    "SK": "METADATA",
                },
                UpdateExpression="SET contentSummary = :summary, updatedAt = :now",
                ExpressionAttributeValues={
                    ":summary": summary,
                    ":now": self._now_iso(),
                },
            )

            return {"success": True, "summary": summary}

        except Exception as e:
            return {"success": False, "error": str(e)}
