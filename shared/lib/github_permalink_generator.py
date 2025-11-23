"""
GitHub Permalink Generator

Generates permanent GitHub URLs to code files and line ranges.
Permalinks include commit SHA to ensure they remain valid even if files are moved/renamed.

Usage:
    from shared.lib.github_permalink_generator import init_permalink_generator, generate_permalink

    # Initialize at startup
    init_permalink_generator("https://github.com/Appsmithery/Dev-Tools")

    # Generate permalink
    url = generate_permalink("agent_orchestrator/main.py", line_start=45, line_end=67)
    # Result: https://github.com/Appsmithery/Dev-Tools/blob/abc123/agent_orchestrator/main.py#L45-L67
"""

import re
import subprocess
from typing import Optional, List
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileReference:
    """Represents a code file reference with optional line numbers."""

    path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: Optional[str] = None


class GitHubPermalinkGenerator:
    """Generate GitHub permalinks for code references."""

    def __init__(self, repo_url: str, repo_path: str = "."):
        """
        Initialize with repository URL.

        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)
            repo_path: Path to local git repository (defaults to current directory)
        """
        self.repo_url = repo_url.rstrip(".git").rstrip("/")
        self.repo_path = Path(repo_path).resolve()
        logger.info(f"Initialized GitHub permalink generator for {self.repo_url}")

    def get_current_commit_sha(self) -> str:
        """
        Get current HEAD commit SHA.

        Returns:
            40-character commit SHA

        Raises:
            subprocess.CalledProcessError: If not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            sha = result.stdout.strip()
            logger.debug(f"Current commit SHA: {sha[:7]}")
            return sha
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get commit SHA: {e.stderr}")
            raise

    def generate_permalink(
        self,
        file_path: str,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        commit_sha: Optional[str] = None,
    ) -> str:
        """
        Generate GitHub permalink for file/lines.

        Args:
            file_path: Relative path from repo root (e.g., "agent_orchestrator/main.py")
            line_start: Starting line number (optional)
            line_end: Ending line number (optional)
            commit_sha: Specific commit SHA (defaults to HEAD)

        Returns:
            GitHub permalink URL

        Example:
            >>> generator.generate_permalink("src/main.py", 45, 67)
            'https://github.com/owner/repo/blob/abc123/src/main.py#L45-L67'
        """
        if commit_sha is None:
            commit_sha = self.get_current_commit_sha()

        # Normalize file path (remove leading ./ or /)
        file_path = file_path.lstrip("./").lstrip("/")

        # Build base URL
        url = f"{self.repo_url}/blob/{commit_sha}/{file_path}"

        # Add line numbers
        if line_start is not None:
            if line_end is not None and line_end != line_start:
                url += f"#L{line_start}-L{line_end}"
            else:
                url += f"#L{line_start}"

        logger.debug(f"Generated permalink: {url}")
        return url

    def extract_file_references(self, text: str) -> List[FileReference]:
        """
        Extract file references from task description.

        Patterns matched:
        - "Review agent_orchestrator/main.py"
        - "Check shared/lib/mcp_client.py lines 45-67"
        - "Update config/env/.env.template line 23"
        - "Fix bug in src/app.ts"

        Args:
            text: Task description or markdown text

        Returns:
            List of FileReference objects

        Example:
            >>> refs = generator.extract_file_references("Review main.py lines 45-67")
            >>> refs[0].path
            'main.py'
            >>> refs[0].line_start
            45
        """
        patterns = [
            # "path/to/file.py lines 45-67"
            r"([a-zA-Z0-9_\-./]+\.(?:py|ts|js|tsx|jsx|yaml|yml|json|md|sh|txt|sql|env))\s+lines?\s+(\d+)-(\d+)",
            # "path/to/file.py line 45"
            r"([a-zA-Z0-9_\-./]+\.(?:py|ts|js|tsx|jsx|yaml|yml|json|md|sh|txt|sql|env))\s+line\s+(\d+)",
            # Just "path/to/file.py"
            r"([a-zA-Z0-9_\-./]+\.(?:py|ts|js|tsx|jsx|yaml|yml|json|md|sh|txt|sql|env))(?:\s|$|,|\.|;)",
        ]

        references = []
        seen = set()  # Deduplicate references

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if len(match.groups()) == 3:
                    # Lines range
                    ref = FileReference(
                        path=match.group(1),
                        line_start=int(match.group(2)),
                        line_end=int(match.group(3)),
                    )
                elif len(match.groups()) == 2:
                    # Single line
                    ref = FileReference(
                        path=match.group(1), line_start=int(match.group(2))
                    )
                else:
                    # Just file path
                    ref = FileReference(path=match.group(1))

                # Deduplicate
                ref_key = (ref.path, ref.line_start, ref.line_end)
                if ref_key not in seen:
                    seen.add(ref_key)
                    references.append(ref)

        logger.info(f"Extracted {len(references)} file references from text")
        return references

    def enrich_markdown_with_permalinks(
        self, markdown_text: str, commit_sha: Optional[str] = None
    ) -> str:
        """
        Convert file references in markdown to GitHub permalinks.

        Args:
            markdown_text: Original markdown text with file references
            commit_sha: Specific commit SHA (defaults to HEAD)

        Returns:
            Markdown with file references converted to permalinks

        Example:
            >>> text = "Review agent_orchestrator/main.py lines 45-67"
            >>> generator.enrich_markdown_with_permalinks(text)
            'Review [agent_orchestrator/main.py (L45-L67)](https://github.com/...)'
        """
        if commit_sha is None:
            commit_sha = self.get_current_commit_sha()

        references = self.extract_file_references(markdown_text)
        enriched = markdown_text

        # Sort references by specificity (most specific first)
        # This ensures we replace "file.py lines 45-67" before just "file.py"
        sorted_refs = sorted(
            references, key=lambda r: (r.path, -(r.line_start or 0), -(r.line_end or 0))
        )

        # Build a list of replacements to make
        replacements = []
        paths_replaced = set()  # Track which paths we've already linked

        for ref in sorted_refs:
            permalink = self.generate_permalink(
                ref.path, ref.line_start, ref.line_end, commit_sha
            )

            # Build the exact text to find and replace
            if ref.line_start:
                if ref.line_end and ref.line_end != ref.line_start:
                    # Find "file.py lines 45-67" or "file.py line 45-67"
                    search_text = f"{ref.path} lines {ref.line_start}-{ref.line_end}"
                    alt_search = f"{ref.path} line {ref.line_start}-{ref.line_end}"
                    link_text = f"{ref.path} (L{ref.line_start}-L{ref.line_end})"
                else:
                    # Find "file.py line 45"
                    search_text = f"{ref.path} line {ref.line_start}"
                    alt_search = None
                    link_text = f"{ref.path} (L{ref.line_start})"

                # Mark this path as linked (so we don't link standalone filename later)
                paths_replaced.add(ref.path)
            else:
                # Only link standalone filename if we haven't linked it with line numbers
                if ref.path in paths_replaced:
                    continue  # Skip this reference
                search_text = ref.path
                alt_search = None
                link_text = ref.path
                paths_replaced.add(ref.path)

            markdown_link = f"[{link_text}]({permalink})"
            replacements.append((search_text, alt_search, markdown_link))

        # Apply replacements (most specific first)
        for search_text, alt_search, markdown_link in replacements:
            # Check if this text is already inside a markdown link
            # by checking if it appears between ]( and )
            if f"]({search_text}" in enriched or f"[{search_text}]" in enriched:
                continue

            # Try primary search text
            if search_text in enriched:
                enriched = enriched.replace(search_text, markdown_link, 1)
            # Try alternative if provided
            elif alt_search and alt_search in enriched:
                enriched = enriched.replace(alt_search, markdown_link, 1)

        logger.info(f"Enriched markdown with {len(references)} permalinks")
        return enriched


# Global generator instance
_generator: Optional[GitHubPermalinkGenerator] = None


def init_permalink_generator(repo_url: str, repo_path: str = "."):
    """
    Initialize global permalink generator.

    Args:
        repo_url: GitHub repository URL
        repo_path: Path to local git repository (defaults to current directory)

    Example:
        >>> init_permalink_generator("https://github.com/Appsmithery/Dev-Tools")
    """
    global _generator
    _generator = GitHubPermalinkGenerator(repo_url, repo_path)
    logger.info("Global permalink generator initialized")


def generate_permalink(
    file_path: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    commit_sha: Optional[str] = None,
) -> str:
    """
    Generate permalink using global generator.

    Args:
        file_path: Relative path from repo root
        line_start: Starting line number (optional)
        line_end: Ending line number (optional)
        commit_sha: Specific commit SHA (defaults to HEAD)

    Returns:
        GitHub permalink URL

    Raises:
        RuntimeError: If init_permalink_generator() not called

    Example:
        >>> generate_permalink("agent_orchestrator/main.py", 45, 67)
        'https://github.com/Appsmithery/Dev-Tools/blob/abc123/agent_orchestrator/main.py#L45-L67'
    """
    if _generator is None:
        raise RuntimeError("Call init_permalink_generator() first")
    return _generator.generate_permalink(file_path, line_start, line_end, commit_sha)


def enrich_description_with_permalinks(description: str) -> str:
    """
    Enrich task description with GitHub permalinks.

    Args:
        description: Task description with file references

    Returns:
        Description with file references converted to permalinks

    Raises:
        RuntimeError: If init_permalink_generator() not called

    Example:
        >>> enrich_description_with_permalinks("Review main.py lines 45-67")
        'Review [main.py (L45-L67)](https://github.com/...)'
    """
    if _generator is None:
        raise RuntimeError("Call init_permalink_generator() first")
    return _generator.enrich_markdown_with_permalinks(description)


def extract_file_references(text: str) -> List[FileReference]:
    """
    Extract file references from text using global generator.

    Args:
        text: Text containing file references

    Returns:
        List of FileReference objects

    Raises:
        RuntimeError: If init_permalink_generator() not called
    """
    if _generator is None:
        raise RuntimeError("Call init_permalink_generator() first")
    return _generator.extract_file_references(text)


# ============================================================================
# STATELESS FUNCTIONS (New Workspace-Aware API)
# ============================================================================


def generate_permalink_stateless(
    repo_url: str,
    file_path: str,
    commit_sha: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
) -> str:
    """
    Generate GitHub permalink for any repository (stateless, workspace-aware).

    This is the NEW API for workspace-aware permalink generation.
    No global state, no git operations - just URL construction.

    Args:
        repo_url: GitHub repository URL (e.g., "https://github.com/owner/repo")
        file_path: Relative path from repo root
        commit_sha: Commit SHA (REQUIRED - from extension)
        line_start: Starting line number (optional)
        line_end: Ending line number (optional)

    Returns:
        GitHub permalink URL

    Example:
        >>> generate_permalink_stateless(
        ...     "https://github.com/user/project",
        ...     "src/main.py",
        ...     "abc123def456",
        ...     45,
        ...     67
        ... )
        'https://github.com/user/project/blob/abc123def456/src/main.py#L45-L67'
    """
    # Clean repo URL
    base_url = repo_url.rstrip(".git").rstrip("/")

    # Normalize file path
    file_path = file_path.lstrip("./").lstrip("/")

    # Build permalink
    url = f"{base_url}/blob/{commit_sha}/{file_path}"

    # Add line numbers
    if line_start:
        url += f"#L{line_start}"
        if line_end and line_end != line_start:
            url += f"-L{line_end}"

    logger.debug(f"Generated permalink (stateless): {url}")
    return url


def enrich_markdown_with_permalinks_stateless(
    markdown_text: str, repo_url: str, commit_sha: str
) -> str:
    """
    Enrich markdown with permalinks for any repository (stateless, workspace-aware).

    This is the NEW API for workspace-aware enrichment.
    Creates temporary generator for this specific repo.

    Args:
        markdown_text: Text containing file references
        repo_url: GitHub repository URL
        commit_sha: Commit SHA (REQUIRED - from extension)

    Returns:
        Markdown text with file references converted to links

    Example:
        >>> enrich_markdown_with_permalinks_stateless(
        ...     "Review src/main.py lines 45-67",
        ...     "https://github.com/user/project",
        ...     "abc123def456"
        ... )
        'Review [src/main.py (L45-L67)](https://github.com/user/project/blob/abc123def456/src/main.py#L45-L67)'
    """
    # Create temporary generator for this repo
    generator = GitHubPermalinkGenerator(repo_url, repo_path="/tmp")
    return generator.enrich_markdown_with_permalinks(markdown_text, commit_sha)
    if _generator is None:
        raise RuntimeError("Call init_permalink_generator() first")
    return _generator.extract_file_references(text)
