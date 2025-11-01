from fastapi import FastAPI, Query
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
import traceback
import sys
from dotenv import load_dotenv
import uvicorn
 
load_dotenv()
 
app = FastAPI()
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
            # Start the run
            yield encoder.encode(RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id="thread_1",
                run_id="run_1"
            ))
           
            # Start assistant message
            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id="msg_1",
                role="assistant"
            ))
 
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
 
            # print(f"📋 Available tools: {[t.name for t in tool_descriptions]}")
 
            messages = [
                {
                    "role": "user",
                    "content":  f"""
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
                    tools=openai_tools if openai_tools else None,
                    stream=False,
                )
 
                message = response.choices[0].message
                finish_reason = response.choices[0].finish_reason
 
                # === TOOL CALLING BRANCH ===
                if message.tool_calls:
                    print(f"🔧 LLM wants to call {len(message.tool_calls)} tool(s)")
                   
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    })
 
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
 
                        print(f"  ⚙️  Calling tool: {tool_name} with args: {tool_args}")
 
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
 
                        result = await client.call_tool(tool_name, tool_args)
                        result = result.data
                       
                        if isinstance(result, dict):
                            result_content = result.get("content", str(result))
                        else:
                            result_content = str(result)
 
                        print(f"  ✅ Tool result: {result_content}")
 
                        yield encoder.encode(
                            ToolCallResultEvent(
                                type=EventType.TOOL_CALL_RESULT,
                                message_id="msg_1",
                                tool_call_id=tool_call.id,
                                content=result_content,
                                role="tool",
                            )
                        )
 
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_content,
                        })
 
                    continue
 
                # === TEXT RESPONSE BRANCH ===
                else:
                    # print(f"💬 LLM final response (finish_reason: {finish_reason})")
                   
                    if message.content:
                        content = message.content
                        print(f"📝 Starting to stream {len(content)} characters...")
                       
                        # Stream character by character
                        for i, char in enumerate(content):
                            event_data = encoder.encode(
                                TextMessageContentEvent(
                                    type=EventType.TEXT_MESSAGE_CONTENT,
                                    message_id="msg_1",
                                    delta=char,
                                )
                            )
                            yield event_data
                           
                            # Print progress every 10 characters
                            if (i + 1) % 10 == 0:
                                print(f"  📤 Streamed {i + 1}/{len(content)} chars", flush=True)
                           
                            # Delay for typing effect
                            await asyncio.sleep(0.05)
                       
                        # print(f"  ✅ Finished streaming all {len(content)} characters")
                   
                    yield encoder.encode(
                        TextMessageEndEvent(
                            type=EventType.TEXT_MESSAGE_END,
                            message_id="msg_1"
                        )
                    )
                   
                    yield encoder.encode(
                        RunFinishedEvent(
                            type=EventType.RUN_FINISHED,
                            thread_id="thread_1",
                            run_id="run_1"
                        )
                    )
                   
                    print("✅ Conversation complete!")
                    break

 
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        yield encoder.encode(
            RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e)
            )
        )
    finally:
        print("🔚 Interaction complete.")
 
 
@app.post("/get_data")
async def stream_response(userprompt: str = Query(...)):
    # print(f"\n{'='*60}")
    # print(f"🟡 NEW REQUEST: {userprompt}")
    # print(f"{'='*60}\n")
   
    async def event_generator():
        try:
            async for event in interact_with_server(userprompt, client):
                # event is a string from encoder.encode()
                # Ensure event ends with newline for SSE format
                if not event.endswith('\n'):
                    event = event + '\n'
                yield event
                # Force flush with tiny delay
                await asyncio.sleep(0)
        except Exception as e:
            # print(f"❌ Generator error: {e}")
            
            traceback.print_exc()
 
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
        },
    )
 
 
@app.get("/")
async def root():
    return {"status": "ok", "message": "AG-UI FastAPI server is running"}
 
 
if __name__ == "__main__":
    print("🚀 FastAPI AG-UI server starting on http://127.0.0.1:8001")
    # print("📡 Ready to receive requests...")
    # print("💡 TIP: Watch the console for streaming progress logs")
   
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info",
        access_log=True,
    )