from pydantic import BaseModel, Field
from typing import List

class TimeTarget(BaseModel):
    timezone: str = Field(..., description="IANA timezone, e.g. 'America/New_York'")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in h:mm AM/PM format")

class TimeSource(BaseModel):
    timezone: str = Field(..., description="IANA timezone, e.g. 'Africa/Lagos'")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    time: str = Field(..., description="Time in h:mm AM/PM format")

class TimeNLConvertResponse(BaseModel):
    input_text: str = Field(..., description="Original natural language time text")
    output_text: str = Field(..., description="Converted time text with all target timezones")
    source: TimeSource
    targets: List[TimeTarget]
