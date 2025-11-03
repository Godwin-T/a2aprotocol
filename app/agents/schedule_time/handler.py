import json
from typing import Optional

from app.agents.schedule_time.prompt import (
    USER_INTENT_PROMPT,
    build_interpretation_prompt,
)
from loguru import logger
from app.agents.schedule_time.tools import get_timezone, tools
from app.shared.llm import llm_client, json_schema_response
from app.shared.message_utils import extract_text_parts
from app.shared.profiles import ProfileDirectory
from app.shared.task_builder import build_error_result, build_task_result
from models.a2a import A2AMessage
from models.time_conversion import IntentResponse, TimeNLConvertResponse

DEFAULT_TARGETS = [
    "America/New_York",
    "Europe/London",
    "Asia/Dubai",
]


class ScheduleTimeAgent:
    """LLM-driven time coordination agent."""

    def __init__(
        self,
        *,
        default_timezone: str = "UTC",
        profile_directory: Optional[ProfileDirectory] = None,
        model: str = "openai/gpt-oss-20b",
    ) -> None:
        self.default_timezone = default_timezone
        self.profiles = profile_directory or ProfileDirectory()
        self.model = model
        self._logger = logger

    async def handle(
        self,
        message: A2AMessage,
        *,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ):
        expression = " ".join(extract_text_parts(message)).strip()
        if not expression:
            self._logger.warning("No expression content found in message")
            return build_error_result(
                message=message,
                error_message="No text supplied for time interpretation.",
                context_id=context_id,
                task_id=task_id,
            )

        metadata = message.metadata or {}
        source_timezone = metadata.get("source_timezone", self.default_timezone)
        target_timezones = metadata.get("target_timezones") or DEFAULT_TARGETS
        logger.debug(
            "Resolved metadata defaults",
            source_timezone=source_timezone,
            target_timezones=target_timezones,
        )

        intent_schema = json_schema_response(
            "intent-response",
            IntentResponse.model_json_schema(),
        )
        intent_prompt = USER_INTENT_PROMPT.format(expression=expression)
        interpretation_messages = build_interpretation_prompt(
            expression,
            source_timezone=source_timezone,
            target_timezones=target_timezones,
            tools=tools,
        )

        response_schema = json_schema_response(
            "time-conversion-response",
            TimeNLConvertResponse.model_json_schema(),
        )

        tool_registry = {
            "get_timezone": get_timezone,
        }

        llm_result = await llm_client.generate_routed_response(
            intent_messages=[{"role": "user", "content": intent_prompt}],
            intent_response_format=intent_schema,
            messages=interpretation_messages,
            model=self.model,
            temperature=0.2,
            response_format=response_schema,
            tools=tools,
            tool_registry=tool_registry,
        )
        logger.info("LLM routed response completed", intent=llm_result.intent)

        completion = llm_result.completion
        final_message = completion.choices[0].message
        final_content = final_message.content or ""
        logger.debug("Received final LLM content", preview=final_content[:200])

        try:
            parsed = json.loads(final_content)
        except json.JSONDecodeError as exc:
            logger.exception("Failed to decode LLM JSON response", error=str(exc))
            return build_error_result(
                message=message,
                error_message="Failed to parse time conversion response.",
                context_id=context_id,
                task_id=task_id,
                data={"error": str(exc), "raw": final_content},
            )

        try:
            time_response = TimeNLConvertResponse.model_validate(parsed)
        except Exception as exc:
            logger.exception(
                "LLM response failed validation", error=str(exc), payload=parsed
            )
            return build_error_result(
                message=message,
                error_message="Invalid time conversion received from model.",
                context_id=context_id,
                task_id=task_id,
                data={"error": str(exc), "raw": parsed},
            )
        logger.info(
            "Successfully built time conversion result",
            targets=[target.timezone for target in time_response.targets],
        )
        return build_task_result(
            message=message,
            context_id=context_id,
            task_id=task_id,
            text_parts=[parsed.get("output_text", "")],
            data_parts=[{"time_conversion": time_response.model_dump()}],
        )
