from pydantic import BaseModel
from typing import Literal, List, Optional

class InputTextContent(BaseModel):
    text: str
    type: Literal["input_text"] = "input_text"

class OutputTextContent(BaseModel):
    type: Literal["output_text"] = "output_text"
    text: str
    logprobs: list = []
    annotations: list = []

class InputMessage(BaseModel):
    type: Literal["message"] = "message"
    role: Literal["user", "assistant"]
    content: List[InputTextContent | OutputTextContent]
    phase: str | None = None
    status: str | None = None

class ResponseCreateRequest(BaseModel):
    model: str | None = None
    input: List[InputMessage]
    previous_response_id: Optional[str] = None
    store: bool = True
    