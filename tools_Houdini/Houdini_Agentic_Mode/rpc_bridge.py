import socket
from typing import Optional

HOST = "127.0.0.1"
PORT = 5005
BUFFER_SIZE = 65536


def run_houdini_python(code: str, timeout: Optional[float] = 10.0) -> str:
    """Send python code to Houdini RPC server and return text response."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("`code` must be a non-empty string")

    payload = code.encode("utf-8")
    if len(payload) > BUFFER_SIZE:
        raise ValueError("Command payload exceeds buffer size")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((HOST, PORT))
        s.send(payload)
        response = s.recv(BUFFER_SIZE)

    return response.decode("utf-8", errors="replace")
