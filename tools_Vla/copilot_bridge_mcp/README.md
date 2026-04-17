# Copilot Bridge MCP

Minimal MCP server that mirrors a subset of VS Code Copilot chat tools:

- `memory`: persistent key/value memory with list/search/delete
- `vscode_listCodeUsages`: whole-word symbol usage search via `rg`
- `vscode_renameSymbol`: whole-word rename across workspace files (dry-run by default)
- `resolve_memory_file_uri`: resolve memory path/URI to absolute file path + `file://` URI
- `vscode_restart`: macOS VS Code hard restart + workspace reopen + restart state handoff file

## Run

```bash
uv run --with mcp python /Users/dunevv/WorkLocal/_AI_/HoudiniElf/tools_Vla/copilot_bridge_mcp/server.py
```

By default, `memory` writes to Copilot Chat memory file:

`/Users/dunevv/Applications/VS Code Portable/code-portable-data/user-data/User/globalStorage/github.copilot-chat/memory-tool/memories/debugging.md`

Optional memory file override (markdown or json):

```bash
uv run --with mcp python /Users/dunevv/WorkLocal/_AI_/HoudiniElf/tools_Vla/copilot_bridge_mcp/server.py \
  --memory-file /Users/dunevv/.codex/memory/copilot_bridge_memory.json
```

## Add to Codex MCP

```bash
codex mcp add copilot-bridge -- uv run --with mcp python /Users/dunevv/WorkLocal/_AI_/HoudiniElf/tools_Vla/copilot_bridge_mcp/server.py
```

## Notes

- `vscode_renameSymbol` uses text-based replacement; it is not AST/LSP-aware.
- Keep `dry_run=true` first, then rerun with `dry_run=false`.
- In markdown mode, Codex-owned entries are stored as `- [codex:<key>] <value>` so they can coexist with Copilot notes.
- `vscode_restart` currently supports macOS only, and reopens `workspace_path` after restart.

## `vscode_restart` usage

Suggested first call:

```json
{
  "workspace_path": "/Users/dunevv/WorkLocal/_AI_/HoudiniElf",
  "session_note": "Restart requested after MCP settings change",
  "dry_run": true
}
```

Then execute:

```json
{
  "workspace_path": "/Users/dunevv/WorkLocal/_AI_/HoudiniElf",
  "session_note": "Restart requested after MCP settings change",
  "dry_run": false
}
```

By default it writes restart handoff context to:

`~/.codex/state/vscode_restart_state.json`
