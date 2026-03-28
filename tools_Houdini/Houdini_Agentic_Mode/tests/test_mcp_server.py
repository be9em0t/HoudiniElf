import json
import threading
import time
from http.client import HTTPConnection

import pytest

from tools_Houdini.Houdini_Agentic_Mode import mcp_server, skills_houdini, copilot_agent


def _start_server(port=0):
    server = mcp_server.create_server(port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_mcp_server_health_check(monkeypatch):
    monkeypatch.setattr(
        'tools_Houdini.Houdini_Agentic_Mode.mcp_server.check_houdini_rpc',
        lambda: 'rpc_ok',
    )
    server, thread = _start_server(0)
    try:
        port = server.server_port
        conn = HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert data["rpc"] == "rpc_ok"
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

    monkeypatch.setattr(
        'tools_Houdini.Houdini_Agentic_Mode.mcp_houdini.check_houdini_rpc',
        lambda: 'rpc_ok',
    )
    monkeypatch.setattr(
        'tools_Houdini.Houdini_Agentic_Mode.mcp_houdini.run_houdini_python',
        lambda code: 'fake run ok',
    )
    server, thread = _start_server(0)
    try:
        port = server.server_port
        conn = HTTPConnection("127.0.0.1", port, timeout=3)
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


def test_mcp_server_execute_skill_fallback(monkeypatch):
    monkeypatch.setenv("RAPTOR_MINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        skills_houdini,
        "llm_translate_intent_to_houdini_code",
        lambda intent, context=None: "pass",
    )
    monkeypatch.setattr(
        # mcp_houdini imports check_houdini_rpc from rpc_bridge
        'tools_Houdini.Houdini_Agentic_Mode.mcp_houdini.check_houdini_rpc',
        lambda: "rpc_down: simulated",
    )

    server, thread = _start_server(0)
    try:
        port = server.server_port
        conn = HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request(
            "POST",
            "/execute",
            body=json.dumps({"intent": "list nodes"}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert "execution" in data
        assert "RPC unavailable" in data["execution"]["result"]
    finally:
        server.shutdown()
        thread.join(timeout=1)

def test_copilot_agent_execute_list_nodes(monkeypatch):
    monkeypatch.setattr(
        skills_houdini,
        'llm_translate_intent_to_houdini_code',
        lambda intent, context=None: "'fake-update'",
    )
    monkeypatch.setattr(
        'tools_Houdini.Houdini_Agentic_Mode.mcp_houdini.check_houdini_rpc',
        lambda: 'rpc_ok',
    )
    monkeypatch.setattr(
        'tools_Houdini.Houdini_Agentic_Mode.mcp_houdini.run_houdini_python',
        lambda code: 'geo1\ngeo2',
    )

    server, thread = _start_server(0)
    try:
        port = server.server_port
        result = copilot_agent.execute_intent('list nodes under /obj', mcp_url=f'http://127.0.0.1:{port}')
        assert result['status'] == 'ok'
        assert 'execution' in result
        assert 'geo1' in result['execution']['result']
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_copilot_agent_supports_example_intents(monkeypatch):
    monkeypatch.setattr(
        'tools_Houdini.Houdini_Agentic_Mode.mcp_houdini.check_houdini_rpc',
        lambda: 'rpc_ok',
    )
    monkeypatch.setattr(
        'tools_Houdini.Houdini_Agentic_Mode.mcp_houdini.run_houdini_python',
        lambda code: 'ok',
    )

    intents = [
        'in houdini list root nodes in /obj context',
        'using houdini MCP add principled shader with blue color',
        'create torus with dimensions 2,2 at zero position',
    ]

    for intent in intents:
        parsed = skills_houdini.interpret_request(intent)
        assert parsed['tool'] == 'run_houdini_python'
        assert 'code' in parsed['args']

