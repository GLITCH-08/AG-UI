from fastapi import FastAPI, Query
from pydantic import BaseModel
from fastmcp import Client
import asyncio
import uvicorn
from typing import Any, Dict
from fastapi.middleware.cors import CORSMiddleware
from openai import AzureOpenAI
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Client("http://127.0.0.1:8000/mcp")

endpoint = os.getenv("endpoint")
model_name = os.getenv("model_name")
deployment = os.getenv("deployment")
subscription_key = os.getenv("subscription_key")
api_version = os.getenv("api_version")


llm = AzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)


async def interact_with_server(user_prompt: str,client):

    try:
        async with client:
            print("✅ Connected to MCP Server")

            # Step 1: Discover available tools
            tool_descriptions = await client.list_tools()
            tool_prompt = "You have access to the following tools:\n\n"

            for tool in tool_descriptions:
                tool_prompt += f"- {tool.name}: {tool.description} : {tool.inputSchema}\n"

            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                }
                for tool in tool_descriptions
            ]

            messages = [{

                "role": "user",

                "content": f"""

                    You are an intelligent agent capable of orchestrating multiple tools to assist users. Below is a list of available tools, each with a name, description of what it does, and the input it requires.

                    Guardrails:

                    - You may only provide answers that are directly related to the database of airports, city details, or weather data.

                    - For Casual greetings or simple pleasantries (e.g., "Hello", "Namaskar","How are you?"), you may respond conversationally(e.g.,"Hi! How can I Assist you today?").

                    - For Casual conversation like (e.g., "ok","Thankyou","amazing") you may respond conversationally(e.g.,"Thank You anything else you want me to assist with you").

                    - Do not provide answers or guesses about anything outside this scope.

                    - If the user's request is outside this scope, respond politely:

                    "I'm sorry, I can only provide information about airports, city details, or weather. Can I help you with that?"

                    Instructions:

                    1. Identify which tools can be used to fulfill their request.

                    2. Call one or more tools as needed.

                    3. Explain how these tools will be used.

                    4. Ask for any additional details if required.

                    5. Do not give any additional explanation, context, or interpretation. Do not hesitate or ask follow-up questions unless the user explicitly asks for explanation or interpretation of Metar Data.

                    6. If duplicate Mongo DB results are present, return only one. If there are differences, return all the unique values.

                    7. If the user specifically asks for Metar data, just provide the Raw Metar Data Value.

                    8. If asked for Hours Back data and no results come back from query running then specify the latest timestamp that is present in MongoDB

                    The user's request is: "{user_prompt}".


                """

            }]


            while True:
                response = llm.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    tool_choice="auto",
                    tools=openai_tools
                )



                message = response.choices[0].message

                # If tool calls are present
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        print(f"🔧 Calling tool: {tool_name} with args: {tool_args}")

                        result = await client.call_tool(tool_name, tool_args)

                        # Append assistant tool call
                        messages.append({
                            "role": "assistant",
                            "tool_calls": [  # mimic OpenAI format
                                {
                                    "id": tool_call.id,
                                    "function": {
                                        "name": tool_name,
                                        "arguments": tool_call.function.arguments
                                    },
                                    "type": "function"
                                }
                            ]
                        })

                        # Append user tool result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result["content"] if isinstance(result, dict) else str(result)
                        })

                else:
                    # Final response from assistant
                    print("💬 Assistant response:", message.content)
                    return message.content



    except Exception as e:
        print(f"❌ MCP Client Error: {e}")
    finally:
        print("🔚 Interaction complete.")


@app.post("/get_data")
async def get_data(userprompt: str):
    data = await interact_with_server(userprompt, client)
    return {"status": "success", "data": data}

if __name__ == "_main_":
    print("🚀 Starting FastAPI MCP Client Middleware...")
    print("🌐 FastAPI middleware will run on: http://127.0.0.1:8001")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info"
    )