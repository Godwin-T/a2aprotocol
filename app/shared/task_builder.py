from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from models.a2a import (
    Artifact,
    A2AMessage,
    MessagePart,
    TaskResult,
    TaskStatus,
)


def build_task_result(
    *,
    message: A2AMessage,
    status_state: str = "completed",
    context_id: Optional[str] = None,
    task_id: Optional[str] = None,
    text_parts: Optional[Iterable[str]] = None,
    data_parts: Optional[Iterable[Dict[str, Any]]] = None,
) -> TaskResult:
    """Create a TaskResult with provided text/data payloads."""

    text_parts = list(text_parts or [])
    data_parts = list(data_parts or [])

    artifact_parts: List[MessagePart] = []

    for text in text_parts:
        artifact_parts.append(MessagePart(kind="text", text=text))

    for data in data_parts:
        artifact_parts.append(MessagePart(kind="data", data=[data]))

    artifact = Artifact(
        name="agent-output",
        parts=artifact_parts or [MessagePart(kind="text", text="")],
    )

    status = TaskStatus(
        state=status_state, timestamp=datetime.utcnow().isoformat()
    )

    return TaskResult(
        id=task_id or str(uuid.uuid4()),
        contextId=context_id or str(uuid.uuid4()),
        status=status,
        artifacts=[artifact],
        history=[message],
    )


def build_error_result(
    *,
    message: A2AMessage,
    error_message: str,
    context_id: Optional[str] = None,
    task_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> TaskResult:
    """Construct a failed TaskResult."""
    error_payload = {"error": error_message}
    if data:
        error_payload["data"] = data

    return build_task_result(
        message=message,
        status_state="failed",
        context_id=context_id,
        task_id=task_id,
        text_parts=[error_message],
        data_parts=[error_payload],
    )
