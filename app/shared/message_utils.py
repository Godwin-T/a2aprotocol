from __future__ import annotations

from typing import List

from models.a2a import A2AMessage


def extract_text_parts(message: A2AMessage) -> List[str]:
    """Return all text payloads from an A2A message."""
    texts: List[str] = []
    for part in message.parts:
        if part.kind == "text" and part.text:
            texts.append(part.text.strip())
    return texts


def get_metadata_value(message: A2AMessage, key: str, default=None):
    """Fetch a metadata field from a message safely."""
    metadata = message.metadata or {}
    return metadata.get(key, default)
