import re
import sys
from typing import Any
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from llm.llm_setup import client

class DebugResponse(BaseModel):
    answer: str = Field(
        description="Full debugging explanation with code and sources"
    )
    spoken_answer: str = Field(
        description="Concise spoken summary of the cause and fix, under 50 words"
    )

def _content_to_text(content: Any) -> str:

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    return ""

def _extract_sources(text: str) -> list[str]:

    matches = re.findall(r"""https?://[^\s<>"']+""", text)
    sources = []

    for url in matches:
        url = url.rstrip(".,;:!?)\]}")
        if url and url not in sources:
            sources.append(url)

    return sources

def _collect_tool_info(messages: list[Any]) -> tuple[list[str], list[str]]:
    tool_names: list[str] = []
    sources: list[str] = []
    seen_tools: set[str] = set()
    seen_sources: set[str] = set()

    for message in messages:
        # Record tool calls made by the assistant.
        for call in getattr(message, "tool_calls", []) or []:
            if isinstance(call, dict):
                name = call.get("name")
                if name and name not in seen_tools:
                    seen_tools.add(name)
                    tool_names.append(name)

        # Record the tool name from its response, if available.
        message_name = getattr(message, "name", None)
        if message_name and message_name not in seen_tools:
            if message.__class__.__name__ == "ToolMessage":
                seen_tools.add(message_name)
                tool_names.append(message_name)

        # Search both tool results and assistant messages for URLs.
        content = _content_to_text(getattr(message, "content", None))
        for source in _extract_sources(content):
            if source not in seen_sources:
                seen_sources.add(source)
                sources.append(source)

    return tool_names, sources

mcp_client = MultiServerMCPClient({
        "devsearch": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [
                "/Users/ifrainam/voice-ai-debugging-agent/backend/mcp_server/server.py"
            ],
        }
})

tools = None

async def initialize_debugger():
    global tools

    if tools is None:
        tools = await mcp_client.get_tools()
        print(f"Loaded {len(tools)} MCP tools")

async def run_debugger(transcript: str, error_text: str) -> dict[str, Any]:

    if tools is None:
        raise RuntimeError(
            "Debugger has not been initialized."
        )
    
    agent = create_agent(
        model=client,
        tools=tools,
        response_format=DebugResponse,
        system_prompt=(
            "You are a developer debugging assistant. "
            "Use the available MCP tools to search GitHub issues, "
            "Stack Overflow, and official documentation when appropriate. "
            "Base your answer on the returned search results. "
            "Do not invent sources or claim you used a tool you did not use. "
            "Explain the likely cause and practical fix. "
            "Include relevant source URLs in the full answer. "
            "The spoken answer must summarize the main cause and fix "
            "in 2-3 short sentences, under 50 words. "
            "Avoid Markdown and long code examples in the spoken answer."
        ),
    )

    prompt = (
        f"User's spoken question:\n{transcript}\n\n"
        f"Error extracted from the screenshot by OCR "
        f"(it may contain OCR errors):\n{error_text}\n\n"
        "Diagnose the issue and provide a practical solution. "
        "Use the available search tools when they would help."
    )

    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    structured = result.get("structured_response")

    if isinstance(structured, DebugResponse):
        answer = structured.answer
        spoken_answer = structured.spoken_answer
    elif isinstance(structured, dict):
        answer = structured.get("answer", "")
        spoken_answer = structured.get("spoken_answer", "")
    else:
        # Fallback if structured output isn't returned
        answer = ""
        spoken_answer = ""

    if not answer:
        answer = "I couldn't generate a debugging answer."

    if not spoken_answer:
        spoken_answer = answer

    messages = result.get("messages", [])
    tool_names, sources = _collect_tool_info(messages)

    return {
        "answer": answer,
        "spoken_answer": spoken_answer,
        "sources": sources,
        "tool_calls": tool_names,
    }
