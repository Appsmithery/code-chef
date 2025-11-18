"""Compatibility package for modules stored under agents/feature-dev."""

from __future__ import annotations

from pathlib import Path

LEGACY_DIR = Path(__file__).resolve().parent.parent / "feature-dev"
if LEGACY_DIR.is_dir():
    __path__.append(str(LEGACY_DIR))  # type: ignore[name-defined]
