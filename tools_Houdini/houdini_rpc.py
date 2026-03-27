import socket
import sys

HOST = "127.0.0.1"
PORT = 5005

cmd = sys.argv[1]

s = socket.socket()
s.connect((HOST, PORT))
s.send(cmd.encode())

result = s.recv(65536).decode()
print(result)

s.close()