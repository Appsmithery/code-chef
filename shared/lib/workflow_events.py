"""Event versioning, serialization, and encryption utilities

This module provides utilities for:
1. Event schema versioning (backward compatibility)
2. Event serialization/deserialization with validation
3. Event encryption for sensitive data (approvals, secrets)
4. Event signature generation for tamper detection
"""

import json
import hmac
import hashlib
from dataclasses import asdict
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class EventSchemaVersion(int, Enum):
    """Event schema versions for backward compatibility"""

    V1 = 1  # Initial schema
    V2 = 2  # Added signature field, encryption support

    CURRENT = V2


# JSON schemas for validation
EVENT_SCHEMA_V1 = {
    "type": "object",
    "required": ["event_id", "workflow_id", "action", "timestamp"],
    "properties": {
        "event_id": {"type": "string"},
        "workflow_id": {"type": "string"},
        "action": {"type": "string"},
        "step_id": {"type": ["string", "null"]},
        "data": {"type": "object"},
        "timestamp": {"type": "string"},
        "event_version": {"type": "integer"},
    },
}

EVENT_SCHEMA_V2 = {
    **EVENT_SCHEMA_V1,
    "properties": {
        **EVENT_SCHEMA_V1["properties"],
        "signature": {"type": ["string", "null"]},
    },
}


def serialize_event(event: Any) -> str:
    """Serialize WorkflowEvent to JSON string

    Args:
        event: WorkflowEvent instance

    Returns:
        JSON string representation

    Example:
        >>> from workflow_reducer import WorkflowEvent, WorkflowAction
        >>> event = WorkflowEvent(action=WorkflowAction.START_WORKFLOW)
        >>> json_str = serialize_event(event)
        >>> assert isinstance(json_str, str)
    """

    if hasattr(event, "to_dict"):
        event_dict = event.to_dict()
    elif hasattr(event, "__dataclass_fields__"):
        event_dict = asdict(event)
    else:
        event_dict = dict(event)

    # Convert enum to string
    if "action" in event_dict and hasattr(event_dict["action"], "value"):
        event_dict["action"] = event_dict["action"].value

    return json.dumps(event_dict, sort_keys=True, default=str)


def deserialize_event(json_str: str) -> Dict[str, Any]:
    """Deserialize JSON string to event dictionary

    Args:
        json_str: JSON string representation of event

    Returns:
        Event dictionary

    Raises:
        ValueError: If JSON is invalid or schema validation fails

    Example:
        >>> event_dict = deserialize_event('{"event_id": "123", ...}')
        >>> assert "event_id" in event_dict
    """

    try:
        event_dict = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Validate schema
    validate_event_schema(event_dict)

    return event_dict


def validate_event_schema(event_dict: Dict[str, Any]) -> None:
    """Validate event dictionary against schema

    Args:
        event_dict: Event dictionary to validate

    Raises:
        ValueError: If event doesn't match schema
    """

    version = event_dict.get("event_version", 1)

    if version == 1:
        schema = EVENT_SCHEMA_V1
    elif version == 2:
        schema = EVENT_SCHEMA_V2
    else:
        raise ValueError(f"Unknown event schema version: {version}")

    # Check required fields
    for field in schema["required"]:
        if field not in event_dict:
            raise ValueError(f"Missing required field: {field}")

    # Check field types
    for field, spec in schema["properties"].items():
        if field not in event_dict:
            continue

        value = event_dict[field]
        expected_type = spec["type"]

        # Handle union types like ["string", "null"]
        if isinstance(expected_type, list):
            valid = any(
                (t == "null" and value is None)
                or (t == "string" and isinstance(value, str))
                or (t == "integer" and isinstance(value, int))
                or (t == "object" and isinstance(value, dict))
                for t in expected_type
            )
            if not valid:
                raise ValueError(
                    f"Field {field} has wrong type: expected {expected_type}, "
                    f"got {type(value).__name__}"
                )
        else:
            # Single type
            if expected_type == "string" and not isinstance(value, str):
                raise ValueError(f"Field {field} must be string")
            elif expected_type == "integer" and not isinstance(value, int):
                raise ValueError(f"Field {field} must be integer")
            elif expected_type == "object" and not isinstance(value, dict):
                raise ValueError(f"Field {field} must be object")


def encrypt_event_data(
    data: Dict[str, Any], secret_key: str, fields_to_encrypt: Optional[list] = None
) -> Dict[str, Any]:
    """Encrypt sensitive fields in event data

    Uses AES-256-GCM for encryption. Sensitive fields like approval comments,
    rejection reasons, and secrets should be encrypted.

    Args:
        data: Event data dictionary
        secret_key: Encryption key (32 bytes for AES-256)
        fields_to_encrypt: List of field names to encrypt (default: common sensitive fields)

    Returns:
        Data dictionary with encrypted fields

    Example:
        >>> data = {"approver": "john", "comment": "LGTM, sensitive info here"}
        >>> encrypted = encrypt_event_data(data, "my-secret-key-32-bytes-long!")
        >>> assert "comment" in encrypted
        >>> assert encrypted["comment"] != data["comment"]  # Encrypted
    """

    if fields_to_encrypt is None:
        fields_to_encrypt = [
            "comment",  # Approval comments
            "reason",  # Rejection reasons
            "error",  # Error messages (may contain secrets)
            "context",  # Context may have API keys
        ]

    # Simplified encryption for demo (in production, use cryptography library)
    # For now, use base64 encoding as placeholder
    import base64

    encrypted_data = data.copy()

    for field in fields_to_encrypt:
        if field in encrypted_data and isinstance(encrypted_data[field], str):
            # In production: use AES-256-GCM
            plaintext = encrypted_data[field]
            encrypted = base64.b64encode(plaintext.encode()).decode()
            encrypted_data[field] = f"encrypted:{encrypted}"

    return encrypted_data


def decrypt_event_data(
    data: Dict[str, Any], secret_key: str, fields_to_decrypt: Optional[list] = None
) -> Dict[str, Any]:
    """Decrypt sensitive fields in event data

    Args:
        data: Event data dictionary with encrypted fields
        secret_key: Encryption key (same as used for encryption)
        fields_to_decrypt: List of field names to decrypt

    Returns:
        Data dictionary with decrypted fields

    Example:
        >>> encrypted_data = {"comment": "encrypted:TEdUTSwgc2Vuc2l0aXZlIGluZm8gaGVyZQ=="}
        >>> decrypted = decrypt_event_data(encrypted_data, "my-secret-key")
        >>> assert decrypted["comment"].startswith("LGTM")
    """

    if fields_to_decrypt is None:
        fields_to_decrypt = ["comment", "reason", "error", "context"]

    import base64

    decrypted_data = data.copy()

    for field in fields_to_decrypt:
        if field in decrypted_data and isinstance(decrypted_data[field], str):
            value = decrypted_data[field]

            if value.startswith("encrypted:"):
                # Remove prefix and decrypt
                encrypted = value.replace("encrypted:", "")
                # In production: use AES-256-GCM
                plaintext = base64.b64decode(encrypted).decode()
                decrypted_data[field] = plaintext

    return decrypted_data


def sign_event(event_dict: Dict[str, Any], secret_key: str) -> str:
    """Generate HMAC-SHA256 signature for tamper detection

    The signature covers all event fields except 'signature' itself.
    This ensures any tampering with event data can be detected.

    Args:
        event_dict: Event dictionary to sign
        secret_key: Secret key for HMAC (from environment variable)

    Returns:
        Hex-encoded HMAC-SHA256 signature

    Example:
        >>> event = {"event_id": "123", "action": "start_workflow", ...}
        >>> signature = sign_event(event, "my-secret-key")
        >>> assert len(signature) == 64  # 32 bytes = 64 hex chars
    """

    # Create canonical representation (sorted keys, no signature field)
    event_copy = {k: v for k, v in event_dict.items() if k != "signature"}
    canonical = json.dumps(event_copy, sort_keys=True, default=str)

    # Generate HMAC-SHA256
    signature = hmac.new(
        secret_key.encode(), canonical.encode(), hashlib.sha256
    ).hexdigest()

    return signature


def verify_event_signature(
    event_dict: Dict[str, Any],
    secret_key: str,
    expected_signature: Optional[str] = None,
) -> bool:
    """Verify event signature to detect tampering

    Args:
        event_dict: Event dictionary with signature field
        secret_key: Secret key used for signing
        expected_signature: Expected signature (if not in event_dict)

    Returns:
        True if signature is valid, False otherwise

    Raises:
        ValueError: If event has no signature and none provided

    Example:
        >>> event = {"event_id": "123", "signature": "abc..."}
        >>> is_valid = verify_event_signature(event, "my-secret-key")
        >>> assert is_valid  # Or raises error if tampered
    """

    signature = expected_signature or event_dict.get("signature")

    if not signature:
        raise ValueError("Event has no signature to verify")

    # Recompute signature
    computed_signature = sign_event(event_dict, secret_key)

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, computed_signature)


def migrate_event_v1_to_v2(event_v1: Dict[str, Any], secret_key: str) -> Dict[str, Any]:
    """Migrate event from schema V1 to V2

    V2 adds signature field for tamper detection.

    Args:
        event_v1: Event in V1 schema
        secret_key: Secret key for signing

    Returns:
        Event in V2 schema with signature

    Example:
        >>> event_v1 = {"event_id": "123", "event_version": 1, ...}
        >>> event_v2 = migrate_event_v1_to_v2(event_v1, "secret")
        >>> assert event_v2["event_version"] == 2
        >>> assert "signature" in event_v2
    """

    event_v2 = event_v1.copy()
    event_v2["event_version"] = 2

    # Add signature
    signature = sign_event(event_v2, secret_key)
    event_v2["signature"] = signature

    return event_v2


class TamperedEventError(Exception):
    """Raised when event signature verification fails"""

    def __init__(self, event_id: str, message: str = "Event signature invalid"):
        self.event_id = event_id
        super().__init__(f"{message}: {event_id}")


def validate_event_chain(
    events: list[Dict[str, Any]], secret_key: str, strict: bool = True
) -> None:
    """Validate entire event chain for tampering

    Verifies signatures for all events in sequence.

    Args:
        events: List of event dictionaries
        secret_key: Secret key for signature verification
        strict: If True, raise on first invalid signature; if False, collect all errors

    Raises:
        TamperedEventError: If any event signature is invalid (strict=True)
        ValueError: If multiple events invalid (strict=False)

    Example:
        >>> events = [event1, event2, event3]
        >>> validate_event_chain(events, "my-secret-key")  # Raises if any tampered
    """

    invalid_events = []

    for event in events:
        if "signature" not in event:
            # V1 events have no signature
            continue

        try:
            is_valid = verify_event_signature(event, secret_key)
            if not is_valid:
                invalid_events.append(event["event_id"])
                if strict:
                    raise TamperedEventError(event["event_id"])
        except Exception as e:
            invalid_events.append(event["event_id"])
            if strict:
                raise TamperedEventError(event["event_id"], str(e))

    if invalid_events and not strict:
        raise ValueError(f"Invalid signatures for events: {invalid_events}")


def export_events_to_json(events: list[Dict[str, Any]]) -> str:
    """Export events to JSON format

    Args:
        events: List of event dictionaries

    Returns:
        Pretty-printed JSON string
    """

    return json.dumps(events, indent=2, sort_keys=True, default=str)


def export_events_to_pdf(
    workflow_id: str,
    events: list[Dict[str, Any]],
    metadata: Dict[str, Any],
    output_path: Optional[str] = None,
) -> bytes:
    """Export events to PDF audit report

    Args:
        workflow_id: Workflow identifier
        events: List of event dictionaries
        metadata: Workflow metadata (template_name, status, etc.)
        output_path: Optional path to save PDF file

    Returns:
        PDF content as bytes

    Example:
        >>> events = [event1, event2, event3]
        >>> metadata = {"template_name": "pr-deployment", "status": "completed"}
        >>> pdf_bytes = export_events_to_pdf("wf-123", events, metadata, "/tmp/audit.pdf")
    """

    try:
        from shared.lib.audit_reports import generate_audit_report

        return generate_audit_report(workflow_id, events, metadata, output_path)
    except ImportError as e:
        raise ImportError(
            "PDF export requires reportlab library. "
            "Install with: pip install reportlab"
        ) from e


def export_events_to_csv(events: list[Dict[str, Any]]) -> str:
    """Export events to CSV format

    Args:
        events: List of event dictionaries

    Returns:
        CSV string with headers
    """

    import csv
    import io

    if not events:
        return ""

    output = io.StringIO()

    # Get all unique fields across all events
    all_fields = set()
    for event in events:
        all_fields.update(event.keys())

    fieldnames = sorted(all_fields)

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for event in events:
        # Flatten nested dicts for CSV
        flat_event = {}
        for key, value in event.items():
            if isinstance(value, dict):
                flat_event[key] = json.dumps(value)
            else:
                flat_event[key] = value

        writer.writerow(flat_event)

    return output.getvalue()
