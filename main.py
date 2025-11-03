from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.agents import (
    ScheduleTimeAgent,
)
from app.config import settings
from models.a2a import A2AMessage, JSONRPCRequest, JSONRPCResponse, TaskResult

load_dotenv()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version="2.0.0",
)

schedule_agent = ScheduleTimeAgent(default_timezone=settings.default_timezone)


@app.get("/health")
async def health_check():
    """Health check endpoint listing available agents."""
    return {
        "status": "healthy",
        "agents": [
            "comms-starter",
            "review-polish",
            "summaries-insights",
            "quick-answer",
            "channel-historian",
            "schedule-time",
        ],
    }


@app.post("/a2a/schedule-time")
async def schedule_time_endpoint(request: Request):
    return await _handle_agent_request(request, schedule_agent.handle)


async def _handle_agent_request(request: Request, handler):
    body = await request.json()
    if body.get("jsonrpc") != "2.0" or "id" not in body:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0' and id is required",
                },
            },
        )

    rpc_request = JSONRPCRequest(**body)
    message = _extract_message(rpc_request)
    if message is None:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": rpc_request.id,
                "error": {
                    "code": -32602,
                    "message": "Request missing required message payload.",
                },
            },
        )

    # try:
    result: TaskResult = await handler(
        message,
        context_id=getattr(rpc_request.params, "contextId", None),
        task_id=getattr(rpc_request.params, "taskId", None),
    )
    # except Exception as exc:  # pragma: no cover - defensive
    #     return JSONResponse(
    #         status_code=500,
    #         content={
    #             "jsonrpc": "2.0",
    #             "id": rpc_request.id,
    #             "error": {
    #                 "code": -32603,
    #                 "message": "Internal error",
    #                 "data": {"details": str(exc)},
    #             },
    #         },
    #     )

    response = JSONRPCResponse(id=rpc_request.id, result=result)
    return response.model_dump()


def _extract_message(request_obj: JSONRPCRequest) -> Optional[A2AMessage]:
    params = request_obj.params
    if hasattr(params, "message"):
        return params.message
    if hasattr(params, "messages"):
        messages = params.messages
        if messages:
            return messages[-1]
    return None


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host="0.0.0.0", port=port)
