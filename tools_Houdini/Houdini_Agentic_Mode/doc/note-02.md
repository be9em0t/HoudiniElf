The agent was confused when connecting:

So yes, this RPC is hitting the actual Houdini session with UI attached. The earlier print() result means your RPC server is probably evaluating the payload as an expression and returning its value, rather than executing arbitrary statements the way the Python console does. Slightly odd, but very much inside Houdini.

If you want, I can check the startup script next and pinpoint why the RPC accepts hou... expressions but rejects print(...).