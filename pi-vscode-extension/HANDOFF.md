# Pi VS Code Extension Handoff

## Overview
Minimal VS Code sidebar extension embedding the pi SDK. Provides a Copilot-style chat UI and a small toolset (file ops + memory) for early iteration.

## Location
`/Users/dunevv/WorkLocal/_AI_/HoudiniElf/pi-vscode-extension`

## Build & Run
```bash
cd /Users/dunevv/WorkLocal/_AI_/HoudiniElf/pi-vscode-extension
npm install
npm run compile
```

### Debug (Extension Host)
Open the folder in VS Code and run **Run Pi Extension** (F5). This opens a **Debug Extension Host** window.

We added a launch config that disables Copilot Chat to avoid its runtime error:
`.vscode/launch.json` → `--disable-extension=github.copilot-chat`

## Usage
- Open the **Pi** sidebar (Activity Bar icon) or Command Palette: **Pi: Open Sidebar**.
- Type a message, send with **Cmd/Ctrl+Enter**.

### Workspace Root
If no workspace folder is open, the sidebar shows a button to set a fallback workspace root.
- Command: **Pi: Select Workspace Root**
- Setting: `pi.workspaceRoot`

## Settings
- `pi.memoryStorePath` (default is Copilot memory store path)
- `pi.workspaceRoot` (fallback root when no workspace is open)

## Tools Implemented (custom tools via pi SDK)
- `read_file`
- `list_dir`
- `grep_search` (simple line match)
- `create_file`
- `create_directory`
- `replace_string_in_file`
- `multi_replace_string_in_file`
- `memory` with actions: `view`, `create`, `str_replace`, `insert`, `delete`, `rename`

Memory tool maps `/memories/...` paths onto `pi.memoryStorePath`.

## Key Files
- `src/extension.ts` — extension activation, sidebar provider, tools
- `media/sidebar.js` / `media/sidebar.css` — minimal webview UI
- `package.json` — contributes view + commands + settings
- `.vscode/launch.json` — debug config

## Known Issues / Notes
- If the Debug Extension Host has **no workspace**, the sidebar shows a setup screen. Use the button to pick a root.
- Copilot Chat extension can throw and break the debugger; disabled in launch config.

## Requirements / Safety Constraints
- **Never touch, modify, or delete any files that are part of the VS Code installation** (app bundle, extensions directory, user-data backups, etc.).
- **Only edit VS Code JSON settings after explicit user approval** (e.g., `settings.json`, `keybindings.json`, `launch.json`).

## Testing & Debugging Plan
- **Immediate logging on launch:** the extension should write a log file as soon as it activates (before any webview is opened or debugger attached).
  - Log location: `<workspace>/.pi/logs/pi-vscode-extension.log` (create folders if missing).
  - Include timestamp, extension version, and activation context.
- **Out-of-band logging:** continue logging even when no debugger is attached so issues can be captured from normal launches.
- **Debugging without Extension Host UI:** add a lightweight command (e.g., `Pi: Dump Diagnostics`) that writes current state, config, and recent errors to the log file.
- **Test flow:**
  1. Open VS Code normally (no debugger) and confirm the log file is created on activation.
  2. Open the Pi sidebar, send a message, and verify log entries for UI init + message send.
  3. Trigger a tool call and confirm tool start/finish are logged.
  4. Run **Run Pi Extension** (F5) only when needed for step-through debugging; rely on file logs for most issues.

## Next Steps (Suggested)
- Add markdown rendering and tool status chips in sidebar.
- Extend tool list and adopt better grep (regex, case-insensitive, binary skip).
- Improve memory management UI and commands.
- Add keybinding for `Pi: Open Sidebar`.
