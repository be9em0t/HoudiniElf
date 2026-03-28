# Houdini Agentic Mode Setup

## 1. Install Houdini RPC startup script (456.py)
- Copy file to Houdini preferences script folder for your Houdini version:
  - `~/WorkLocal/_AI_/HoudiniElf/tools_Houdini/Houdini_Agentic_Mode/Houdini_Preferences/houdini/21.0/scripts/456.py`
  - Or `~/Library/Preferences/houdini/21.0/scripts/456.py`
- Verify the script loads on Houdini startup by opening Houdini and checking console output:
  - `Houdini RPC server running on 127.0.0.1:5005`

## 2. Verify RPC connection from local utility
In your project folder, run:

```bash
python -c 'from tools_Houdini.Houdini_Agentic_Mode.rpc_bridge import check_houdini_rpc; print(check_houdini_rpc())'
```

Expected output: `rpc_ok`

## 2.1 Architecture plan
You’re asking for an orchestrated system that turns freeform user goals into Houdini RPC commands. Good news: this is exactly what Copilot `tools/skills/agent/mcp` should do.

This maps to 4 layers:

1. `tool` = low-level Houdini RPC API caller
2. `skill` = intent-to-precondition translator
3. `MCP` = context/intents router + policy
4. `agent` = final user conversation flow + tool orchestration

## 2.2 Project imperatives
- In VS Code Chat mode, require a non-bypassing MCP/skills/tools/agent implementation in all flows. The agent must route through `intent_router` and `skills_houdini` before `rpc_bridge`.
- No silent fallbacks: on failure, return explicit error details and stop. Any fallback behavior must be a hard failure with diagnostic text.
- LLM availability is mandatory and immediate; if `RAPTOR_MINI_API_KEY` is absent or invalid, the system must refuse request and report configuration error. No fallback interpreters or local heuristics are allowed.
- The project is intended to work ONLY with strong LLM models (e.g. Raptor mini (Preview)).  Do not rely on weak or unsupervised heuristics.
- No dumb hard-coding of commands like `create pink sphere` in code paths. Flow must be:
  - receive user intent,
  - interpret via LLM (or skill layer mimicking LLM mapping),
  - execute via tool/MCP/RPC,
  - sanity check state via RPC and return explicit result.

Refer to `requirements.txt` for dependency and install instructions.

## 3. Run local MCP bridge server (required for VS Code)
From repo root:

```bash
python -m tools_Houdini.Houdini_Agentic_Mode.mcp_server
```

This starts a local HTTP MCP gateway at `http://127.0.0.1:5006`.

### Copilot profile update
In your `mcp.json`, set:

```json
"houdini-mcp": {
  "type": "http",
  "url": "http://127.0.0.1:5006",
  "headers": {}
}
```

Then restart VS Code Copilot and validate `GET /health` responds.

## 4. Use CLI tool
From repo root:

```bash
python -m tools_Houdini.Houdini_Agentic_Mode.agent_cli --intent "create a blue sphere" --dry_run
```

To execute:

```bash
python -m tools_Houdini.Houdini_Agentic_Mode.agent_cli --intent "create a blue sphere"
```

## 4. MCP layer and agent call example
In Python:

```python
from tools_Houdini.Houdini_Agentic_Mode.mcp_houdini import preprocess_request, execute_plan

req = preprocess_request('build new geo network with scatter', {'target_path': '/obj'})
print(req)
if req['status'] == 'ready':
    out = execute_plan(req)
    print(out)
```

## 5. No fallback mode
- If RPC is unavailable, the tools return a clear message: "verify Houdini is running and that the startup RPC script is installed." 
- If LLM config is unavailable (`RAPTOR_MINI_API_KEY` missing), the tools return explicit configuration error and refuse intent routing.
- No fallback to clipboard/standalone Python script or local heuristic command mapping is performed automatically.

## 6. Troubleshooting
- Ensure Houdini runs with Python support and that the script is in the correct version folder.
- If `check_houdini_rpc()` returns failure, check firewall and local port conflict.
- Optional: restart Houdini, then re-run the CLI.

## 7. Usage hint for VS Code MCP
- In your profile `mcp.json`, add:
  - `houdini-mcp` server with `type: http` and URL pointing to local gateway (e.g. `http://127.0.0.1:5006`).
  - Keep existing server entries (e.g. `tomtom-mcp`) if needed.
- Add `tools_Houdini/Houdini_Agentic_Mode/houdini_agentic_mode.prompt.md` to `chat.agent.additionalInstructionFiles`.
- Use the command below to validate in your widget:
  ```bash
  python -m tools_Houdini.Houdini_Agentic_Mode.agent_cli --intent "create a blue sphere" --dry_run
  ```
