import json
from datetime import datetime
from typing import Optional, List

SYSTEM_PROMPT = """
You are a time conversion agent. Extract the date and time from natural language text. Output valid JSON only, no prose or explanation. 
Format date as 'YYYY-MM-DD' and time as 'h:mm a'. Include IANA timezone names.
"""

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