import json
import logging
from fastapi import APIRouter, Depends
from openai import OpenAI
from app.schemas import ResponseCreateRequest
from app.auth import verify_token
from app.config import settings
from app.contexts import CvAgentContext
from app.contexts.tools import read_cv, CV_TOOL_SCHEMA, fetch_link, FETCH_LINK_TOOL_SCHEMA
from app.memory.database import log_turn

logger = logging.getLogger(__name__)

router = APIRouter()
client = OpenAI(api_key=settings.openai_api_key)

cv_agent_context = CvAgentContext()
AGENT_CONTEXT = cv_agent_context.get_context()
TOOLS = [CV_TOOL_SCHEMA, FETCH_LINK_TOOL_SCHEMA]

def extract_text(response) -> str:
    texto = ""
    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if block.type == "output_text":
                    texto += block.text
    return texto

def extract_last_user_message(body) -> str:
    for msg in reversed(body.input):
        if msg.role == "user":
            return "".join(c.text for c in msg.content if c.type == "input_text")
    return ""

def to_openai_input(messages: list) -> list[dict]:
    return [
        {
            "role": msg.role,
            "type": msg.type,
            "content": [
                {"type": block.type, "text": block.text}
                for block in msg.content
            ],
        }
        for msg in messages
    ]
    
def to_openai_output_items(output) -> list[dict]:
    items = []
    for item in output:
        if item.type == "function_call":
            items.append({
                "type": "function_call",
                "call_id": item.call_id,
                "name": item.name,
                "arguments": item.arguments,
            })
        elif item.type == "message":
            items.append({
                "type": "message",
                "role": item.role,
                "content": [
                    {"type": block.type, "text": block.text}
                    for block in item.content
                    if block.type == "output_text"
                ],
            })
    return items

@router.post("/v1/responses")
async def create_response(body: ResponseCreateRequest, _auth: str = Depends(verify_token)):
    user_message = extract_last_user_message(body)
    logger.info("Incoming message | previous_response_id=%s | text=%s", body.previous_response_id, user_message)

    conversation_input = to_openai_input(body.input)

    response = client.responses.create(
        model=settings.default_openai_model,
        instructions=AGENT_CONTEXT,
        input=conversation_input,
        previous_response_id=body.previous_response_id if body.store else None,
        store=body.store,
        tools = TOOLS
    )

    while any(item.type == "function_call" for item in response.output):
        tool_output = []
        for item in response.output:
            if item.type != "function_call":
                continue

            args = json.loads(item.arguments)
            logger.info("Tool call requested: %s(%s)", item.name, args)

            if item.name == "read_cv":
                result = read_cv()
            elif item.name == "fetch_link":
                result = await fetch_link(args["url"])
            else:
                raise ValueError(f"Unknown tool: {item.name}")
            
            logger.info("Tool %s result preview: %s", item.name, result[:200])
            
            tool_output.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": result
            })
        
        if body.store:
            response = client.responses.create(
                model=settings.default_openai_model,
                previous_response_id=response.id,
                input=tool_output,
                store=body.store,
                tools = TOOLS
            )
        else:
            conversation_input = conversation_input + to_openai_output_items(response.output) + tool_output
            response = client.responses.create(
                model=settings.default_openai_model,
                instructions=AGENT_CONTEXT,
                input=conversation_input,
                store=body.store,
                tools=TOOLS,
            )
    agent_reply = extract_text(response)
    logger.info("Response completed | response_id=%s | reply_preview=%s", response.id, agent_reply[:150])

    user_message = extract_last_user_message(body)
    log_turn(
        response_id=response.id,
        previous_response_id=body.previous_response_id,
        user_message=user_message,
        agent_reply=agent_reply,
    )

    return response
