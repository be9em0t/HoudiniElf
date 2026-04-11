import * as vscode from "vscode";
import path from "node:path";
import fs from "node:fs/promises";
import fsSync from "node:fs";
import os from "node:os";
import type { AgentSession, AuthStorage, ModelRegistry } from "@mariozechner/pi-coding-agent";
import type { Api, Model } from "@mariozechner/pi-ai";

let LOG_FILE_PATH = path.join(os.tmpdir(), "pi-vscode-extension.log");

function preloadLog(message: string) {
  try {
    fsSync.appendFileSync(LOG_FILE_PATH, `[preload] ${new Date().toISOString()} ${message}\n`);
  } catch {
    // ignore
  }
}

preloadLog("extension module loaded");

const DEFAULT_MEMORY_PATH =
  "/Users/dunevv/Applications/VS Code Portable/code-portable-data/user-data/User/globalStorage/github.copilot-chat/memory-tool/memories";

export async function activate(context: vscode.ExtensionContext) {
  LOG_FILE_PATH = resolveLogFilePath(getWorkspaceRoot());
  const logger = new Logger(LOG_FILE_PATH);
  context.subscriptions.push(logger);

  logger.info("Pi extension activating");
  logger.info(`Log file: ${LOG_FILE_PATH}`);

  const provider = new PiSidebarProvider(context, logger);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("piSidebar", provider, {
      webviewOptions: { retainContextWhenHidden: true },
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("pi.openSidebar", async () => {
      await vscode.commands.executeCommand("workbench.view.extension.pi");
      await vscode.commands.executeCommand("piSidebar.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("pi.selectWorkspaceRoot", async () => {
      const picked = await vscode.window.showOpenDialog({
        canSelectFolders: true,
        canSelectFiles: false,
        canSelectMany: false,
        title: "Select workspace root for Pi",
      });
      if (!picked || picked.length === 0) return;
      const target = picked[0].fsPath;
      const config = vscode.workspace.getConfiguration("pi");
      await config.update("workspaceRoot", target, vscode.ConfigurationTarget.Global);
      await vscode.commands.executeCommand("workbench.action.reloadWindow");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("pi.selectModel", async () => {
      await provider.selectModel();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("pi.openLogs", async () => {
      logger.show();
    })
  );

  logger.info("Pi extension activated");
}

class Logger implements vscode.Disposable {
  private readonly channel = vscode.window.createOutputChannel("Pi", { log: true });

  constructor(private readonly logFilePath: string) {
    try {
      fsSync.appendFileSync(this.logFilePath, `[info] ${new Date().toISOString()} logger initialized\n`);
    } catch {
      // ignore
    }
  }

  get path() {
    return this.logFilePath;
  }

  dispose() {
    this.channel.dispose();
  }

  show() {
    this.channel.show(true);
  }

  info(message: string) {
    this.write(`[info] ${message}`);
  }

  warn(message: string) {
    this.write(`[warn] ${message}`);
  }

  error(message: string) {
    this.write(`[error] ${message}`);
  }

  private write(message: string) {
    const line = `${message}`;
    this.channel.appendLine(line);
    try {
      fsSync.appendFileSync(this.logFilePath, `${new Date().toISOString()} ${line}\n`);
    } catch {
      // ignore
    }
  }
}

export function deactivate() {
  // noop
}

class PiSidebarProvider implements vscode.WebviewViewProvider {
  private session: AgentSession | undefined;
  private view: vscode.WebviewView | undefined;
  private authStorage: AuthStorage | undefined;
  private modelRegistry: ModelRegistry | undefined;

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly logger: Logger
  ) {}

  async resolveWebviewView(view: vscode.WebviewView): Promise<void> {
    this.logger.info("Resolving Pi sidebar view");
    this.view = view;
    try {
      view.webview.options = {
        enableScripts: true,
        localResourceRoots: [this.context.extensionUri],
      };

      if (!getWorkspaceRoot()) {
        this.logger.warn("No workspace root configured; showing setup screen");
        view.webview.html = this.getNoWorkspaceHtml(view.webview);
        this.attachMessageHandler(view);
        return;
      }

      view.webview.html = this.getHtml(view.webview);
      this.attachMessageHandler(view);

      const session = await this.getSession();
      this.logModel(session.model);
      this.postModelInfo(session.model);

      const unsubscribe = session.subscribe((event) => {
      if (event.type === "message_start" && event.message.role === "assistant") {
        view.webview.postMessage({ type: "assistantStart" });
        return;
      }

      if (event.type === "message_update") {
        const delta = event.assistantMessageEvent;
        if (delta.type === "text_delta") {
          view.webview.postMessage({ type: "assistantDelta", text: delta.delta });
        }
      }

      if (event.type === "message_end" && event.message.role === "assistant") {
        view.webview.postMessage({ type: "assistantEnd" });
      }
    });

      view.onDidDispose(() => {
        unsubscribe();
        this.view = undefined;
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.logger.error(`Failed to resolve sidebar: ${message}`);
      view.webview.html = this.getErrorHtml(message);
      this.attachMessageHandler(view);
    }
    view.onDidDispose(() => {
      this.view = undefined;
      this.logger.info("Pi sidebar disposed");
    });

  }

  private attachMessageHandler(view: vscode.WebviewView) {
    view.webview.onDidReceiveMessage(async (message) => {
      if (message?.type === "selectWorkspace") {
        await vscode.commands.executeCommand("pi.selectWorkspaceRoot");
        return;
      }

      if (message?.type === "selectModel") {
        await vscode.commands.executeCommand("pi.selectModel");
        return;
      }

      if (message?.type !== "userMessage" || typeof message.text !== "string") return;

      const text = message.text.trim();
      if (!text) return;

      this.logger.info(`User message received (${text.length} chars)`);
      view.webview.postMessage({ type: "userMessage", text });

      try {
        const session = await this.getSession();
        if (session.isStreaming) {
          await session.steer(text);
        } else {
          await session.prompt(text);
        }
      } catch (error) {
        const messageText = error instanceof Error ? error.message : String(error);
        this.logger.error(`Prompt failed: ${messageText}`);
        view.webview.postMessage({
          type: "error",
          text: messageText,
        });
      }
    });
  }

  async selectModel(): Promise<void> {
    try {
      const session = await this.getSession();
      const registry = this.modelRegistry;
      if (!registry) {
        throw new Error("Model registry not initialized.");
      }

      const available = await registry.getAvailable();
      if (available.length === 0) {
        vscode.window.showErrorMessage(
          "No authenticated models available. Run `pi` and `/login`, or set OPENAI_API_KEY in your environment."
        );
        return;
      }

      const picks = available.map((model) => ({
        label: `${model.provider}/${model.id}`,
        description: model.name,
        detail: `Context ${model.contextWindow} tokens`,
        model,
      }));

      const pick = await vscode.window.showQuickPick(picks, {
        placeHolder: "Select a Pi model",
        matchOnDescription: true,
        matchOnDetail: true,
      });

      if (!pick) return;

      await session.setModel(pick.model);
      this.logger.info(`Model set to ${pick.label}`);
      this.postModelInfo(session.model);
    } catch (error) {
      const messageText = error instanceof Error ? error.message : String(error);
      this.logger.error(`Select model failed: ${messageText}`);
      vscode.window.showErrorMessage(`Pi model selection failed: ${messageText}`);
    }
  }

  private postModelInfo(model: Model<Api> | undefined) {
    if (!this.view) return;
    this.view.webview.postMessage({
      type: "modelInfo",
      model: model ? `${model.provider}/${model.id}` : "unknown",
      name: model?.name ?? "",
    });
  }

  private logModel(model: Model<Api> | undefined) {
    if (model) {
      this.logger.info(`Model: ${model.provider}/${model.id} (${model.name})`);
    } else {
      this.logger.warn("Model: not set");
    }
  }

  private async getSession(): Promise<AgentSession> {
    if (this.session) return this.session;

    const workspaceRoot = getWorkspaceRoot();
    if (!workspaceRoot) {
      throw new Error("Open a workspace folder to use Pi.");
    }

    this.logger.info(`Initializing session (workspace: ${workspaceRoot})`);

    const sdk = await this.loadSdk();
    const tools = createTools(workspaceRoot, () => getMemoryBasePath(), sdk);

    if (!this.authStorage) {
      this.authStorage = sdk.AuthStorage.create();
      this.modelRegistry = sdk.ModelRegistry.create(this.authStorage);
    }

    const { session } = await sdk.createAgentSession({
      cwd: workspaceRoot,
      sessionManager: sdk.SessionManager.inMemory(),
      tools: [],
      customTools: tools,
      authStorage: this.authStorage,
      modelRegistry: this.modelRegistry,
    });

    this.logger.info("Pi session ready");
    this.session = session;
    return session;
  }

  private async loadSdk() {
    try {
      const sdk = await import("@mariozechner/pi-coding-agent");
      const typebox = await import("@sinclair/typebox");
      const piAi = await import("@mariozechner/pi-ai");
      return {
        createAgentSession: sdk.createAgentSession,
        SessionManager: sdk.SessionManager,
        AuthStorage: sdk.AuthStorage,
        ModelRegistry: sdk.ModelRegistry,
        defineTool: sdk.defineTool,
        Type: typebox.Type,
        StringEnum: piAi.StringEnum,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.logger.error(`Failed to load pi SDK: ${message}`);
      throw error;
    }
  }

  private getHtml(webview: vscode.Webview): string {
    const nonce = getNonce();
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "media", "sidebar.js")
    );
    const styleUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "media", "sidebar.css")
    );

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>Pi</title>
</head>
<body>
  <div id="status">
    <div id="model">Model: <span id="model-value">loading...</span></div>
    <button id="select-model">Select model</button>
  </div>
  <div id="messages"></div>
  <div id="composer">
    <textarea id="input" rows="3" placeholder="Ask Pi..."></textarea>
    <button id="send">Send</button>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }

  private getNoWorkspaceHtml(webview: vscode.Webview): string {
    const nonce = getNonce();
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body { font-family: var(--vscode-font-family); padding: 12px; }
    button { margin-top: 12px; }
  </style>
  <title>Pi</title>
</head>
<body>
  <p>Set a workspace root so Pi can access files.</p>
  <button id="select">Select workspace root</button>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    document.getElementById('select').addEventListener('click', () => {
      vscode.postMessage({ type: 'selectWorkspace' });
    });
  </script>
</body>
</html>`;
  }

  private getErrorHtml(message: string): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body { font-family: var(--vscode-font-family); padding: 12px; }
    code { background: rgba(0,0,0,0.1); padding: 2px 4px; border-radius: 4px; }
  </style>
  <title>Pi</title>
</head>
<body>
  <p>Pi failed to load. Check the output logs.</p>
  <p>Log file: <code>${LOG_FILE_PATH}</code></p>
  <p><code>${message}</code></p>
</body>
</html>`;
  }
}

function getWorkspaceRoot(): string | undefined {
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (folder) return folder.uri.fsPath;
  const config = vscode.workspace.getConfiguration("pi");
  const configured = config.get<string>("workspaceRoot")?.trim();
  return configured ? configured : undefined;
}

function getMemoryBasePath(): string {
  const config = vscode.workspace.getConfiguration("pi");
  return config.get<string>("memoryStorePath") ?? DEFAULT_MEMORY_PATH;
}

function resolveLogFilePath(workspaceRoot?: string): string {
  if (!workspaceRoot) {
    return path.join(os.tmpdir(), "pi-vscode-extension.log");
  }
  const logDir = path.join(workspaceRoot, ".pi", "logs");
  try {
    fsSync.mkdirSync(logDir, { recursive: true });
  } catch {
    // ignore
  }
  return path.join(logDir, "pi-vscode-extension.log");
}

function resolveWorkspacePath(workspaceRoot: string, inputPath: string): string {
  const resolved = path.resolve(workspaceRoot, inputPath);
  const relative = path.relative(workspaceRoot, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("Path is outside the workspace.");
  }
  return resolved;
}

function resolveMemoryPath(basePath: string, inputPath: string): string {
  let relative = inputPath;
  if (relative.startsWith("/memories/")) {
    relative = relative.slice("/memories/".length);
  } else if (relative.startsWith("memories/")) {
    relative = relative.slice("memories/".length);
  }
  const resolved = path.resolve(basePath, relative);
  const resolvedRelative = path.relative(basePath, resolved);
  if (resolvedRelative.startsWith("..") || path.isAbsolute(resolvedRelative)) {
    throw new Error("Memory path is outside the memory store.");
  }
  return resolved;
}

function createTools(
  workspaceRoot: string,
  getMemoryPath: () => string,
  sdk: {
    defineTool: typeof import("@mariozechner/pi-coding-agent").defineTool;
    Type: typeof import("@sinclair/typebox").Type;
    StringEnum: typeof import("@mariozechner/pi-ai").StringEnum;
  }
) {
  const { defineTool, Type, StringEnum } = sdk;

  const readFileTool = defineTool({
    name: "read_file",
    label: "Read File",
    description: "Read a file from the workspace",
    parameters: Type.Object({
      path: Type.String({ description: "File path relative to workspace root" }),
    }),
    execute: async (_toolCallId, params) => {
      const target = resolveWorkspacePath(workspaceRoot, params.path);
      const content = await fs.readFile(target, "utf8");
      return {
        content: [{ type: "text", text: content }],
        details: { path: params.path },
      };
    },
  });

  const listDirTool = defineTool({
    name: "list_dir",
    label: "List Directory",
    description: "List files in a directory",
    parameters: Type.Object({
      path: Type.Optional(Type.String({ description: "Directory path" })),
    }),
    execute: async (_toolCallId, params) => {
      const target = resolveWorkspacePath(workspaceRoot, params.path ?? ".");
      const entries = await fs.readdir(target, { withFileTypes: true });
      const lines = entries
        .map((entry) => (entry.isDirectory() ? `${entry.name}/` : entry.name))
        .sort();
      return {
        content: [{ type: "text", text: lines.join("\n") }],
        details: { path: params.path ?? "." },
      };
    },
  });

  const grepSearchTool = defineTool({
    name: "grep_search",
    label: "Grep Search",
    description: "Search for text in workspace files",
    parameters: Type.Object({
      query: Type.String({ description: "Search string" }),
      include: Type.Optional(Type.String({ description: "Glob pattern" })),
      maxResults: Type.Optional(Type.Number({ description: "Maximum results" })),
    }),
    execute: async (_toolCallId, params) => {
      const results: string[] = [];
      const max = params.maxResults ?? 50;
      const include = params.include ?? "**/*";
      const files = await vscode.workspace.findFiles(include, "**/node_modules/**", Math.max(max, 200));

      for (const file of files) {
        if (results.length >= max) break;
        const fullPath = file.fsPath;
        let content: string;
        try {
          content = await fs.readFile(fullPath, "utf8");
        } catch {
          continue;
        }

        const lines = content.split(/\r?\n/);
        for (let index = 0; index < lines.length; index++) {
          if (results.length >= max) break;
          const lineText = lines[index];
          if (!lineText.includes(params.query)) continue;
          const relative = vscode.workspace.asRelativePath(file);
          const preview = lineText.trim();
          results.push(`${relative}:${index + 1}: ${preview}`);
        }
      }

      return {
        content: [{ type: "text", text: results.join("\n") }],
        details: { count: results.length },
      };
    },
  });

  const createDirectoryTool = defineTool({
    name: "create_directory",
    label: "Create Directory",
    description: "Create a new directory",
    parameters: Type.Object({
      path: Type.String({ description: "Directory path" }),
    }),
    execute: async (_toolCallId, params) => {
      const target = resolveWorkspacePath(workspaceRoot, params.path);
      await fs.mkdir(target, { recursive: true });
      return {
        content: [{ type: "text", text: `Created ${params.path}` }],
        details: { path: params.path },
      };
    },
  });

  const createFileTool = defineTool({
    name: "create_file",
    label: "Create File",
    description: "Create or overwrite a file",
    parameters: Type.Object({
      path: Type.String({ description: "File path" }),
      content: Type.Optional(Type.String({ description: "File contents" })),
    }),
    execute: async (_toolCallId, params) => {
      const target = resolveWorkspacePath(workspaceRoot, params.path);
      await fs.mkdir(path.dirname(target), { recursive: true });
      await fs.writeFile(target, params.content ?? "", "utf8");
      return {
        content: [{ type: "text", text: `Wrote ${params.path}` }],
        details: { path: params.path },
      };
    },
  });

  const replaceStringTool = defineTool({
    name: "replace_string_in_file",
    label: "Replace String",
    description: "Replace text in a file",
    parameters: Type.Object({
      path: Type.String({ description: "File path" }),
      oldText: Type.String({ description: "Text to replace" }),
      newText: Type.String({ description: "Replacement text" }),
    }),
    execute: async (_toolCallId, params) => {
      const target = resolveWorkspacePath(workspaceRoot, params.path);
      const original = await fs.readFile(target, "utf8");
      if (!original.includes(params.oldText)) {
        throw new Error(`Text not found in ${params.path}`);
      }
      const updated = original.split(params.oldText).join(params.newText);
      await fs.writeFile(target, updated, "utf8");
      return {
        content: [{ type: "text", text: `Updated ${params.path}` }],
        details: { path: params.path },
      };
    },
  });

  const multiReplaceTool = defineTool({
    name: "multi_replace_string_in_file",
    label: "Multi Replace",
    description: "Apply multiple replacements in a file",
    parameters: Type.Object({
      path: Type.String({ description: "File path" }),
      replacements: Type.Array(
        Type.Object({
          oldText: Type.String(),
          newText: Type.String(),
        })
      ),
    }),
    execute: async (_toolCallId, params) => {
      const target = resolveWorkspacePath(workspaceRoot, params.path);
      let content = await fs.readFile(target, "utf8");
      for (const replacement of params.replacements) {
        if (!content.includes(replacement.oldText)) {
          throw new Error(`Text not found in ${params.path}`);
        }
        content = content.split(replacement.oldText).join(replacement.newText);
      }
      await fs.writeFile(target, content, "utf8");
      return {
        content: [{ type: "text", text: `Updated ${params.path}` }],
        details: { path: params.path },
      };
    },
  });

  return [
    readFileTool,
    listDirTool,
    grepSearchTool,
    createDirectoryTool,
    createFileTool,
    replaceStringTool,
    multiReplaceTool,
  ];
}

function getNonce(): string {
  let text = "";
  const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let index = 0; index < 32; index++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
