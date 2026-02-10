"""Encode/decode Python values to/from Firestore REST API 'fields' format."""

from datetime import datetime
from typing import Any


def _encode_value(v: Any) -> dict:
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, datetime):
        return {"timestampValue": v.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, bytes):
        import base64

        return {"bytesValue": base64.standard_b64encode(v).decode("ascii")}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_encode_value(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _encode_value(x) for k, x in v.items()}}}
    raise TypeError(f"Unsupported Firestore value type: {type(v)}")


def encode_document(data: dict[str, Any]) -> dict:
    """Convert a Python dict to Firestore REST Document.fields format."""
    return {"fields": {k: _encode_value(v) for k, v in data.items()}}


def _decode_value(obj: dict) -> Any:
    if "nullValue" in obj:
        return None
    if "booleanValue" in obj:
        return obj["booleanValue"]
    if "integerValue" in obj:
        return int(obj["integerValue"])
    if "doubleValue" in obj:
        return obj["doubleValue"]
    if "timestampValue" in obj:
        return datetime.fromisoformat(obj["timestampValue"].replace("Z", "+00:00"))
    if "stringValue" in obj:
        return obj["stringValue"]
    if "bytesValue" in obj:
        import base64

        return base64.standard_b64decode(obj["bytesValue"])
    if "arrayValue" in obj:
        vals = obj.get("arrayValue", {}).get("values") or []
        return [_decode_value(x) for x in vals]
    if "mapValue" in obj:
        fields = obj["mapValue"].get("fields") or {}
        return {k: _decode_value(x) for k, x in fields.items()}
    return None


def decode_document(fields: dict | None) -> dict:
    """Convert Firestore REST Document.fields to a Python dict."""
    if not fields:
        return {}
    return {k: _decode_value(v) for k, v in fields.get("fields", {}).items()}
