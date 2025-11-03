from pydantic import BaseModel, Field

# Define the Pydantic model for the tool call
class ToolCall(BaseModel):
    input_text: str = Field(description="The user's input text")
    tool_name: str = Field(description="The name of the tool to call")
    tool_parameters: str = Field(description="JSON string of tool parameters")

class ResponseModel(BaseModel):
    tool_calls: list[ToolCall]
