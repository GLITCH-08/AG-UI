from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from openai import AzureOpenAI
from ag_ui.encoder import EventEncoder
from ag_ui.core import (
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallResultEvent,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    EventType,
)
import asyncio
import json
import os
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Client("mcp_server.py")

llm = AzureOpenAI(
    api_key=os.getenv("subscription_key"),
    api_version=os.getenv("api_version"),
    azure_endpoint=os.getenv("endpoint"),
)

encoder = EventEncoder()


async def interact_with_server(user_prompt: str, client):
    """Main orchestration generator that yields AG-UI events for streaming."""
    try:
        async with client:
            yield encoder.encode(RunStartedEvent(type=EventType.RUN_STARTED, thread_id="thread_1", run_id="run_1"))
            yield encoder.encode(TextMessageStartEvent(type=EventType.TEXT_MESSAGE_START, message_id="msg_1", role="assistant"))

            # Discover tools from MCP server
            tool_descriptions = await client.list_tools()
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in tool_descriptions
            ]

            messages = [
                {
                    "role": "user",
                    "content": f"""
                    You are an intelligent agent capable of orchestrating multiple tools.
                    The user's request is: "{user_prompt}".
                    """,
                }
            ]

            while True:
                response = llm.chat.completions.create(
                    model=os.getenv("deployment"),
                    messages=messages,
                    tool_choice="auto",
                    tools=openai_tools,
                )

                message = response.choices[0].message

                # === TOOL CALLING BRANCH ===
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        yield encoder.encode(
                            ToolCallStartEvent(
                                type=EventType.TOOL_CALL_START,
                                tool_call_id=tool_call.id,
                                tool_call_name=tool_name,
                            )
                        )
                        yield encoder.encode(
                            ToolCallArgsEvent(
                                type=EventType.TOOL_CALL_ARGS,
                                tool_call_id=tool_call.id,
                                delta=json.dumps(tool_args),
                            )
                        )

                        # Execute MCP tool
                        result = await client.call_tool(tool_name, tool_args)

                        yield encoder.encode(
                            ToolCallResultEvent(
                                type=EventType.TOOL_CALL_RESULT,
                                message_id="msg_1",
                                tool_call_id=tool_call.id,
                                content=result["content"] if isinstance(result, dict) else str(result),
                                role="tool",
                            )
                        )

                        messages.append(
                            {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "id": tool_call.id,
                                        "function": {
                                            "name": tool_name,
                                            "arguments": tool_call.function.arguments,
                                        },
                                        "type": "function",
                                    }
                                ],
                            }
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": result["content"] if isinstance(result, dict) else str(result),
                            }
                        )
                else:
                    # === TEXT STREAMING BRANCH ===
                    if message.content:
                        yield encoder.encode(
                            TextMessageContentEvent(
                                type=EventType.TEXT_MESSAGE_CONTENT,
                                message_id="msg_1",
                                delta=message.content,
                            )
                        )
                    yield encoder.encode(TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id="msg_1"))
                    yield encoder.encode(RunFinishedEvent(type=EventType.RUN_FINISHED, thread_id="thread_1", run_id="run_1"))
                    break

    except Exception as e:
        yield encoder.encode(RunErrorEvent(type=EventType.RUN_ERROR, message=str(e)))
    finally:
        print("🔚 Interaction complete.")


@app.get("/get_data")
async def stream_response(userprompt: str):
    """Expose AG-UI event stream for the React frontend."""
    async def event_generator():
        async for event in interact_with_server(userprompt, client):
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    print("🚀 FastAPI AG-UI server starting...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
