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

## 3. Use CLI tool
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
- No fallback to clipboard/standalone Python script is performed automatically.

## 6. Troubleshooting
- Ensure Houdini runs with Python support and that the script is in the correct version folder.
- If `check_houdini_rpc()` returns failure, check firewall and local port conflict.
- Optional: restart Houdini, then re-run the CLI.
