# =============================================================================
# S3 Client for SGA Inventory
# =============================================================================
# Client for all S3 operations in the inventory management module.
#
# Features:
# - Presigned URL generation for secure uploads/downloads
# - Organized directory structure for NFs, evidences, inventories
# - Temporary upload staging with auto-cleanup
# - Content type detection
#
# CRITICAL: Lazy imports for cold start optimization (<30s limit)
# =============================================================================

from typing import Optional, Dict, Any, List
from datetime import datetime
import os

# Lazy imports - boto3 imported only when needed
_s3_client = None


def _get_s3_client():
    """
    Get S3 client with lazy initialization.

    CRITICAL: Must use signature_version='s3v4' for presigned URLs.
    S3 buckets in us-east-2 require SigV4 - SigV2 URLs return 400 Bad Request.

    Returns:
        boto3 S3 client configured for us-east-2 with SigV4
    """
    global _s3_client
    if _s3_client is None:
        import boto3
        from botocore.config import Config

        # CRITICAL: Configure S3 client for SigV4 presigned URLs
        # Without this, presigned URLs use SigV2 which fails with 400 Bad Request
        # See CLAUDE.md "S3 Presigned URL Issues - CORS 307 Redirect (CRITICAL)"
        config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'virtual'}
        )
        _s3_client = boto3.client(
            's3',
            region_name='us-east-2',
            config=config
        )
    return _s3_client


def _get_bucket_name() -> str:
    """Get documents bucket name from environment."""
    return os.environ.get("DOCUMENTS_BUCKET", "faiston-one-sga-documents-prod")


# =============================================================================
# S3 Client Class
# =============================================================================


class SGAS3Client:
    """
    S3 client for SGA Inventory document management.

    Directory Structure:
    - notas-fiscais/{YYYY}/{MM}/{nf_id}/ - NF files
    - evidences/{movement_id}/ - Movement evidence
    - inventories/{campaign_id}/ - Inventory campaign files
    - temp/uploads/ - Temporary upload staging

    Example:
        client = SGAS3Client()
        url = client.generate_upload_url("temp/uploads/doc.pdf", "application/pdf")
    """

    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize the S3 client.

        Args:
            bucket_name: Override bucket name (for testing)
        """
        self._bucket = bucket_name or _get_bucket_name()

    @property
    def bucket(self) -> str:
        """Get bucket name."""
        return self._bucket

    @property
    def client(self):
        """Get S3 client with lazy loading."""
        return _get_s3_client()

    # =========================================================================
    # Presigned URL Generation
    # =========================================================================

    def generate_upload_url(
        self,
        key: str,
        content_type: str = "application/octet-stream",
        expires_in: int = 3600,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for file upload.

        Args:
            key: S3 object key (path)
            content_type: MIME type of the file
            expires_in: URL expiration in seconds (default 1 hour)
            metadata: Optional metadata to attach

        Returns:
            Dict with upload_url and key
        """
        try:
            params = {
                "Bucket": self._bucket,
                "Key": key,
                "ContentType": content_type,
            }

            if metadata:
                params["Metadata"] = metadata

            url = self.client.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=expires_in,
            )

            return {
                "success": True,
                "upload_url": url,
                "key": key,
                "bucket": self._bucket,
                "content_type": content_type,
                "expires_in": expires_in,
            }
        except Exception as e:
            print(f"[S3] generate_upload_url error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def generate_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for file download.

        Args:
            key: S3 object key (path)
            expires_in: URL expiration in seconds (default 1 hour)
            filename: Optional filename for Content-Disposition

        Returns:
            Dict with download_url and key
        """
        try:
            params = {
                "Bucket": self._bucket,
                "Key": key,
            }

            if filename:
                params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

            url = self.client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )

            return {
                "success": True,
                "download_url": url,
                "key": key,
                "expires_in": expires_in,
            }
        except Exception as e:
            print(f"[S3] generate_download_url error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Direct File Operations
    # =========================================================================

    def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Upload file data directly to S3.

        Args:
            key: S3 object key (path)
            data: File data as bytes
            content_type: MIME type
            metadata: Optional metadata

        Returns:
            True if successful
        """
        try:
            params = {
                "Bucket": self._bucket,
                "Key": key,
                "Body": data,
                "ContentType": content_type,
            }

            if metadata:
                params["Metadata"] = metadata

            self.client.put_object(**params)
            return True
        except Exception as e:
            print(f"[S3] upload_file error: {e}")
            return False

    def download_file(self, key: str) -> Optional[bytes]:
        """
        Download file data from S3.

        Args:
            key: S3 object key (path)

        Returns:
            File data as bytes, or None if error
        """
        try:
            response = self.client.get_object(
                Bucket=self._bucket,
                Key=key,
            )
            return response["Body"].read()
        except Exception as e:
            print(f"[S3] download_file error: {e}")
            return None

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            key: S3 object key (path)

        Returns:
            True if successful
        """
        try:
            self.client.delete_object(
                Bucket=self._bucket,
                Key=key,
            )
            return True
        except Exception as e:
            print(f"[S3] delete_file error: {e}")
            return False

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """
        Copy a file within the bucket.

        Args:
            source_key: Source object key
            dest_key: Destination object key

        Returns:
            True if successful
        """
        try:
            self.client.copy_object(
                Bucket=self._bucket,
                CopySource={"Bucket": self._bucket, "Key": source_key},
                Key=dest_key,
            )
            return True
        except Exception as e:
            print(f"[S3] copy_file error: {e}")
            return False

    def move_file(self, source_key: str, dest_key: str) -> bool:
        """
        Move a file (copy then delete).

        Args:
            source_key: Source object key
            dest_key: Destination object key

        Returns:
            True if successful
        """
        if self.copy_file(source_key, dest_key):
            return self.delete_file(source_key)
        return False

    def list_files(
        self,
        prefix: str,
        max_keys: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List files with a given prefix.

        Args:
            prefix: Key prefix to filter
            max_keys: Maximum files to return

        Returns:
            List of file info dicts
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            files = []
            for obj in response.get("Contents", []):
                files.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                })

            return files
        except Exception as e:
            print(f"[S3] list_files error: {e}")
            return []

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists.

        Args:
            key: S3 object key

        Returns:
            True if file exists
        """
        try:
            self.client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    # =========================================================================
    # Path Generation Helpers
    # =========================================================================

    def get_nf_path(
        self,
        nf_id: str,
        filename: str,
        year_month: Optional[str] = None,
    ) -> str:
        """
        Generate path for NF file.

        Args:
            nf_id: NF identifier
            filename: File name (e.g., "original.pdf")
            year_month: Optional YYYY/MM, defaults to current

        Returns:
            S3 key path
        """
        if not year_month:
            now = datetime.utcnow()
            year_month = f"{now.year}/{now.month:02d}"

        return f"notas-fiscais/{year_month}/{nf_id}/{filename}"

    def get_evidence_path(
        self,
        movement_id: str,
        evidence_type: str,
        filename: str,
    ) -> str:
        """
        Generate path for movement evidence.

        Args:
            movement_id: Movement identifier
            evidence_type: Type (photos, signatures, documents)
            filename: File name

        Returns:
            S3 key path
        """
        return f"evidences/{movement_id}/{evidence_type}/{filename}"

    def get_inventory_path(
        self,
        campaign_id: str,
        file_type: str,
        filename: str,
    ) -> str:
        """
        Generate path for inventory campaign file.

        Args:
            campaign_id: Campaign identifier
            file_type: Type (photos, exports)
            filename: File name

        Returns:
            S3 key path
        """
        return f"inventories/{campaign_id}/{file_type}/{filename}"

    def get_temp_path(self, filename: str) -> str:
        """
        Generate path for temporary upload.

        Files in temp/ are auto-deleted after 24 hours.

        Args:
            filename: File name

        Returns:
            S3 key path in temp folder
        """
        import uuid
        unique = str(uuid.uuid4())[:8]
        return f"temp/uploads/{unique}_{filename}"

    def move_from_temp(self, temp_key: str, final_key: str) -> bool:
        """
        Move file from temp staging to final location.

        Args:
            temp_key: Temporary key (from get_temp_path)
            final_key: Final destination key

        Returns:
            True if successful
        """
        return self.move_file(temp_key, final_key)

    # =========================================================================
    # NF Specific Operations
    # =========================================================================

    def upload_nf_xml(
        self,
        nf_id: str,
        xml_content: str,
        year_month: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload NF XML file.

        Args:
            nf_id: NF identifier
            xml_content: XML content as string
            year_month: Optional YYYY/MM

        Returns:
            Dict with success status and key
        """
        key = self.get_nf_path(nf_id, "original.xml", year_month)
        success = self.upload_file(
            key=key,
            data=xml_content.encode("utf-8"),
            content_type="application/xml",
        )
        return {
            "success": success,
            "key": key if success else None,
        }

    def upload_nf_extraction(
        self,
        nf_id: str,
        extraction: Dict[str, Any],
        year_month: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload NF extraction result as JSON.

        Args:
            nf_id: NF identifier
            extraction: Extraction dict
            year_month: Optional YYYY/MM

        Returns:
            Dict with success status and key
        """
        import json

        key = self.get_nf_path(nf_id, "extraction.json", year_month)
        success = self.upload_file(
            key=key,
            data=json.dumps(extraction, ensure_ascii=False, indent=2).encode("utf-8"),
            content_type="application/json",
        )
        return {
            "success": success,
            "key": key if success else None,
        }

    def get_nf_files(self, nf_id: str) -> List[Dict[str, Any]]:
        """
        List all files for an NF.

        Args:
            nf_id: NF identifier

        Returns:
            List of file info dicts
        """
        # Search in recent months
        files = []
        now = datetime.utcnow()

        for months_ago in range(12):  # Search last 12 months
            month = now.month - months_ago
            year = now.year
            while month <= 0:
                month += 12
                year -= 1

            prefix = f"notas-fiscais/{year}/{month:02d}/{nf_id}/"
            month_files = self.list_files(prefix)

            if month_files:
                files.extend(month_files)
                break  # Found files, stop searching

        return files
