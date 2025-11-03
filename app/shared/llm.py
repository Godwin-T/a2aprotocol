from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from loguru import logger
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from app.llm_client import _build_groq_client, _build_instructor_client
from models.tool_call import ResponseModel


@dataclass
class ConversationResult:
    """Container that exposes the detected intent and final completion."""

    intent: str
    completion: Any


class LLMClient:
    """Async wrapper capable of routing between normal chat and tool flows."""

    def __init__(self) -> None:
        self._block_client = _build_groq_client()
        self._instructor_client = _build_instructor_client()
        self._logger = logger
    async def generate_response(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto"] | str | None = None,
        response_format: dict[str, Any] | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        """Backward-compatible helper that returns the assistant content."""
        completion = await self._block_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format=response_format,
            max_output_tokens=max_output_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )
        return completion.choices[0].message.content or ""

    async def generate_routed_response(
        self,
        *,
        intent_messages: list[dict[str, Any]],
        intent_response_format: dict[str, Any],
        messages: list[dict[str, Any]],
        model: str,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_registry: Mapping[str, Callable[..., Any]] | None = None,
        max_output_tokens: int | None = None,
        log_context: Mapping[str, Any] | None = None,
    ) -> ConversationResult:
        """Determine the flow to use and return the final completion."""
        logger.info(
            "Starting routed conversation",
            message_count=len(messages),
            has_tools=bool(tools),
        )

        intent = await self._determine_intent(
            intent_messages=intent_messages,
            intent_response_format=intent_response_format,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,

        )

        logger.info("Intent classified", intent=intent)

        needs_tools = intent == "tool_call" and tools and tool_registry

        if needs_tools:
            completion = await self._run_tool_flow(
                messages=messages,
                model=model,
                temperature=temperature,
                response_format=response_format,
                tools=tools,
                tool_registry=tool_registry,
                max_output_tokens=max_output_tokens,
            )
        else:
            completion = await self._run_chat_flow(
                messages=messages,
                model=model,
                temperature=temperature,
                response_format=response_format,
                max_output_tokens=max_output_tokens,
                tools=tools if needs_tools else None,
            )

        content_preview = self._preview_text(
            completion.choices[0].message.content or ""
        )
        logger.info("Completed routed conversation", intent=intent, preview=content_preview)
        return ConversationResult(intent=intent, completion=completion)

    async def _determine_intent(
        self,
        *,
        intent_messages: list[dict[str, Any]],
        intent_response_format: dict[str, Any],
        model: str,
        temperature: float,
        max_output_tokens: int | None,
    ) -> str:
        logger.debug("Requesting intent classification", message_count=len(intent_messages))
        completion = await self._block_completion(
            model=model,
            messages=intent_messages,
            temperature=temperature,
            response_format=intent_response_format,
            max_output_tokens=max_output_tokens,
        )
        content = completion.choices[0].message.content or "{}"
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Intent classification returned invalid JSON", preview=self._preview_text(content))
            return "normal_request"
        intent = payload.get("intent")
        if isinstance(intent, str):
            return intent
        logger.warning("Intent classification missing 'intent' field", payload=payload)
        return "normal_request"

    async def _run_chat_flow(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        response_format: dict[str, Any] | None,
        max_output_tokens: int | None,
        tools: list[dict[str, Any]] | None = None,
    ):
        logger.debug(
            "Invoking chat completion",
            message_count=len(messages),
            uses_tools=bool(tools),
        )
        return await self._block_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format=response_format,
            max_output_tokens=max_output_tokens,
            tools=tools,
        )

    async def _run_tool_flow(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
        response_format: dict[str, Any] | None,
        tools: list[dict[str, Any]],
        tool_registry: Mapping[str, Callable[..., Any]],
        max_output_tokens: int | None,
    ):
        logger.info(
            "Planning tool calls",
            available_tools=list(tool_registry.keys()),
            message_count=len(messages),
        )
        plan = await self._plan_tool_calls(
            messages=messages,
            model=model,
            temperature=temperature,
        )

        if not plan.tool_calls:
            logger.info("No tool calls returned; falling back to chat completion")
            return await self._run_chat_flow(
                messages=messages,
                model=model,
                temperature=temperature,
                response_format=response_format,
                max_output_tokens=max_output_tokens,
            )

        augmented_messages = [msg.copy() for msg in messages]
        assistant_tool_calls: list[dict[str, Any]] = []
        tool_messages: list[dict[str, Any]] = []

        planned_tools = [call.tool_name for call in plan.tool_calls]
        logger.info("Tool calls planned", planned_tools=planned_tools)

        for call in plan.tool_calls:
            tool_name = call.tool_name
            tool_fn = tool_registry.get(tool_name)
            if tool_fn is None:
                logger.error("Model requested unknown tool", tool_name=tool_name)
                raise ValueError(f"Unknown tool requested by model: {tool_name}")

            arguments = self._parse_tool_arguments(call.tool_parameters)
            logger.info("Executing tool", tool_name=tool_name, arguments=arguments)
            result = await self._execute_tool(tool_fn, arguments)
            tool_output = self._stringify_tool_output(result)
            logger.info(
                "Tool completed",
                tool_name=tool_name,
                output_preview=self._preview_text(tool_output),
            )
            tool_call_id = str(uuid.uuid4())

            assistant_tool_calls.append(
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(arguments),
                    },
                }
            )
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": tool_output,
                }
            )

        augmented_messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": assistant_tool_calls,
            }
        )
        augmented_messages.extend(tool_messages)

        return await self._run_chat_flow(
            messages=augmented_messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
            max_output_tokens=max_output_tokens,
        )

    async def _block_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        response_format: dict[str, Any] | None,
        max_output_tokens: int | None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["auto"] | str | None = None,
    ):
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        completion = await asyncio.to_thread(
            self._block_client.chat.completions.create,
            **kwargs,
        )
        content = completion.choices[0].message.content or ""
        logger.debug(
            "Chat completion received",
            preview=self._preview_text(content),
        )
        return completion

    async def _plan_tool_calls(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
    ) -> ResponseModel:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_model": ResponseModel,
        }
        plan = await asyncio.to_thread(
            self._instructor_client.chat.completions.create,
            **kwargs,
        )
        logger.debug(
            "Tool plan received",
            call_count=len(plan.tool_calls),
            planned_tools=[call.tool_name for call in plan.tool_calls],
        )
        return plan

    async def _execute_tool(
        self, tool_fn: Callable[..., Any], arguments: dict[str, Any]
    ) -> Any:
        if inspect.iscoroutinefunction(tool_fn):
            return await tool_fn(**arguments)
        result = tool_fn(**arguments)
        if inspect.isawaitable(result):
            return await result
        return result

    @staticmethod
    def _parse_tool_arguments(arguments: str) -> dict[str, Any]:
        if not arguments:
            return {}
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("Tool arguments must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments must decode to an object")
        return parsed

    @staticmethod
    def _stringify_tool_output(value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value)
        except TypeError:
            return str(value)

    @staticmethod
    def _preview_text(text: str, limit: int = 200) -> str:
        if not text:
            return ""
        if len(text) <= limit:
            return text
        return f"{text[:limit]}…"


llm_client = LLMClient()


def json_schema_response(schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "schema": schema,
        },
    }
