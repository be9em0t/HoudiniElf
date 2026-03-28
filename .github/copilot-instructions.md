---
applyTo: "**/*.py,**/*.md"
---
# Copilot Chat Integration for Houdini Agentic Mode

## Objective
- Expose the Houdini Agentic Mode pipeline in VS Code Copilot Chat using explicit MCP/skills/tools separation.
- Ensure requests are routed through:
  1. **MCP router** (`tools_Houdini/Houdini_Agentic_Mode/mcp_houdini.py`, `tools_Houdini/Houdini_Agentic_Mode/intent_router.py`)
  2. **Skills** (`tools_Houdini/Houdini_Agentic_Mode/skills_houdini.py`, `tools_Houdini/Houdini_Agentic_Mode/skills_build_network.py`, `tools_Houdini/Houdini_Agentic_Mode/skills_query_scene.py`)
  3. **Tool wrappers** (`tools_Houdini/Houdini_Agentic_Mode/houdini_rpc_tool.py`, `tools_Houdini/Houdini_Agentic_Mode/rpc_bridge.py`)
  4. **Agent orchestration** (`tools_Houdini/Houdini_Agentic_Mode/agent_cli.py`, `tools_Houdini/Houdini_Agentic_Mode/run_agent_cli.py`, `tools_Houdini/Houdini_Agentic_Mode/houdini_agentic_mode.prompt.md`)

## Instructions for Copilot Chat
- Use this as authoritative project behavior; do not bypass the pipeline with direct Houdini RPC code injection.
- Always route natural language through `intent_router.route_intent()` / `skills_houdini.interpret_request()`.
- Map intents -> tool calls and execute only via the declared tool APIs.

## Toolset / Agent declaration
- Agent config file: `tools_Houdini/Houdini_Agentic_Mode/agent_config.json`
- Exposed tools:
  - `run_houdini_python`
  - `push_vex_to_node`
  - `apply_network_template`

## Health and safety
- Preflight: call `rpc_bridge.check_houdini_rpc()`.
- If RPC unavailable, return clear error text and stop: `Houdini RPC is unavailable; verify Houdini is running and the RPC startup script is deployed.`
- No fallback execution modes are permitted; explicit failure is required on missing RPC.
