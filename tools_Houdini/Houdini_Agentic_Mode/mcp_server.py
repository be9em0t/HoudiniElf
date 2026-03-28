import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from .mcp_houdini import preprocess_request, execute_plan
from .rpc_bridge import check_houdini_rpc

logging.basicConfig(level=logging.INFO)


class MCPHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return None
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body)

    def do_GET(self):
        if self.path in ["/", "/health", "/ready"]:
            self._send_json({
                "status": "ok",
                "message": "Houdini MCP server running",
                "rpc": check_houdini_rpc(),
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if payload is None:
            self.send_error(400, "Missing JSON payload")
            return

        if self.path in ["/execute", "/run", "/intent"]:
            intent_text = payload.get("intent") or payload.get("command")
            if not intent_text and payload.get("tool"):
                # direct tool execution (advanced path)
                tool = payload["tool"]
                args = payload.get("args", {})
                try:
                    from .intent_router import execute_routed_intent

                    result = execute_routed_intent({"tool": tool, "args": args})
                    self._send_json({"status": "ok", "result": result})
                except Exception as exc:
                    logging.exception("Tool execution failed")
                    self._send_json({"status": "error", "error": str(exc)}, status=500)
                return

            if not intent_text:
                self.send_error(400, "Missing intent or tool in request")
                return

            context = payload.get("context", {})
            plan = preprocess_request(intent_text, context)
            if plan.get("status") != "ready":
                self._send_json(plan, status=400)
                return

            try:
                out = execute_plan(plan)
                self._send_json({"status": "ok", "plan": plan, "execution": out})
            except Exception as exc:
                logging.exception("Execution failed")
                self._send_json({"status": "error", "error": str(exc)}, status=500)
            return

        self.send_error(404, "Not Found")


def create_server(port: int = 5006) -> HTTPServer:
    return HTTPServer(("127.0.0.1", port), MCPHandler)


def run_server(port: int = 5006):
    server = create_server(port)
    logging.info("Starting Houdini MCP server on port %d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Houdini MCP server stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
