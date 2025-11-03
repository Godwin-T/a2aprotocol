# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
from app.agent import TimeCoordinationAgent
from app.config import settings
from models.a2a import JSONRPCRequest, JSONRPCResponse, TaskResult, TaskStatus, Artifact, MessagePart, A2AMessage

load_dotenv()


# Initialize agent
# agent = None

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Lifespan context manager for startup and shutdown"""
#     global agent

#     # Startup: Initialize agent
#     agent = TimeCoordinationAgent()
#     yield

#     # Shutdown: Cleanup
#     if agent:
#         await agent.cleanup()

agent = TimeCoordinationAgent()
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version="1.0.0",
    # lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "time-coordination"}

@app.post("/a2a/time-coordinate")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint for time-coordination agent"""
    # try:
    # Parse request body
    body = await request.json()

    # Validate JSON-RPC request
    if body.get("jsonrpc") != "2.0" or "id" not in body:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0' and id is required"
                }
            }
        )

    rpc_request = JSONRPCRequest(**body)

    # Extract messages
    messages = []
    context_id = None
    task_id = None
    config = None

    message = rpc_request.params.message
    message = message.model_dump()
    # Process with time-coordination agent
    result = await agent.process_messages(
        messages=message,
        context_id=context_id,
        task_id=task_id,
        config=config
    )
    print(result)

    # Build response
    response = JSONRPCResponse(
        id=rpc_request.id,
        result=result
    )

    return response.model_dump()

    # except Exception as e:
    #     return JSONResponse(
    #         status_code=500,
    #         content={
    #             "jsonrpc": "2.0",
    #             "id": body.get("id") if "body" in locals() else None,
    #             "error": {
    #                 "code": -32603,
    #                 "message": "Internal error",
    #                 "data": {"details": str(e)}
    #             }
    #         }
    #     )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host="0.0.0.0", port=port)
