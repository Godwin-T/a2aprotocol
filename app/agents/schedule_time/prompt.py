import json
from datetime import datetime
from typing import Iterable, List, Optional

# SYSTEM_PROMPT = """
# You are a time conversion agent. Extract the date and time from natural language text.
# Always respond with valid JSON only, no prose or explanation.
# Format date as 'YYYY-MM-DD' and time as 'h:mm a'. Include IANA timezone names.
# """

SYSTEM_PROMPT = """
You are a time conversion agent and a Slack ID time zone assistant.
1. Extract the date and time from natural language text and convert it across multiple time zones.
   Always respond with valid JSON only, no prose or explanation.
   - Format date as 'YYYY-MM-DD' and time as 'h:mm a'.
   - Include IANA timezone names (e.g., 'America/New_York').
   
2. If asked for the time zone of a specific Slack ID, Use the get_timezone function to return the corresponding time zone.
   - The Slack ID is provided in the format: 'U12345678'.
   - Look up the Slack ID from the internal table of Slack IDs and time zones with the get_timezone function.
   - If the Slack ID is found, return the associated time zone. If not, return 'Slack ID not found'.

3. Do not generate any unnecessary explanation; only return the requested data in JSON format.
"""

# USER_PROMPT = """
# Convert the following natural language time expression into structured time data:

# INPUT:
# {expression} - The input natural language time expression.
# {source_timezone} - The assumed source timezone for the input expression.
# {target_timezones} - A list of target timezones for conversion.
# {reference_time} - The reference time (in ISO 8601 format) to interpret relative expressions.
# """

USER_PROMPT = """
You are a time-conversion assistant that can also resolve Slack ID time zones.

Available tools:
{tools}

INPUT:
{expression} - The user’s natural-language request.
{source_timezone} - Default source time zone (override it if a Slack ID lookup succeeds).
{target_timezones} - Target time zones to convert into (ignored if the request is only a Slack ID lookup).
{reference_time} - ISO 8601 timestamp to interpret relative expressions.

Instructions:
1. If the user mentions a Slack ID, use the get_timezone tool to resolve the time zone for that ID.
2. Perform the time conversion using the source and target time zones.
3. Produce a JSON object that matches the provided schema exactly. Populate:
   - input_text with the original request,
   - source and targets with the structured time data,
   - output_text with a concise natural-language answer that addresses the user’s question.
4. Do not include any content outside of the JSON response.
"""




USER_PROMPT = """
You are a time-conversion assistant that can also resolve Slack ID time zones.

Available tools:
{tools}

INPUT:
{expression} - The user’s natural-language request.
{source_timezone} - Default source time zone (override it if a Slack ID lookup succeeds).
{target_timezones} - Target time zones to convert into when the user does not specify their own.
{reference_time} - ISO 8601 timestamp to interpret relative expressions.

Instructions:
1. Identify exactly which time zones the user wants. If a Slack ID is mentioned, resolve it with get_timezone and treat that resolved zone as a requested target. Do not add extra target zones the user did not ask for. If the user never specifies any target zone, then fall back to the provided default target_timezones list.
2. Use the resolved source and requested target time zones to perform the conversion.
3. Produce a JSON object that matches the provided schema exactly. Populate:
   - input_text with the original request,
   - source and targets with only the time data the user asked for,
   - output_text with a concise natural-language answer that responds directly to the user’s question (no added conversions).
4. If get_timezone returns 'Slack ID not found', reflect that in both the structured data and output_text instead of fabricating a time.
5. Do not include any content outside of the JSON response.
"""


USER_INTENT_PROMPT = """
Classify this input to either require a tool call or just a normal request.

INPUT:
{expression} - The input natural language time expression.

1. **Tool Call**: This should be used if the user asks for a time zone lookup for a **specific Slack ID**.
   Example input: "What is the timezone for Slack ID U12345678?"
2. **Normal Request**: This is used for regular time conversion queries, where the user asks to convert a specific time from one time zone to another.
   Example input: "What is 3pm in London in New York and Dubai?"

Output Format:
{{
  "intent": "tool_call"  # If the input requires a Slack ID lookup.
}}
or
{{
  "intent": "normal_request"  # If the input is a regular time conversion request.
}}
"""



def build_interpretation_prompt(
    expression: str,
    *,
    source_timezone: str,
    target_timezones: Iterable[str],
    reference_time: Optional[datetime] = None,
    tools: Optional[List[dict]] = None,
) -> List[dict]:
    
    user_prompt = USER_PROMPT.format(
        expression=expression,
        source_timezone=source_timezone,
        target_timezones=", ".join(target_timezones),
        reference_time=reference_time.isoformat() if reference_time else None,
        tools=json.dumps(tools) if tools else None,
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
