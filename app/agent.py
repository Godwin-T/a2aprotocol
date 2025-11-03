import json
from uuid import uuid4
from typing import Dict, Optional, List, Set
from zoneinfo import ZoneInfo

from app.llm_client import _build_groq_client
from app.prompt import SYSTEM_PROMPT, build_interpretation_prompt
from models.a2a import (
    A2AMessage, TaskResult, TaskStatus, Artifact,
    MessagePart, MessageConfiguration
)
from models.time_conversion import TimeNLConvertResponse

client = _build_groq_client()

class TimeCoordinationAgent:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or client

    async def process_messages(
        self,
        messages: A2AMessage,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        config: Optional[MessageConfiguration] = None
    ) -> TaskResult:
        
        # Generate IDs if not provided
        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())

        # Extract text from message parts
        if isinstance(messages, dict):
            parts = messages.get("parts", [])

        input_texts = [p["text"] for p in parts if p.get("kind") == "text" and p.get("text")]
        if not input_texts:
            raise ValueError("No text parts found in the message.")

        input_text = " ".join(input_texts)

        # Build prompt for time conversion
        prompt = build_interpretation_prompt(input_text)[0]

        # Call LLM to get time conversions
        response = self.llm_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages= prompt,
            response_format={
                "type": "json_schema",
                "json_schema": {"name":"time-conversion-response", "schema": TimeNLConvertResponse.model_json_schema()},
            }
        )
        response = json.loads(response.choices[0].message.content)
        try:
            response = TimeNLConvertResponse(**response)
        except Exception as e:
            raise ValueError(f"Failed to parse LLM response: {e}")

        response = response.model_dump()

        # Build response message parts
        artifact_parts = [
            MessagePart(
                kind="data",
                data=[{
                    "time_conversion": response
                }]
            )
        ]
        message_parts = [
            MessagePart(
                kind="text",
                text= f"Time conversion completed successfully. {response['output_text']}"
                                                
            )
        ]

        # Build task result
        task_result = TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="completed", 
                              message=A2AMessage(
                                  role="agent",
                                  parts=message_parts)),
            artifacts=[
                Artifact(
                    name="time-conversion-response",
                    parts=artifact_parts
                )
            ],
            history=[messages]
        )

        return task_result