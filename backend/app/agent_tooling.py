from __future__ import annotations

"""Shared tool capability registry for Company AI's ChatGPT + Gemini agents.

Policy: expose the full provider tool surface that the current API/model and
Company AI execution environment can safely support. Do not silently remove a
tool because it is inconvenient. Preview/high-impact tools remain available
but require the appropriate supervised execution/approval gate.
"""

from typing import Any
import os

OPENAI_HOSTED_TOOLS = (
    "web_search_preview",
    "file_search",
    "computer_use_preview",
    "code_interpreter",
    "image_generation",
)
GEMINI_BUILTIN_TOOLS = (
    "google_search",
    "google_maps",
    "url_context",
    "file_search",
    "code_execution",
    "computer_use",
    "function_calling",
)
SUPERVISED_TOOLS = {
    "computer_use_preview",
    "computer_use",
    "function_calling",
    "remote_mcp",
    "local_shell",
    "shell",
}

def openai_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = [
        {"type": "web_search_preview"},
        {"type": "code_interpreter"},
        {"type": "image_generation"},
    ]
    vector_ids = [x.strip() for x in os.getenv("OPENAI_VECTOR_STORE_IDS", "").split(",") if x.strip()]
    if vector_ids:
        tools.append({"type": "file_search", "vector_store_ids": vector_ids})
    if os.getenv("OPENAI_ENABLE_COMPUTER_USE", "").strip().lower() == "true":
        tools.append({"type": "computer_use_preview", "environment": "browser"})
    return tools

def gemini_tools() -> list[dict[str, Any]]:
    # These are the built-in tools supported by the Gemini API path used by the agent.
    # Computer Use requires a client-side execution loop and is exposed by the
    # capability manifest rather than incorrectly sent through legacy generateContent.
    return [
        {"google_search": {}},
        {"google_maps": {}},
        {"url_context": {}},
        {"code_execution": {}},
    ]

def capability_manifest() -> dict[str, Any]:
    configured_openai = openai_tools()
    return {
        "policy": "full_provider_capability_surface",
        "rule": "Enable all supported tools; only gate tools for safety, authorization, provider limitations, or missing execution infrastructure.",
        "openai": {
            "available_surface": list(OPENAI_HOSTED_TOOLS),
            "enabled_in_this_runtime": [x.get("type") for x in configured_openai],
            "file_search_requires": "OPENAI_VECTOR_STORE_IDS",
            "computer_use_requires": "OPENAI_ENABLE_COMPUTER_USE=true plus supervised browser executor",
        },
        "gemini": {
            "available_surface": list(GEMINI_BUILTIN_TOOLS),
            "enabled_builtin_tools": [next(iter(x.keys())) for x in gemini_tools()],
            "computer_use": "available capability; requires client-side supervised executor",
            "function_calling": "available for Company AI custom tools",
        },
        "supervision": sorted(SUPERVISED_TOOLS),
    }

def tool_policy_prompt() -> str:
    return (
        "TOOL POLICY: Use the strongest relevant available tool rather than guessing. "
        "The Company AI tool registry exposes the full supported OpenAI and Gemini capability surface. "
        "Use web/search for current facts, file retrieval for company knowledge, code execution for calculations "
        "and verification, URL tools for source inspection, maps for location work, image generation when visual "
        "output is needed, and approved Company AI functions for business operations. "
        "Computer-use and other high-impact tools are allowed but must pass their execution/approval gate. "
        "Never bypass security, authorization, owner approval, privacy, or provider safety controls."
    )
