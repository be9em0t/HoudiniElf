import json
import threading
import time
from http.client import HTTPConnection

import pytest

from tools_Houdini.Houdini_Agentic_Mode import mcp_server, skills_houdini


def _start_server(port):
    server = mcp_server.create_server(port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_mcp_server_health_check():
    server, thread = _start_server(5007)
    try:
        conn = HTTPConnection("127.0.0.1", 5007, timeout=3)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert "rpc" in data
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_mcp_server_execute_intent(monkeypatch):
    monkeypatch.setenv("RAPTOR_MINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        skills_houdini,
        "llm_translate_intent_to_houdini_code",
        lambda intent, context=None: "'fake-update'",
    )

    server, thread = _start_server(5008)
    try:
        conn = HTTPConnection("127.0.0.1", 5008, timeout=3)
        conn.request(
            "POST",
            "/execute",
            body=json.dumps({"intent": "create sphere"}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert "execution" in data
    finally:
        server.shutdown()
        thread.join(timeout=1)
