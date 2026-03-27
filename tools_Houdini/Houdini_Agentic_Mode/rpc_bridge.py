import socket
import time
from typing import Optional

HOST = "127.0.0.1"
PORT = 5005
BUFFER_SIZE = 65536
MAX_CONNECT_ATTEMPTS = 3
CONNECT_RETRY_DELAY = 1.0


def ensure_rpc_server(timeout: float = 2.0) -> None:
    """Verify that Houdini RPC server is listening."""
    last_err = None
    for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
        try:
            with socket.create_connection((HOST, PORT), timeout=timeout):
                return
        except Exception as exc:
            last_err = exc
            time.sleep(CONNECT_RETRY_DELAY)
    raise ConnectionError(f"Cannot connect to Houdini RPC server at {HOST}:{PORT} after {MAX_CONNECT_ATTEMPTS} attempts") from last_err


def check_houdini_rpc() -> str:
    """Return server health status; used as a preflight check."""
    try:
        ensure_rpc_server(timeout=1.0)
        return 'rpc_ok'
    except ConnectionError as e:
        return f'rpc_down: {e}'


def run_houdini_python(code: str, timeout: Optional[float] = 10.0) -> str:
    """Send python code to Houdini RPC server and return text response."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("`code` must be a non-empty string")

    payload = code.encode("utf-8")
    if len(payload) > BUFFER_SIZE:
        raise ValueError("Command payload exceeds buffer size")

    ensure_rpc_server(timeout=2.0)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((HOST, PORT))
        s.send(payload)
        response = s.recv(BUFFER_SIZE)

    return response.decode("utf-8", errors="replace")
