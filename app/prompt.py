import json
from datetime import datetime
from typing import Optional, List

SYSTEM_PROMPT = """
You are a time conversion agent. Extract the date and time from natural language text. Output valid JSON only, no prose or explanation. 
Format date as 'YYYY-MM-DD' and time as 'h:mm a'. Include IANA timezone names.
"""

time_nl_convert_response_schema = {
    "type": "object",
    "properties": {
        "input_text": {"type": "string"},
        "source": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "time": {"type": "string", "description": "h:mm AM/PM"}
            },
            "required": ["timezone", "date", "time"]
        },
        "targets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "h:mm AM/PM"}
                },
                "required": ["timezone", "date", "time"]
            },
            "minItems": 1
        }
    },
    "required": ["input_text", "source", "targets"],
    "additionalProperties": False
}

def build_interpretation_prompt(
    expression: str,
    timezone: str = "Africa/Lagos",
    targets: Optional[List[str]] = ["America/New_York", "Europe/London", "Asia/Dubai"],
    reference_time: datetime | None = None,
) -> str:

    if reference_time is None:
        reference_now = str(datetime.utcnow())

    messages=[
        {
            "role": "system",
            "content": (SYSTEM_PROMPT)
        },
        {
            "role": "user",
            "content": json.dumps({
                "task": "Convert natural language time to multiple timezones",
                "text": expression,
                "assumed_source_timezone": timezone,
                "targets": targets,
                "reference_now": reference_now,
                "options": {"format": "iso", "include_relative": True}
            })
        }
    ],
    return messages