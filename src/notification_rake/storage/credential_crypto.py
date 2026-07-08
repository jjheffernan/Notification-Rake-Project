"""Encrypt connected-account config at rest (Fernet envelope in JSONB)."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

_ENVELOPE_KEY = "__enc"
_SECRET_NAME_PARTS = ("password", "token", "secret", "api_key")


def _fernet_key(secret: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def _fernet() -> Fernet:
    from notification_rake.config import settings

    raw = settings.credential_encryption_key.strip()
    if raw:
        return Fernet(_fernet_key(raw))
    if settings.rake_env.lower() != "production":
        return Fernet(_fernet_key(settings.dashboard_secret_key))
    raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY required when RAKE_ENV=production")


def encrypt_config(config: dict[str, Any]) -> dict[str, Any]:
    if not config:
        return {}
    token = _fernet().encrypt(json.dumps(config, separators=(",", ":")).encode())
    return {_ENVELOPE_KEY: token.decode()}


def decrypt_config(stored: dict[str, Any]) -> dict[str, Any]:
    if not stored:
        return {}
    enc = stored.get(_ENVELOPE_KEY)
    if not enc:
        return dict(stored)
    try:
        plain = _fernet().decrypt(enc.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("connected account config could not be decrypted") from exc
    return json.loads(plain)


def is_encrypted(stored: dict[str, Any]) -> bool:
    return bool(stored.get(_ENVELOPE_KEY))


def mask_config(config: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in config.items():
        if any(part in key.lower() for part in _SECRET_NAME_PARTS):
            out[key] = "***" if value else ""
        elif isinstance(value, dict):
            out[key] = mask_config(value)
        else:
            out[key] = value
    return out
