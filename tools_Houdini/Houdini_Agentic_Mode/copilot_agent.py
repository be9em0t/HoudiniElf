import json
from typing import Any, Dict, Optional

import requests

from .skills_houdini import interpret_request


def execute_intent(user_text: str, mcp_url: str = "http://127.0.0.1:5007", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Adapt a chat intent into MCP execute call.

    1) Interpret natural text via skills_houdini.
    2) Post resulting payload to MCP server /execute.
    """
    if not user_text or not isinstance(user_text, str):
        raise ValueError("user_text must be a non-empty string")

    payload = interpret_request(user_text, context)

    try:
        resp = requests.post(f"{mcp_url}/execute", json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": f"MCP request failed: {exc}",
            "payload": payload,
        }
