#!/usr/bin/env python3
"""
Test script for Linear attachment upload functionality.

Usage:
    python test_linear_attachments.py --issue-id PR-123 --file /path/to/file.log
    python test_linear_attachments.py --issue-id PR-123 --text "Error log content" --filename error.log
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent / "shared" / "lib"))

from linear_attachments import (
    LinearAttachmentUploader,
    upload_text_as_file,
    attach_execution_artifacts,
)


async def test_file_upload(issue_id: str, file_path: str):
    """Test uploading a file from disk"""
    print(f"\n🧪 Testing file upload: {file_path} → {issue_id}")

    async with LinearAttachmentUploader() as uploader:
        attachment = await uploader.upload_file(
            issue_id=issue_id,
            file_path=file_path,
            subtitle=f"Test upload via linear_attachments.py",
        )

        print(f"✅ Success!")
        print(f"   Attachment ID: {attachment.id}")
        print(f"   URL: {attachment.url}")
        print(f"   Title: {attachment.title}")
        print(f"   Created: {attachment.created_at}")

    return attachment


async def test_text_upload(issue_id: str, text: str, filename: str):
    """Test uploading text content as a file"""
    print(f"\n🧪 Testing text upload: {len(text)} chars → {filename} → {issue_id}")

    attachment = await upload_text_as_file(
        issue_id=issue_id, content=text, filename=filename, title=f"Test: {filename}"
    )

    print(f"✅ Success!")
    print(f"   Attachment ID: {attachment.id}")
    print(f"   URL: {attachment.url}")
    print(f"   Title: {attachment.title}")

    return attachment


async def test_multiple_artifacts(issue_id: str):
    """Test uploading multiple execution artifacts"""
    print(f"\n🧪 Testing multiple artifacts upload → {issue_id}")

    artifacts = {
        "Deployment Log": """
[2025-11-22 10:30:15] Starting deployment...
[2025-11-22 10:30:20] Building Docker image...
[2025-11-22 10:32:45] Pushing to registry...
[2025-11-22 10:35:10] Deployment complete!
        """.strip(),
        "Git Diff": """
diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,7 +10,7 @@ def main():
-    return "Hello"
+    return "Hello, World!"
        """.strip(),
        "Test Results": """
============================= test session starts ==============================
collected 15 items

tests/test_api.py::test_health PASSED                                    [  6%]
tests/test_api.py::test_orchestrate PASSED                               [ 13%]
tests/test_integration.py::test_workflow PASSED                          [ 20%]

========================= 15 passed in 2.34s ================================
        """.strip(),
    }

    attachments = await attach_execution_artifacts(
        issue_id=issue_id, artifacts=artifacts
    )

    print(f"✅ Success! Uploaded {len(attachments)} artifacts:")
    for attachment in attachments:
        print(f"   - {attachment.title}: {attachment.url}")

    return attachments


async def test_multiple_files(issue_id: str, file_paths: list):
    """Test uploading multiple files"""
    print(f"\n🧪 Testing multiple file upload: {len(file_paths)} files → {issue_id}")

    async with LinearAttachmentUploader() as uploader:
        attachments = await uploader.upload_multiple_files(
            issue_id=issue_id, file_paths=file_paths
        )

        print(f"✅ Success! Uploaded {len(attachments)}/{len(file_paths)} files:")
        for attachment in attachments:
            print(f"   - {attachment.title}: {attachment.url}")

    return attachments


async def main():
    parser = argparse.ArgumentParser(description="Test Linear attachment uploads")
    parser.add_argument(
        "--issue-id", required=True, help="Linear issue ID (e.g., PR-123)"
    )

    # Mode 1: Upload file
    parser.add_argument("--file", help="Path to file to upload")

    # Mode 2: Upload text as file
    parser.add_argument("--text", help="Text content to upload")
    parser.add_argument(
        "--filename", help="Filename for text upload (required with --text)"
    )

    # Mode 3: Upload multiple files
    parser.add_argument("--files", nargs="+", help="Multiple files to upload")

    # Mode 4: Test artifacts
    parser.add_argument(
        "--test-artifacts",
        action="store_true",
        help="Test uploading sample execution artifacts",
    )

    args = parser.parse_args()

    # Verify LINEAR_API_KEY is set
    if not os.getenv("LINEAR_API_KEY"):
        print("❌ Error: LINEAR_API_KEY environment variable not set")
        print("\nSet it with:")
        print('  $env:LINEAR_API_KEY="lin_oauth_..."  # PowerShell')
        print('  export LINEAR_API_KEY="lin_oauth_..."  # Bash')
        return 1

    try:
        if args.file:
            await test_file_upload(args.issue_id, args.file)

        elif args.text:
            if not args.filename:
                print("❌ Error: --filename required with --text")
                return 1
            await test_text_upload(args.issue_id, args.text, args.filename)

        elif args.files:
            await test_multiple_files(args.issue_id, args.files)

        elif args.test_artifacts:
            await test_multiple_artifacts(args.issue_id)

        else:
            print("❌ Error: Specify one of: --file, --text, --files, --test-artifacts")
            parser.print_help()
            return 1

        print("\n✅ All tests passed!")
        return 0

    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
