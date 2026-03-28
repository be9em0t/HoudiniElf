
# Plan - build MCP server, tools, skills 

You already have the hardest part working: Houdini’s **HOM RPC server**. MCP should sit **on top of that**, not replace it. Think of RPC as the transport into Houdini, and MCP as the structured API layer for AI.
---
## 1) What you have now (RPC)
Houdini exposes Python over the network via `hrpyc.start_server()` and you import a remote `hou` module from another process.
That gives:
LLM → Python client → RPC → hou API → Houdini
It works, but:
- objects are proxied (slow)
- no tool schema
- no validation
- no context management
- no discoverability
That’s exactly what MCP solves.
---
## 2) Target architecture with MCP
Correct long-term structure:
           ┌──────────────┐  
           │  LLM Host    │ (VSCode, Cline, Claude, etc.)  
           └──────┬───────┘  
                  │ MCP  
           ┌──────▼───────┐  
           │ MCP Server   │  ← you implement this  
           │ (Python)     │  
           └──────┬───────┘  
                  │ RPC  
           ┌──────▼───────┐  
           │ Houdini       │  
           │ hrpyc server  │  
           └──────────────┘
MCP uses a client-server model where the host connects to servers exposing tools and resources over a standard protocol.
So your MCP server is essentially:  
**a typed wrapper around hou**.
---
## 3) Split responsibilities correctly
### Houdini RPC server
Handles:
- scene mutation
- geometry ops
- node graph operations
It should **stay minimal and dumb**.
### MCP server
Handles:
- tool schema
- argument validation
- session state
- batching
- caching
- higher-level abstractions
This separation dramatically improves reliability and speed.
---
## 4) Minimal viable MCP server for Houdini
Core components:
### Transport
Start with **STDIO** (simplest, lowest latency)
### Connection bootstrap
Your MCP server should:
1. Start
2. Connect to Houdini RPC
3. Keep connection alive globally
Example skeleton:
# houdini_mcp_server.py  
from mcp.server.fastmcp import FastMCP  
import hrpyc  
mcp = FastMCP("houdini")  
connection, hou = hrpyc.import_remote_module()  
@mcp.tool()  
def create_geo(name: str):  
    obj = hou.node("/obj")  
    node = obj.createNode("geo", name)  
    return node.path()
---
## 5) Tools vs Skills (important design decision)
### Tools
Atomic operations:
- create node
- set parm
- cook node
- save hip
- export geometry
These map almost 1-to-1 to HOM.
### Skills
High-level workflows:
- “create pyro sim”
- “build instancing network”
- “import CSV and build scatter”
Skills orchestrate multiple tools.
You’ll want:
tools/  
    nodes.py  
    parms.py  
    geometry.py  
skills/  
    pyro.py  
    scattering.py  
    layout.py
This mirrors Houdini’s own mental model and works extremely well for LLM planning.
---
## 6) Avoid the biggest performance trap
**Never expose raw hou objects through MCP.**
Bad:
return hou.node("/obj/geo1")
Good:
return "/obj/geo1"
Because:
- RPC proxies are slow
- MCP serializes everything to JSON
- nested proxy objects explode latency
This is the #1 reason RPC setups feel sluggish.
---
## 7) Add a command queue (huge stability gain)
Houdini is not thread-safe. RPC calls from MCP can collide with UI operations.
Add a dispatcher inside Houdini:
MCP → RPC → enqueue(cmd) → Houdini main thread executes
This prevents:
- random crashes
- viewport freezes
- partial node creation
---
## 8) Tool granularity that works best in practice
Too fine:
set_parm_value(node, parm, value)
Too coarse:
build_city_simulation()
Sweet spot:
create_node(type, parent, name)  
set_parm(node, parm, value)  
connect_nodes(src, dst)
This gives the LLM composability without hallucinating giant workflows.
---
## 9) Recommended first tool set
Implement these first:
### Scene
load_hip(path)  
save_hip(path)
### Nodes
create_node  
delete_node  
list_children  
connect_nodes
### Parameters
set_parm  
get_parm
### Geometry
export_geo(path)  
import_geo(path)
With just this, an AI can build 90% of Houdini networks.
---
## 10) Reliability improvements over raw RPC
MCP lets you add:
### Argument validation
node: str  # must be valid path  
parm: str  # must exist
### Structured errors
Instead of:
Traceback...
You return:
{"error": "parm not found"}
### Retry logic
If Houdini is cooking, retry instead of failing.
---
## 11) Suggested development order
1. **Write MCP server**
2. Connect to Houdini RPC
3. Implement 3 tools:
    - `create_node`
    - `set_parm`
    - `connect_nodes`
4. Test from CLI agent
5. Add skills later
Do **not** start with skills — they’re useless until tools are stable.

## 13) Copilot agent integration path
This repository now includes a small Copilot adapter module at:
- `tools_Houdini/Houdini_Agentic_Mode/copilot_agent.py`

It maps chat intents into MCP requests:
1. `skills_houdini.interpret_request(user_text)`
2. `POST {mcp_url}/execute` with that payload

Example usage:
```python
from tools_Houdini.Houdini_Agentic_Mode.copilot_agent import execute_intent
print(execute_intent('list nodes under /obj', mcp_url='http://127.0.0.1:5007'))
```

### Minimal local Copilot chat configuration
Add to your VS Code settings (user/workspace):
```json
"chat.agent.additionalInstructionFiles": [
  "${workspaceFolder}/tools_Houdini/Houdini_Agentic_Mode/houdini_agentic_mode.prompt.md"
],
"chat.agent.mcpConfigurationFiles": [
  "${workspaceFolder}/tools_Houdini/Houdini_Agentic_Mode/mcp.json"
],
"chat.agent.openaiToolName": "houdini-mcp"
```

Then call from chat: `list nodes under /obj` and it will route through `copilot_agent` + `mcp_server`.

### Optional unified wiring (one page)
In the same file (this README):
- How to install Houdini RPC script
- How to verify `check_houdini_rpc()`
- How to start MCP server
- How to run health + execute control commands
- How to configure Copilot to point to local `houdini-mcp`

This is already in place above; keep it synced to avoid drift.


## 12) VS Code Copilot MCP wiring
1. Add workspace `mcp.json`:
```json
{
  "servers": {
    "houdini-mcp": {
      "type": "http",
      "url": "http://127.0.0.1:5007",
      "headers": {"Content-Type": "application/json"}
    }
  }
}
```
2. Add to VS Code settings:
```json
"chat.agent.additionalInstructionFiles": [
  "${workspaceFolder}/tools_Houdini/Houdini_Agentic_Mode/houdini_agentic_mode.prompt.md"
],
"chat.agent.mcpConfigurationFiles": [
  "${workspaceFolder}/tools_Houdini/Houdini_Agentic_Mode/mcp.json"
],
"chat.agent.openaiToolName": "houdini-mcp"
```
3. Use `python -m tools_Houdini.Houdini_Agentic_Mode.mcp_server --port 5007` to start.

### Example curl + health-check
```bash
curl -X POST http://127.0.0.1:5007/execute \
  -H "Content-Type: application/json" \
  -d '{"intent":"list nodes under /obj", "tool":"run_houdini_python", "args":{"code":"'\\n'.join([n.path() for n in hou.node('/obj').children()])"}}'

curl http://127.0.0.1:5007/health
```
Expected: `{"status":"ok","rpc":"rpc_ok"}`
