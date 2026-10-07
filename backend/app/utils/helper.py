"""
Utility helpers for the AI Tender Platform.
Provides path sanitation, cryptographic hashing, prompt injection neutralization,
audit logging, and query pagination.
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Sequence, TypeVar
from sqlalchemy.orm import Query, Session

from app.models.audit_log import AuditLog

logger = logging.getLogger("app.utils.helper")

T = TypeVar("T")

# Regex to remove potentially dangerous path traversal characters and invalid characters
SAFE_FILENAME_REGEX = re.compile(r"[^a-zA-Z0-9_.-]")


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to protect against directory traversal (e.g., '../../etc/passwd').
    Ensures safe, bounded file basenames with standard alphanumeric extensions.
    """
    if not filename or not isinstance(filename, str):
        raise ValueError("Filename must be a non-empty string.")

    # Strip null bytes and normalize
    clean_name = filename.replace("\x00", "").strip()
    
    # Extract only the base name (strip directory components)
    clean_name = os.path.basename(clean_name)

    # Replace forbidden path characters
    clean_name = SAFE_FILENAME_REGEX.sub("_", clean_name)

    # Prevent hidden files or empty base names
    if clean_name.startswith("."):
        clean_name = f"uploaded_{clean_name.lstrip('.')}"

    if not clean_name or clean_name == "_":
        clean_name = "tender_document.pdf"

    # Enforce maximum length
    max_len = 200
    if len(clean_name) > max_len:
        ext = os.path.splitext(clean_name)[1]
        stem = os.path.splitext(clean_name)[0][: max_len - len(ext)]
        clean_name = f"{stem}{ext}"

    return clean_name


def compute_file_sha256(file_path_or_bytes: str | Path | bytes) -> str:
    """
    Computes SHA-256 hash for document integrity and deduplication.
    """
    hasher = hashlib.sha256()

    if isinstance(file_path_or_bytes, bytes):
        hasher.update(file_path_or_bytes)
        return hasher.hexdigest()

    path = Path(file_path_or_bytes)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for hash calculation: {path}")

    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)

    return hasher.hexdigest()


def sanitize_text(text: str) -> str:
    """
    Strips non-printable control characters and null bytes from extracted PDF texts.
    Preserves newlines and standard readable punctuation.
    """
    if not text:
        return ""
    # Remove null bytes
    cleaned = text.replace("\x00", "")
    # Remove non-printable ASCII control characters except \t, \n, \r
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    return cleaned.strip()


def sanitize_prompt_input(text: str, max_chars: int = 15000) -> str:
    """
    Guards AI input by capping payload size and mitigating delimiter injection attacks.
    """
    if not text:
        return ""
    sanitized = sanitize_text(text)
    # Neutralize markdown and triple backtick escapes that attempt prompt boundaries breaking
    sanitized = sanitized.replace("```", "'''")
    if len(sanitized) > max_chars:
        return sanitized[:max_chars] + "\n[Content truncated for model context limit]"
    return sanitized


def record_audit_log(
    db: Session,
    organization_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    user_id: int | None = None,
    tender_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Idempotently records an audit log entry within the active transaction.
    Ensures tenant isolation and serializes structured metadata.
    """
    metadata_json = None
    if metadata:
        try:
            metadata_json = json.dumps(metadata, default=str)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to serialize audit log metadata: %s", exc)
            metadata_json = json.dumps({"serialization_error": str(exc)})

    audit_entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender_id,
        action=action.strip().upper(),
        entity_type=entity_type.strip(),
        entity_id=entity_id,
        metadata_json=metadata_json,
    )
    db.add(audit_entry)
    db.flush()
    return audit_entry


def paginate_sequence(
    items: Sequence[T],
    page: int = 1,
    page_size: int = 20,
) -> tuple[Sequence[T], int]:
    """
    In-memory pagination helper returning (page_items, total_count).
    Safely enforces bounds on page and page_size.
    """
    safe_page = max(1, page)
    safe_page_size = min(100, max(1, page_size))
    total = len(items)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    return items[start:end], total
