"""Utilities module."""

from __future__ import annotations

from base64 import b64decode, b64encode
import json

ENCODING = "utf-8"


def decode(value: str) -> str:
    """Decode a value."""
    return b64decode(value).decode(ENCODING)


def encode(value: str | dict) -> str:
    """Encode a value."""
    if isinstance(value, dict):
        value = json.dumps(value)
    return b64encode(value.encode(ENCODING)).decode(ENCODING)


class PlantaError(Exception):
    """Generic Planta error."""


class UnauthorizedError(PlantaError):
    """Unauthorized error."""
