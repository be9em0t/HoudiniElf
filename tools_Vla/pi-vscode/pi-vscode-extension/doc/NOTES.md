# Next steps:
- Allow custom prompts
- Periodic quality audit of the code, flagging potential problems and listing them in this file
- Create a valid extension installation package, compatibe with further development

# Development and update

## MCP Servers next steps
- ideally we will reuse VS Code/Github Copilot settings
- we need to be careful about MCP and tool bloat. Less is more.
- use skills to ensure efficient tool use, where appropriate

### In short
- **I can use MCP servers if they’re wired into my toolset by the environment**
- **I can’t independently “discover” or connect to arbitrary MCP servers on my own**
- So if you want me to use a couple of MCP servers, **some setup/functionality is usually needed**

### What that means practically
You’d need one of these:
1. **Existing MCP integration in the agent/runtime**  
   - Register the servers
   - Expose their tools to me
2. **Add support in the app/harness**  
   - For example: config, discovery, auth, and tool routing for MCP
3. **A custom bridge/wrapper**  
   - Your app talks to the MCP server
   - Then surfaces the actions to me as tools

### What I can help with
If you want, I can help you:
- design the MCP wiring
- write the config/manifest
- implement the client bridge
- define how tool calls should be mapped

If you tell me:
- what MCP servers you want to add
- what stack you’re using
- how this agent is hosted

…I can tell you whether it’s already supported or what needs to be added.

## How to build and iterate
- Build the extension after code changes:
  - `npm run compile`
- Launch the extension host from the command line for testing:
  - `code --extensionDevelopmentPath="${PWD}"`
  - In the Extension Development Host window, open the Pi sidebar and exercise the UI.
- Run an Extension Host test from the command line:
  - `npm test` if tests are configured, or use `code --extensionDevelopmentPath="${PWD}" --enable-proposed-api local.pi-vscode-extension` for manual host launch.
  - If using a dedicated test runner, create `./.vscode-test` or a test script and invoke it here.
- Re-package the extension after changes:
  - `npm run package`
  - Accept the warnings for missing repository/license if publishing is not required.
- Reinstall the built package manually:
  - In VS Code, open the Command Palette and choose `Extensions: Install from VSIX...`.
  - Select `pi-vscode-extension-0.0.1.vsix` and reload the window.

## Audit findings
- TypeScript compiles cleanly with `npm run compile`.
- A valid VS Code extension package was created: `pi-vscode-extension-0.0.1.vsix`.
- `vsce package` emitted warnings about the missing `repository` field and a missing license file. Add `repository` to `package.json` and a `LICENSE` file for publication readiness.
- The package currently included 16,624 files (45 MB), so a `.vscodeignore` was added to exclude workspace-only files and logs for future packaging.
- `src/extension.ts` is monolithic and could benefit from refactoring into smaller modules for tool registration, sidebar rendering, and SDK session management.
- Potential runtime issue: `pi.openSidebar` executes `piSidebar.focus`, but that command is not defined by this extension and may fail in VS Code. Confirm the view focus flow or replace it with a supported view/command API.
- Limitation: `getWorkspaceRoot()` only uses the first workspace folder; multi-root workspace support is not implemented.
- Recommendation: bundle the extension before publishing to reduce package size and avoid shipping unnecessary dependency files.


# Random Notes
Symbol font css: /Users/dunevv/WorkLocal/_AI_/HoudiniElf/pi-vscode-extension/node_modules/@vscode/codicons/dist/codicon.css


# UI structure
PNL_MainUI
 ├── PNL_Messages
 │    ├── PNL_Message.assistant
 │    ├── PNL_Message.user
 │    └── PNL_Message.error
 └── PNL_UserInput (gray, rounded c orners, full width of panel)
      ├── PNL_UserInputArea
      │    └── TXT_UserInput (Aligned top, full width, multiline)
      │    └── PNL_ButtonArea (Aligned bottom, full width, single line)
      │         └── BTN_Add (aligned bottom right)
      │         ├── BTN_ModelChip (aligned bottom center)
      │         └── BTN_Send (aligned bottom right)
