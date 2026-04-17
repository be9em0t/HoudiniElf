# Pi VS Code Extension Development

This document describes how to restore, build, and test the recovered `pi-vscode-extension` project.

## Prerequisites

- Node.js 18.x or 20.x
- npm
- VS Code Insiders installed
- `code-insiders` available in your shell path

## Restore the project

1. Open a terminal and change into the extension folder:
   ```bash
   cd /Users/dunevv/WorkLocal/_AI_/HoudiniElf/tools_Vla/pi-vscode/pi-vscode-extension
   ```

2. Install dependencies from the committed manifest:
   ```bash
   npm ci
   ```

## Build the extension

1. Compile TypeScript to `out/`:
   ```bash
   npm run compile
   ```

2. If you need watch mode for development:
   ```bash
   npm run watch
   ```

## Run in VS Code Insiders Extension Host

1. Start VS Code Insiders with this extension loaded for development:
   ```bash
   code-insiders --extensionDevelopmentPath="$(pwd)"
   ```

2. In the opened Extension Development Host window, verify:
   - the `Pi` activity bar icon is visible
   - the sidebar can open
   - commands like `Pi: Open Sidebar`, `Pi: Select Workspace Root`, and `Pi: Open Logs` work

## Package the extension

1. Create a VSIX package:
   ```bash
   npm run package
   ```

2. Install the generated VSIX manually via VS Code if needed.

## Notes

- `package.json`, `package-lock.json`, and `tsconfig.json` are restored and committed on the `recover/pi-vscode-extension` branch.
- `node_modules/` should remain uncommitted; use `npm ci` after checkout.
- If `code-insiders` is not found, ensure VS Code Insiders is installed and the command-line installation is enabled.

## Troubleshooting

- If TypeScript compilation fails, confirm `npm ci` completed successfully.
- If the extension does not appear in the Extension Host, reload the window and confirm the development path is correct.
- For packaging issues, check `package.json` for required metadata such as `publisher`, `name`, and `engines.vscode`.
