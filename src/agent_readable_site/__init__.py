"""Inspect and draft machine-readable website metadata."""

from .linter import InspectionError, inspect_site
from .llms import generate_llms_txt, validate_llms_txt

__all__ = ["InspectionError", "generate_llms_txt", "inspect_site", "validate_llms_txt"]
__version__ = "0.1.0"
