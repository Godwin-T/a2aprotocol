# A2A Productivity Agents Service

FastAPI service exposing multiple Agent-to-Agent (A2A) endpoints for common productivity workflows. Each endpoint accepts JSON-RPC 2.0 payloads that comply with the `models/a2a.py` schema and returns structured `TaskResult` artifacts ready for orchestration with other agents.

---

## Available Agents

| Endpoint | Purpose |
|----------|---------|
| `POST /a2a/comms-starter` | Feeds briefs to a Groq-hosted LLM that drafts announcements, icebreakers, and feature blurbs. |
| `POST /a2a/review-polish` | Uses an LLM editor to proofread, rewrite, or translate copy (any language supported by the model). |
| `POST /a2a/summaries-insights` | Summarises long-form text, surfaces key points, and extracts action items via structured LLM output. |
| `POST /a2a/quick-answer` | Answers FAQs from cached data or escalates to an LLM for free-form questions. |
| `POST /a2a/channel-historian` | Sends channel snapshots to an LLM which highlights topics, decisions, and experts. |
| `POST /a2a/schedule-time` | Upgraded time agent powered by an LLM prompt that returns conversions, meeting windows, and natural replies; still supports current-time lookups deterministically. |

All endpoints return a JSON-RPC response shaped exactly like the original time agent, so downstream consumers require no protocol changes. Every agent call ultimately routes through the Groq chat completion API using carefully crafted prompts and JSON schemas.

---

## Project Layout

```
.
├── main.py                         # FastAPI app registering all agent routes
├── app/
│   ├── agents/
│   │   ├── channel_historian/      # Channel Historian agent implementation
│   │   ├── comms_starter/          # Comms Starter agent implementation
│   │   ├── quick_answer/           # Quick Answer Desk agent implementation
│   │   ├── review_polish/          # Review & Polish agent implementation
│   │   ├── schedule_time/          # Upgraded Schedule & Time agent
│   │   └── summaries_insights/     # Summaries & Insights agent
│   ├── shared/                     # Reusable helpers (message parsing, task builder, etc.)
│   ├── config.py                   # Pydantic settings loader
│   └── __init__.py
├── models/                         # JSON-RPC and time conversion schemas (unchanged)
├── data/channel_snapshots/         # Optional offline data for the historian agent
├── data/faq.json                   # Optional FAQ cache for quick answers
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## JSON-RPC Payload Example

```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "metadata": {
        "tone": "friendly",
        "audience": "team"
      },
      "parts": [
        {
          "kind": "text",
          "text": "We shipped timeline filtering for dashboards. Mention that it unlocks faster insights."
        }
      ]
    }
  }
}
```

POST the payload to `http://localhost:5001/a2a/comms-starter`. The response body keeps the JSON-RPC envelope and embeds the generated announcement inside the first artifact.

---

## Local Development

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) 3. Provide supporting data
mkdir -p data/channel_snapshots/general
echo "[]" > data/faq.json

# 4. Run the API
uvicorn main:app --host 0.0.0.0 --port 5001 --reload
```

Smoke test the health endpoint:

```bash
curl -s http://localhost:5001/health | jq
```

Send a request to an agent (example: upgraded schedule agent):

```bash
curl -s http://localhost:5001/a2a/schedule-time \
  -H "Content-Type: application/json" \
  -d @examples/schedule-request.json | jq
```

---

## Docker Usage

```bash
docker build -t a2a-agents .

# Default container listens on port 8000 inside the container
docker run --rm -p 8000:8000 a2a-agents
```

Endpoints are reachable at `http://localhost:8000/a2a/...`.

To mount offline assets (e.g., channel snapshots or FAQ JSON), bind them at runtime:

```bash
docker run --rm \
  -v $PWD/data:/app/data \
  -p 8000:8000 \
  a2a-agents
```

---

## Configuration & Data Inputs

| Setting | Description | Default |
|---------|-------------|---------|
| `APP_NAME` | FastAPI title | `Global Time Coordination Agent` |
| `APP_DESCRIPTION` | FastAPI description | `An agent that coordinates time-related tasks across multiple agents.` |
| `DEFAULT_TIMEZONE` | Default source timezone for Schedule & Time agent | `UTC` |
| `GROQ_API_KEY` | **Required** API key for Groq chat completions (all agents rely on LLM calls) | *(none)* |
| `FAQ_PATH` | Absolute/relative path to FAQ JSON file for Quick Answer agent | `data/faq.json` |
| `PROFILE_CSV` | Future use: path to user timezone directory CSV | *(none)* |

> ⚠️ All agents call Groq's `chat.completions.create` endpoint under the hood. Set `GROQ_API_KEY` in your environment (or `.env`) before invoking them.

### Optional Data Formats

- `data/faq.json`: array of `{ "question": "...", "answer": "...", "source": "..." }`.
- `data/channel_snapshots/<channel>/*.jsonl`: newline-delimited JSON objects `{ "user": "alice", "text": "message", "ts": "2024-05-01T10:30:00Z" }`.

---

## Testing

Unit and integration tests can be wired using pytest. Suggested layout:

```
tests/
├── test_comms_starter.py
├── test_review_polish.py
├── test_summaries_insights.py
├── test_quick_answer.py
├── test_channel_historian.py
└── test_schedule_time.py
```

Because each agent handler is asynchronous and returns a `TaskResult`, tests can instantiate the handler and feed synthetic `A2AMessage` objects without spinning up FastAPI.

---

## Extending the Service

- Swap to a different LLM by overriding the `model` parameter when instantiating each agent.
- Enhance the Channel Historian ingestion script (`scripts/`) to talk to Slack or Teams APIs and refresh snapshots on a schedule.
- Expand Schedule & Time profile loading using `app/shared/profiles.py` when you have a definitive user timezone directory.

---

## Troubleshooting

- `Invalid Request: jsonrpc must be '2.0' and id is required` – ensure the outer request follows JSON-RPC 2.0.
- `No snapshots found for channel` – ingest history into `data/channel_snapshots/<channel>/` before calling the historian endpoint.
- FAQ lookups returning the fallback – populate `data/faq.json` with the expected questions.

---

Built for multi-agent productivity workflows while keeping the canonical A2A schema intact.
