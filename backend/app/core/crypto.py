import json
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _cipher() -> Fernet:
    settings = get_settings()
    return Fernet(settings.fernet_key.encode("utf-8"))


def encrypt_json(payload: dict[str, Any] | None) -> bytes | None:
    if not payload:
        return None
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _cipher().encrypt(encoded)


def decrypt_json(payload: bytes | None) -> dict[str, Any]:
    if not payload:
        return {}
    decoded = _cipher().decrypt(payload)
    return json.loads(decoded.decode("utf-8"))

