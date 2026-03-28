import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional

# Ensure this file can be run as a script from the repo root and still find package modules
if __name__ == '__main__' and __package__ is None:
    package_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if package_root not in sys.path:
        sys.path.insert(0, package_root)
    __package__ = 'tools_Houdini.Houdini_Agentic_Mode'

# Support running as package and standalone script
try:
    from tools_Houdini.Houdini_Agentic_Mode.mcp_houdini import execute_request
    from tools_Houdini.Houdini_Agentic_Mode.rpc_bridge import check_houdini_rpc
except ImportError:
    try:
        from .mcp_houdini import execute_request
        from .rpc_bridge import check_houdini_rpc
    except ImportError:
        from mcp_houdini import execute_request
        from rpc_bridge import check_houdini_rpc


class HoudiniMCPRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.end_headers()

    def do_GET(self):
        if self.path != '/health':
            self._set_headers(404)
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Not found'}).encode('utf-8'))
            return

        # report status of MCP prompt flow + backend RPC check
        rpc_status = check_houdini_rpc()
        body = {
            'status': 'ok',
            'mcp': 'ok',
            'rpc': rpc_status,
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(body).encode('utf-8'))

    def do_POST(self):
        if self.path != '/execute':
            self._set_headers(404)
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Not found'}).encode('utf-8'))
            return

        content_length = int(self.headers.get('Content-Length', 0))
        payload_bytes = self.rfile.read(content_length)
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
        except Exception as exc:
            self._set_headers(400)
            self.wfile.write(json.dumps({'status': 'error', 'message': f'Invalid JSON: {exc}'}).encode('utf-8'))
            return

        result = execute_request(payload)
        status_code = 200 if result.get('status') == 'ok' else 400
        self._set_headers(status_code)
        self.wfile.write(json.dumps(result).encode('utf-8'))

    def log_message(self, format: str, *args):
        # Suppress default logging for cleaner output in tests and chat flows.
        return


def create_server(port: int, address: str = '127.0.0.1') -> HTTPServer:
    return HTTPServer((address, port), HoudiniMCPRequestHandler)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run Houdini MCP HTTP server')
    parser.add_argument('--port', type=int, default=5007, help='port to listen on')
    parser.add_argument('--host', default='127.0.0.1', help='host to bind')
    args = parser.parse_args()

    server = create_server(args.port, args.host)
    print(f'Houdini MCP server listening on http://{args.host}:{args.port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down server...')
    finally:
        server.shutdown()
