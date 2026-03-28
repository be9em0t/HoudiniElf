# Houdini Agentic Mode Setup

## 1. Install Houdini RPC startup script (456.py)
- Copy Houdini preferences script folder for your Houdini version:
  - `tools_Houdini/Houdini_Agentic_Mode/Houdini_Preferences/houdini/21.0/scripts/456.py`
 to `~/Library/Preferences/houdini/21.0/scripts/456.py`
- Verify the script loads on Houdini startup by opening Houdini and checking console output:
  - `Houdini RPC server running on 127.0.0.1:5005`

## 2. Verify RPC connection from local utility
In your project folder, run:

```bash
python -c 'from tools_Houdini.Houdini_Agentic_Mode.rpc_bridge import check_houdini_rpc; print(check_houdini_rpc())'
```

Expected output: `rpc_ok`

## 2.1 Architecture plan
Orchestrated system that turns freeform user goals into Houdini RPC commands. Good news: this is exactly what Copilot `tools/skills/agent/mcp` should do.

This maps to 4 layers:

1. `tool` = low-level Houdini RPC API caller
2. `skill` = intent-to-precondition translator
3. `MCP` = context/intents router + policy
4. `agent` = final user conversation flow + tool orchestration

## 2.2 Project imperatives
- In VS Code Chat mode, require a non-bypassing LLM-first MCP/skills/tools/agent implementation in all flows. 
- No silent fallbacks: on failure, return explicit error details and stop. Any fallback behavior must be a hard failure with diagnostic text.
- LLM availability is mandatory and immediate; No fallback interpreters or local heuristics are allowed.
- The project is intended to work ONLY with strong LLM models (e.g. Raptor mini (Preview)).  Do not rely on weak or unsupervised heuristics.
- Flow must be:
  - receive user intent,
  - interpret via LLM (or skill layer supporting LLM mapping),
  - execute via tool/MCP/RPC,
  - sanity check state via RPC and return explicit result.

Refer to `requirements.txt` for dependency and install instructions.


## 3. Troubleshooting
- Ensure Houdini runs with Python support and that the script is in the correct version folder.
- If `check_houdini_rpc()` returns failure, check firewall and local port conflict.
- Optional: restart Houdini, then re-run the CLI.

# Next step - build MCP server, tools, skills 

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