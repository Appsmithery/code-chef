"""
Linear File Attachments Module

Handles uploading files directly to Linear using their native attachment API.
Supports multipart/form-data uploads with S3-backed storage.

Usage:
    from shared.lib.linear_attachments import LinearAttachmentUploader

    uploader = LinearAttachmentUploader(api_key="lin_oauth_...")
    attachment_url = await uploader.upload_file(
        issue_id="PR-123",
        file_path="/path/to/file.log"
    )
"""

import os
import mimetypes
from typing import Optional, Dict, Any, List
from pathlib import Path
import httpx
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class FileUploadRequest(BaseModel):
    """Request for Linear file upload URL"""

    content_type: str = Field(..., description="MIME type of the file")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")


class FileUploadResponse(BaseModel):
    """Response from Linear file upload URL request"""

    upload_url: str = Field(..., description="S3 pre-signed upload URL")
    asset_url: str = Field(..., description="Final CDN URL after upload")


class AttachmentCreateRequest(BaseModel):
    """Request to attach uploaded file to Linear issue"""

    issue_id: str = Field(..., description="Linear issue ID")
    url: str = Field(..., description="Asset URL from upload response")
    title: str = Field(..., description="Display title for attachment")
    subtitle: Optional[str] = Field(None, description="Optional subtitle")
    icon_url: Optional[str] = Field(None, description="Optional icon URL")


class Attachment(BaseModel):
    """Linear attachment metadata"""

    id: str = Field(..., description="Attachment UUID")
    url: str = Field(..., description="Asset URL")
    title: str = Field(..., description="Display title")
    subtitle: Optional[str] = None
    created_at: str = Field(..., description="ISO timestamp")


class LinearAttachmentUploader:
    """Handles file uploads to Linear via GraphQL + S3"""

    GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize uploader with Linear API key.

        Args:
            api_key: Linear OAuth token (defaults to LINEAR_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError("LINEAR_API_KEY required (env or constructor)")

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _guess_content_type(self, file_path: str) -> str:
        """Guess MIME type from file extension"""
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or "application/octet-stream"

    async def _request_upload_url(
        self, filename: str, content_type: str, size: int
    ) -> FileUploadResponse:
        """
        Request pre-signed S3 upload URL from Linear.

        GraphQL Mutation:
            uploadFile(contentType: String!, filename: String!, size: Int!)
        """
        mutation = """
        mutation UploadFile($contentType: String!, $filename: String!, $size: Int!) {
          uploadFile(contentType: $contentType, filename: $filename, size: $size) {
            uploadFile
            assetUrl
          }
        }
        """

        payload = {
            "query": mutation,
            "variables": {
                "contentType": content_type,
                "filename": filename,
                "size": size,
            },
        }

        logger.info(
            f"Requesting upload URL for {filename} ({size} bytes, {content_type})"
        )

        response = await self.client.post(self.GRAPHQL_ENDPOINT, json=payload)

        # Check for errors before raise_for_status to get GraphQL error details
        if response.status_code != 200:
            try:
                error_data = response.json()
                if "errors" in error_data:
                    errors = error_data["errors"]
                    error_msg = "; ".join([e.get("message", str(e)) for e in errors])
                    logger.error(f"Linear GraphQL error details: {error_msg}")
                    raise RuntimeError(
                        f"Linear GraphQL error ({response.status_code}): {error_msg}"
                    )
            except RuntimeError:
                raise
            except Exception:
                pass
            response.raise_for_status()

        data = response.json()

        if "errors" in data:
            errors = data["errors"]
            error_msg = "; ".join([e.get("message", str(e)) for e in errors])
            raise RuntimeError(f"Linear GraphQL error: {error_msg}")

        upload_data = data["data"]["uploadFile"]

        return FileUploadResponse(
            upload_url=upload_data["uploadFile"], asset_url=upload_data["assetUrl"]
        )

    async def _upload_to_s3(
        self, upload_url: str, file_content: bytes, content_type: str
    ) -> None:
        """
        Upload file to S3 using pre-signed URL.

        Args:
            upload_url: Pre-signed S3 PUT URL
            file_content: Raw file bytes
            content_type: MIME type for Content-Type header
        """
        logger.info(f"Uploading {len(file_content)} bytes to S3...")

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as s3_client:
            response = await s3_client.put(
                upload_url, content=file_content, headers={"Content-Type": content_type}
            )
            response.raise_for_status()

        logger.info("S3 upload successful")

    async def _attach_to_issue(
        self, issue_id: str, asset_url: str, title: str, subtitle: Optional[str] = None
    ) -> Attachment:
        """
        Create Linear attachment linking asset to issue.

        GraphQL Mutation:
            attachmentCreate(input: AttachmentCreateInput!)
        """
        mutation = """
        mutation AttachmentCreate($issueId: String!, $url: String!, $title: String!, $subtitle: String) {
          attachmentCreate(input: {
            issueId: $issueId
            url: $url
            title: $title
            subtitle: $subtitle
          }) {
            attachment {
              id
              url
              title
              subtitle
              createdAt
            }
          }
        }
        """

        payload = {
            "query": mutation,
            "variables": {
                "issueId": issue_id,
                "url": asset_url,
                "title": title,
                "subtitle": subtitle,
            },
        }

        logger.info(f"Attaching {title} to issue {issue_id}...")

        response = await self.client.post(self.GRAPHQL_ENDPOINT, json=payload)
        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            errors = data["errors"]
            error_msg = "; ".join([e.get("message", str(e)) for e in errors])
            raise RuntimeError(f"Linear GraphQL error: {error_msg}")

        attachment_data = data["data"]["attachmentCreate"]["attachment"]

        return Attachment(**attachment_data)

    async def upload_file(
        self,
        issue_id: str,
        file_path: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
    ) -> Attachment:
        """
        NOTE: Linear API doesn't support direct file uploads.
        This creates a link attachment instead.

        For actual file storage, use GitHub Gist or external hosting.

        Args:
            issue_id: Linear issue ID (e.g., "PR-123")
            file_path: Path to file to upload (will be read and stored as text)
            title: Display title (defaults to filename)
            subtitle: Optional subtitle/description

        Returns:
            Attachment object with id, url, title, created_at

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If Linear API returns errors

        Example:
            >>> uploader = LinearAttachmentUploader()
            >>> attachment = await uploader.upload_file(
            ...     issue_id="PR-123",
            ...     file_path="logs/error.log",
            ...     title="Error Log"
            ... )
        """
        raise NotImplementedError(
            "Linear API doesn't support direct file uploads. "
            "Use GitHub Gist (github_gist_uploader.py) or upload to external "
            "hosting and attach URL with attach_link() method."
        )

    async def upload_multiple_files(
        self,
        issue_id: str,
        file_paths: List[str],
        titles: Optional[Dict[str, str]] = None,
    ) -> List[Attachment]:
        """
        Upload multiple files to a Linear issue.

        Args:
            issue_id: Linear issue ID
            file_paths: List of file paths to upload
            titles: Optional mapping of file_path -> display title

        Returns:
            List of Attachment objects

        Example:
            >>> attachments = await uploader.upload_multiple_files(
            ...     issue_id="PR-123",
            ...     file_paths=["error.log", "debug.log", "config.yaml"],
            ...     titles={"error.log": "Production Error Log"}
            ... )
        """
        titles = titles or {}
        attachments = []

        for file_path in file_paths:
            try:
                title = titles.get(file_path)
                attachment = await self.upload_file(
                    issue_id=issue_id, file_path=file_path, title=title
                )
                attachments.append(attachment)
            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {e}")
                # Continue with remaining files

        return attachments


async def upload_text_as_file(
    issue_id: str,
    content: str,
    filename: str,
    title: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Attachment:
    """
    Helper to upload text content as a file attachment.

    Useful for attaching logs, diffs, stack traces, etc.

    Args:
        issue_id: Linear issue ID
        content: Text content to upload
        filename: Filename (with extension for MIME type detection)
        title: Display title (defaults to filename)
        api_key: Linear API key (optional)

    Returns:
        Attachment object

    Example:
        >>> error_log = "ERROR: Connection refused\\n..."
        >>> attachment = await upload_text_as_file(
        ...     issue_id="PR-123",
        ...     content=error_log,
        ...     filename="deployment_error.log",
        ...     title="Deployment Error Log"
        ... )
    """
    import tempfile

    # Write to temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=Path(filename).suffix, delete=False
    ) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        async with LinearAttachmentUploader(api_key=api_key) as uploader:
            # Upload with desired filename
            attachment = await uploader.upload_file(
                issue_id=issue_id, file_path=tmp_path, title=title or filename
            )

        return attachment
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


# Convenience function for orchestrator integration
async def attach_execution_artifacts(
    issue_id: str, artifacts: Dict[str, str], api_key: Optional[str] = None
) -> List[Attachment]:
    """
    Attach execution artifacts (logs, diffs, reports) to Linear issue.

    Args:
        issue_id: Linear issue ID
        artifacts: Mapping of title -> content
        api_key: Linear API key (optional)

    Returns:
        List of created attachments

    Example (in orchestrator):
        >>> artifacts = {
        ...     "Deployment Log": deployment_output,
        ...     "Git Diff": git_diff_output,
        ...     "Test Results": pytest_report
        ... }
        >>> attachments = await attach_execution_artifacts(
        ...     issue_id=task.linear_issue_id,
        ...     artifacts=artifacts
        ... )
    """
    attachments = []

    for title, content in artifacts.items():
        try:
            # Infer extension from title
            extension = ".log" if "log" in title.lower() else ".txt"
            filename = f"{title.replace(' ', '_').lower()}{extension}"

            attachment = await upload_text_as_file(
                issue_id=issue_id,
                content=content,
                filename=filename,
                title=title,
                api_key=api_key,
            )
            attachments.append(attachment)

            logger.info(f"Attached '{title}' to {issue_id}")
        except Exception as e:
            logger.error(f"Failed to attach '{title}': {e}")

    return attachments
