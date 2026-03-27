import socket
import threading
import queue
import hou

HOST = "127.0.0.1"
PORT = 5005

cmd_queue = queue.Queue()

def socket_thread():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Allow immediate rebinding after crash
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((HOST, PORT))
    except OSError:
        # Another Houdini instance already owns the port
        print("Houdini RPC server already running on port 5005 — skipping startup.")
        return

    server.listen()
    print(f"Houdini RPC server running on {HOST}:{PORT}")

    while True:
        try:
            conn, _ = server.accept()
            data = conn.recv(4096).decode()
            cmd_queue.put((conn, data))
        except Exception:
            # Prevent socket thread from dying silently
            pass

def process_queue():
    while not cmd_queue.empty():
        conn, cmd = cmd_queue.get()

        try:
            result = str(eval(cmd))
        except Exception as e:
            result = str(e)

        try:
            conn.sendall(result.encode())
        finally:
            conn.close()

# Start background listener
threading.Thread(target=socket_thread, daemon=True).start()

# Execute hou commands safely on main thread
hou.ui.addEventLoopCallback(process_queue)