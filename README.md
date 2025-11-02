# Global Time Coordination A2A Agent

FastAPI-based Agent-to-Agent (A2A) service that interprets natural language time expressions and returns structured conversions across multiple time zones. The agent exposes a JSON-RPC 2.0 compliant interface tailored for time-coordination scenarios where one agent requests temporal context from another.

---

## Key Capabilities
- Accepts `message/send` and `execute` style JSON-RPC payloads defined by the Anthropic A2A schema.
- Interprets incoming message parts, extracting free-form text that describes a time or scheduling intent.
- Calls a Groq-hosted large language model (`openai/gpt-oss-20b`) with a constrained JSON schema to convert the text into normalized timestamps.
- Returns a `TaskResult` artifact containing the original understanding plus conversions into multiple target time zones.
- Ships with a lightweight health probe for orchestration environments.

---

## Project Layout
```
.
├── main.py                  # FastAPI application with JSON-RPC endpoint wiring
├── app/
│   ├── agent.py             # TimeCoordinationAgent orchestrating message parsing and LLM calls
│   ├── config.py            # Pydantic settings loader (.env support)
│   ├── llm_client.py        # Groq SDK client factory
│   └── prompt.py            # System prompt & prompt builder for time conversion tasks
├── models/
│   ├── a2a.py               # JSON-RPC, A2A message, artifact, and task models
│   └── time_conversion.py   # Structured response schema returned by the agent
├── Dockerfile               # Container definition (uvicorn entrypoint, override command as needed)
├── requirements.txt         # Python dependencies
└── README.md                # This document
```

---

## Request Lifecycle
1. **Ingress (FastAPI)** – `POST /a2a/time-coordinate` receives the JSON-RPC payload, validates basic protocol fields, and instantiates `JSONRPCRequest`.
2. **Message Interpretation** – `TimeCoordinationAgent.process_messages` pulls `text` parts out of the A2A message and builds a deterministic LLM prompt.
3. **LLM Invocation** – `Groq` client issues a `chat.completions.create` call enforcing the `TimeNLConvertResponse` JSON schema.
4. **Task Packaging** – The normalized result is wrapped in a `TaskResult` with artifacts and history that comply with the downstream A2A expectations.
5. **Response** – FastAPI serializes the `JSONRPCResponse` back to the caller. Errors are surfaced with standard JSON-RPC error objects.

---

## API Surface
- `GET /health` &rarr; Lightweight readiness probe.
- `POST /a2a/time-coordinate` &rarr; Main JSON-RPC entrypoint.

Example request payload:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Let's meet next Tuesday at 2pm in Lagos."
        }
      ]
    }
  }
}
```

Example success response (abridged):
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "id": "3b4b77d8-6b7d-4c36-9b82-67c345c8992d",
    "contextId": "dd58e58a-f08b-4d58-8356-1690a940cb11",
    "status": {
      "state": "completed",
      "timestamp": "2024-05-22T14:02:11.582Z"
    },
    "artifacts": [
      {
        "name": "time-conversion-response",
        "parts": [
          {
            "kind": "data",
            "data": {
              "time_conversion": {
                "input_text": "Let's meet next Tuesday at 2pm in Lagos.",
                "source": {
                  "timezone": "Africa/Lagos",
                  "date": "2024-05-28",
                  "time": "2:00 PM"
                },
                "targets": [
                  {
                    "timezone": "America/New_York",
                    "date": "2024-05-28",
                    "time": "9:00 AM"
                  }
                ]
              }
            }
          }
        ]
      }
    ]
  }
}
```

---

## Configuration
The service reads settings from environment variables or a `.env` file (via `pydantic-settings`):

| Variable         | Purpose                                           | Default                |
|------------------|---------------------------------------------------|------------------------|
| `APP_NAME`       | Overrides the FastAPI title                       | `Global Time Coordination Agent` |
| `APP_DESCRIPTION`| Overrides the FastAPI description                 | `An agent that coordinates...`   |
| `GROQ_API_KEY`   | **Required** Groq API key for hosted LLM access   | `None`                 |
| `GROQ_MODEL`     | Groq model identifier                             | `mixtral-8x7b-32768`   |

Add any secrets to `.env` (never commit real keys):
```bash
cp .env.example .env  # if you maintain a template
echo "GROQ_API_KEY=sk-..." >> .env
```

---

## Run Locally (Python)
```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Provide environment (either export vars or create .env)
export GROQ_API_KEY=sk-your-key

# 4. Start the API (default port 5001 as defined in main.py)
uvicorn main:app --host 0.0.0.0 --port 5001 --reload
```
Health-check:
```bash
curl -s http://localhost:5001/health | jq
```

Send a sample JSON-RPC request:
```bash
curl -s http://localhost:5001/a2a/time-coordinate \
  -H "Content-Type: application/json" \
  -d @examples/sample-request.json | jq
```
*(Create `examples/sample-request.json` with the payload above.)*

---

## Run with Docker
> The provided Dockerfile installs dependencies under `/app` and exposes port `8000`. Because the application entrypoint lives in `main.py`, override the command to point uvicorn at `main:app`.

```bash
# Build the image
docker build -t time-coordination-agent .

# Run the container (maps host port 8000 -> service port 5001)
docker run --rm \
  --env GROQ_API_KEY=sk-your-key \
  -p 8000:5001 \
  time-coordination-agent \
  uvicorn main:app --host 0.0.0.0 --port 5001
```

Then visit `http://localhost:8000/health`.

---

## Extending the Agent
- **Additional targets** – Update `app/prompt.py` `targets` default list to include more time zones.
- **Alternate LLMs** – Swap the `model` argument or implement a new client factory in `app/llm_client.py`.
- **New artifacts** – Modify `app/agent.py` to attach extra `MessagePart` data (e.g., calendar links).
- **Stateful context** – Use the optional `context_id` and `task_id` parameters to maintain multi-turn workflows.

---

## Troubleshooting
- `401 Unauthorized` from Groq &rarr; ensure `GROQ_API_KEY` is set in your environment or `.env`.
- JSON-RPC errors with code `-32600` &rarr; the payload is missing the `"jsonrpc": "2.0"` header or an `id`.
- Empty `parts` array &rarr; the agent requires at least one `text` message part; include user input under `parts[].text`.

---

## Licensing
No explicit license file is bundled. Confirm licensing requirements before distributing or deploying externally.
