# Houdini Agentic Mode Setup

## 1. Install Houdini RPC startup script (456.py)
- Copy Houdini preferences script folder for your Houdini version:
  - `tools_Houdini/Houdini_Agentic_Mode/Houdini_Preferences/houdini/21.0/scripts/456.py`
 to `~/Library/Preferences/houdini/21.0/scripts/456.py`
- Verify the script loads on Houdini startup by opening Houdini and checking console output:
  - `Houdini RPC server running on 127.0.0.1:5005`

## 2. RPC and MCP verification and launch instructions:
In your project folder:

- test RPC is available
```bash
python -c 'from tools_Houdini.Houdini_Agentic_Mode.rpc_bridge import check_houdini_rpc; print(check_houdini_rpc())'
```
Expected output: `rpc_ok`

- Kill stale 5007 before startup: `lsof -i :5007 -t | xargs -r kill`
- launch python MCP Server using modeule mode: `python -m tools_Houdini.Houdini_Agentic_Mode.mcp_server --port 5007`
- verify `curl http://127.0.0.1:5007/health`
- test MCP is working with simple command (intent mapping via `copilot_agent`, not CLI)
- call MCP from VS Code Chat via prompt + `chat.agent.mcpConfigurationFiles`
- activate MCP task: `Start Houdini MCP Server`
- do not rely on direct 5005 HTTP; MCP should handle RPC proxying through 5007
- optionally use VS Code tasks to auto-start the server:
  - `.vscode/tasks.json`, run `Start Houdini MCP Server` task
  - this avoids manual CLI startup in normal use

- if RPC is not available
    - kill houdini processes (with user permission): `pkill -f "houdini|houdinifx|houdini-bin"`
    - restart Houdini: `tools_Houdini/Houdini_Agentic_Mode/houdini_launch.sh`

extras:
- list available LLM models
- verify LLM availability (keys, tokens avaiable)

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

# 4. Random ToDos
- in MCP startup task (`Start Houdini MCP Server`) implement fallbacks:
  - port 5007 is already taken
  - houdini is not loaded
  - no RPC on port 5005
  - we already have some of these as shell scripts (houdini_launch.sh, houdini_mcp_test.sh)
- make Houdini-MCP start from vscode, as noral MCP server
- should we implement better-defined tools + a low-level structured API for more efficient work? Can we derive them for hou module in a systematic way?
- memory: should we store already defined tools/skills like scatter, create sphere etc.