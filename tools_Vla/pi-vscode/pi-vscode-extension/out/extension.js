import * as vscode from "vscode";
import path from "node:path";
import fs from "node:fs/promises";
import fsSync from "node:fs";
import os from "node:os";
import { execFile as execFileCallback } from "node:child_process";
import { promisify } from "node:util";
const execFile = promisify(execFileCallback);
let LOG_FILE_PATH = path.join(os.tmpdir(), "pi-vscode-extension.log");
let DEVELOPMENT_WORKSPACE_ROOT;
function preloadLog(message) {
    try {
        fsSync.appendFileSync(LOG_FILE_PATH, `[preload] ${new Date().toISOString()} ${message}\n`);
    }
    catch {
        // ignore
    }
}
preloadLog("extension module loaded");
export async function activate(context) {
    if (context.extensionMode === vscode.ExtensionMode.Development) {
        DEVELOPMENT_WORKSPACE_ROOT = context.extensionUri.fsPath;
    }
    LOG_FILE_PATH = resolveLogFilePath(context.globalStoragePath);
    const logger = new Logger(LOG_FILE_PATH);
    context.subscriptions.push(logger);
    logger.info("Pi extension activating");
    logger.info(`Log file: ${LOG_FILE_PATH}`);
    const provider = new PiSidebarProvider(context, logger);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider("piSidebar", provider, {
        webviewOptions: { retainContextWhenHidden: true },
    }));
    context.subscriptions.push(vscode.commands.registerCommand("pi.openSidebar", async () => {
        await vscode.commands.executeCommand("workbench.view.extension.pi");
        await vscode.commands.executeCommand("piSidebar.focus");
    }));
    context.subscriptions.push(vscode.commands.registerCommand("pi.selectWorkspaceRoot", async () => {
        const picked = await vscode.window.showOpenDialog({
            canSelectFolders: true,
            canSelectFiles: false,
            canSelectMany: false,
            title: "Select workspace root for Pi",
        });
        if (!picked || picked.length === 0)
            return;
        const target = picked[0].fsPath;
        const config = vscode.workspace.getConfiguration("pi");
        await config.update("workspaceRoot", target, vscode.ConfigurationTarget.Global);
        await vscode.commands.executeCommand("workbench.action.reloadWindow");
    }));
    context.subscriptions.push(vscode.commands.registerCommand("pi.selectModel", async () => {
        await provider.selectModel();
    }));
    context.subscriptions.push(vscode.commands.registerCommand("pi.openLogs", async () => {
        logger.show();
    }));
    logger.info("Pi extension activated");
}
class Logger {
    constructor(logFilePath) {
        this.logFilePath = logFilePath;
        this.channel = vscode.window.createOutputChannel("Pi", { log: true });
        try {
            fsSync.appendFileSync(this.logFilePath, `[info] ${new Date().toISOString()} logger initialized\n`);
        }
        catch {
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
    info(message) {
        this.write(`[info] ${message}`);
    }
    warn(message) {
        this.write(`[warn] ${message}`);
    }
    error(message) {
        this.write(`[error] ${message}`);
    }
    write(message) {
        const line = `${message}`;
        this.channel.appendLine(line);
        try {
            fsSync.appendFileSync(this.logFilePath, `${new Date().toISOString()} ${line}\n`);
        }
        catch {
            // ignore
        }
    }
}
export function deactivate() {
    // noop
}
class PiSidebarProvider {
    constructor(context, logger) {
        this.context = context;
        this.logger = logger;
    }
    async resolveWebviewView(view) {
        this.logger.info("Resolving Pi sidebar view");
        this.view = view;
        try {
            view.webview.options = {
                enableScripts: true,
                localResourceRoots: [
                    this.context.extensionUri,
                    vscode.Uri.joinPath(this.context.extensionUri, "node_modules", "@vscode", "codicons", "dist"),
                ],
            };
            if (!getWorkspaceRoot()) {
                this.logger.warn("No workspace root configured; showing setup screen");
                view.webview.html = this.getNoWorkspaceHtml(view.webview);
                this.attachMessageHandler(view);
                return;
            }
            view.webview.html = this.getHtml(view.webview);
            this.attachMessageHandler(view);
            this.ensureStatusBarItem();
            const session = await this.getSession();
            this.logModel(session.model);
            this.postModelInfo(session.model);
            let unsubscribe;
            unsubscribe = session.subscribe((event) => {
                if (event.type === "message_start" && event.message.role === "assistant") {
                    view.webview.postMessage({ type: "assistantStart" });
                    return;
                }
                if (event.type === "message_update") {
                    const delta = event.assistantMessageEvent;
                    if (delta.type === "text_delta") {
                        view.webview.postMessage({ type: "assistantDelta", text: delta.delta, deltaType: "text" });
                    }
                    if (delta.type === "thinking_delta") {
                        view.webview.postMessage({ type: "assistantDelta", text: delta.delta, deltaType: "thinking" });
                    }
                }
                if (event.type === "message_end" && event.message.role === "assistant") {
                    const assistantMessage = event.message;
                    this.logger.info(`Responding model: ${assistantMessage.provider}/${assistantMessage.model}`);
                    this.postRespondingModelInfo(assistantMessage);
                    view.webview.postMessage({ type: "assistantEnd" });
                }
            });
            view.onDidDispose(() => {
                unsubscribe?.();
                this.view = undefined;
                if (this.statusBarItem) {
                    this.statusBarItem.hide();
                }
                this.logger.info("Pi sidebar disposed");
            });
        }
        catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            this.logger.error(`Failed to resolve sidebar: ${message}`);
            view.webview.html = this.getErrorHtml(message);
            this.attachMessageHandler(view);
        }
    }
    attachMessageHandler(view) {
        view.webview.onDidReceiveMessage(async (message) => {
            if (message?.type === "selectWorkspace") {
                await vscode.commands.executeCommand("pi.selectWorkspaceRoot");
                return;
            }
            if (message?.type === "selectModel") {
                await vscode.commands.executeCommand("pi.selectModel");
                return;
            }
            if (message?.type !== "userMessage" || typeof message.text !== "string")
                return;
            const text = message.text.trim();
            if (!text)
                return;
            this.logger.info(`User message received (${text.length} chars)`);
            view.webview.postMessage({ type: "userMessage", text });
            try {
                const session = await this.getSession();
                if (session.isStreaming) {
                    await session.steer(text);
                }
                else {
                    await session.prompt(text);
                }
            }
            catch (error) {
                const messageText = error instanceof Error ? error.message : String(error);
                this.logger.error(`Prompt failed: ${messageText}`);
                view.webview.postMessage({
                    type: "error",
                    text: messageText,
                });
            }
        });
    }
    async selectModel() {
        try {
            const session = await this.getSession();
            const registry = this.modelRegistry;
            if (!registry) {
                throw new Error("Model registry not initialized.");
            }
            injectFavoriteFallbackModels(registry);
            const available = await registry.getAvailable();
            if (available.length === 0) {
                vscode.window.showErrorMessage("No authenticated models available. Run `pi` and `/login`, or set OPENAI_API_KEY in your environment.");
                return;
            }
            const favoriteOrder = getFavoriteModelOrder();
            const picks = [...available]
                .sort((left, right) => compareFavoriteModelOrder(left, right, favoriteOrder))
                .map((model) => ({
                label: favoriteOrder.has(modelKey(model)) ? `★ ${model.provider}/${model.id}` : `${model.provider}/${model.id}`,
                description: model.name,
                detail: `Context ${model.contextWindow} tokens`,
                model,
            }));
            const pick = await vscode.window.showQuickPick(picks, {
                placeHolder: "Select a Pi model",
                matchOnDescription: true,
                matchOnDetail: true,
            });
            if (!pick)
                return;
            await session.setModel(pick.model);
            this.logger.info(`Model set to ${pick.label}`);
            this.postModelInfo(session.model);
        }
        catch (error) {
            const messageText = error instanceof Error ? error.message : String(error);
            this.logger.error(`Select model failed: ${messageText}`);
            vscode.window.showErrorMessage(`Pi model selection failed: ${messageText}`);
        }
    }
    postRespondingModelInfo(message) {
        const respondingModel = `${message.provider}/${message.model}`;
        const selectedModel = this.session?.model ? `${this.session.model.provider}/${this.session.model.id}` : "unknown";
        this.updateStatusBar(selectedModel, respondingModel);
        if (!this.view)
            return;
        this.view.webview.postMessage({
            type: "respondingModelInfo",
            respondingModel,
            selectedModel,
        });
    }
    updateStatusBar(selectedModel, respondingModel) {
        if (!this.statusBarItem)
            return;
        this.statusBarItem.text = `Pi: selected ${selectedModel} · responding ${respondingModel}`;
        this.statusBarItem.show();
    }
    ensureStatusBarItem() {
        if (this.statusBarItem)
            return;
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
        this.statusBarItem.tooltip = "Pi selected and actual responding model";
        this.statusBarItem.show();
    }
    postModelInfo(model) {
        const selectedModel = model ? `${model.provider}/${model.id}` : "unknown";
        this.updateStatusBar(selectedModel, this.session?.model ? `${this.session.model.provider}/${this.session.model.id}` : selectedModel);
        if (!this.view)
            return;
        this.view.webview.postMessage({
            type: "modelInfo",
            selectedModel: selectedModel,
            name: model?.name ?? "",
        });
    }
    logModel(model) {
        if (model) {
            this.logger.info(`Model: ${model.provider}/${model.id} (${model.name})`);
        }
        else {
            this.logger.warn("Model: not set");
        }
    }
    async getSession() {
        if (this.session)
            return this.session;
        const workspaceRoot = getWorkspaceRoot();
        if (!workspaceRoot) {
            throw new Error("Open a workspace folder to use Pi.");
        }
        this.logger.info(`Initializing session (workspace: ${workspaceRoot})`);
        const sdk = await this.loadSdk();
        const tools = createTools(workspaceRoot, sdk, this.context.extensionUri.fsPath);
        if (!this.authStorage) {
            this.authStorage = sdk.AuthStorage.create();
            this.modelRegistry = sdk.ModelRegistry.create(this.authStorage);
        }
        const startupModel = await this.getStartupModel(this.modelRegistry);
        if (startupModel) {
            this.logger.info(`Startup model: ${startupModel.provider}/${startupModel.id}`);
        }
        const { session } = await sdk.createAgentSession({
            cwd: workspaceRoot,
            sessionManager: sdk.SessionManager.inMemory(),
            tools: [],
            customTools: tools,
            authStorage: this.authStorage,
            modelRegistry: this.modelRegistry,
            model: startupModel,
        });
        this.logger.info("Pi session ready");
        this.session = session;
        return session;
    }
    async getStartupModel(registry) {
        if (!registry)
            return undefined;
        injectFavoriteFallbackModels(registry);
        const favorites = getFavoriteModelRefs();
        if (favorites.length === 0)
            return undefined;
        const available = await registry.getAvailable();
        for (const favorite of favorites) {
            const match = available.find((model) => model.provider === favorite.provider && model.id === favorite.id);
            if (match) {
                return match;
            }
        }
        return undefined;
    }
    async loadSdk() {
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
        }
        catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            this.logger.error(`Failed to load pi SDK: ${message}`);
            throw error;
        }
    }
    getHtml(webview) {
        const nonce = getNonce();
        const version = Date.now();
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "sidebar.js")) + `?v=${version}`;
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "sidebar.css")) + `?v=${version}`;
        const addIconUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "BTN_Add.svg")) + `?v=${version}`;
        const sendIconUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "BTN_Send.svg")) + `?v=${version}`;
        const chevronIconUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "BTN_chevron.svg")) + `?v=${version}`;
        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; img-src ${webview.cspSource}; font-src ${webview.cspSource}; script-src 'nonce-${nonce}';" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>Pi</title>
</head>
<body style="position:relative; min-height:100vh; margin:0; padding:0;">
  <div id="PNL_Messages" style="position:absolute; inset:0; overflow-y:auto; padding:14px 14px 12px; padding-bottom:calc(12px + 180px); min-height:0;"></div>
  <div id="PNL_UserInput" style="position:absolute; left:0; right:0; bottom:0; padding:12px; background:transparent; z-index:1;">
    <div class="PNL_UserInputArea">
      <textarea id="TXT_UserInput" rows="3" placeholder="Ask Pi..."></textarea>
      <div class="PNL_ButtonArea">
        <button id="BTN_Add" class="BTN_IconButton" type="button" aria-label="Add">
          <img src="${addIconUri}" alt="Add" />
        </button>
        <button id="BTN_SelectModel" class="BTN_ModelChip" type="button">
          <span class="TXT_ModelLabel">Select model</span>
          <img src="${chevronIconUri}" alt="Expand" class="ICN_Chevron" />
        </button>
        <button id="BTN_Send" class="BTN_IconButton" type="button" aria-label="Send">
          <img src="${sendIconUri}" alt="Send" />
        </button>
      </div>
      <div id="TXT_ModelStatus" class="TXT_ModelStatus">Selected: unknown · Responding: unknown</div>
    </div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
    getNoWorkspaceHtml(webview) {
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
    getErrorHtml(message) {
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
  <p>Log file: <code>${escapeHtml(LOG_FILE_PATH)}</code></p>
  <p><code>${escapeHtml(message)}</code></p>
</body>
</html>`;
    }
}
function escapeHtml(value) {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
function getWorkspaceRoot() {
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (folder)
        return folder.uri.fsPath;
    if (DEVELOPMENT_WORKSPACE_ROOT)
        return DEVELOPMENT_WORKSPACE_ROOT;
    const config = vscode.workspace.getConfiguration("pi");
    const configured = config.get("workspaceRoot")?.trim();
    return configured ? configured : undefined;
}
function getFavoriteModelRefs() {
    const configured = vscode.workspace.getConfiguration("pi").get("favoriteModels") ?? [];
    const seen = new Set();
    const result = [];
    for (const value of configured) {
        if (typeof value !== "string")
            continue;
        const trimmed = value.trim();
        if (!trimmed)
            continue;
        const slashIndex = trimmed.indexOf("/");
        if (slashIndex <= 0 || slashIndex >= trimmed.length - 1)
            continue;
        const provider = trimmed.slice(0, slashIndex).trim();
        const id = trimmed.slice(slashIndex + 1).trim();
        if (!provider || !id)
            continue;
        const key = `${provider}/${id}`;
        if (seen.has(key))
            continue;
        seen.add(key);
        result.push({ provider, id });
    }
    return result;
}
function getFavoriteModelOrder() {
    const refs = getFavoriteModelRefs();
    return new Map(refs.map((ref, index) => [`${ref.provider}/${ref.id}`, index]));
}
function modelKey(model) {
    return `${model.provider}/${model.id}`;
}
const DEFAULT_FALLBACK_MODEL_PER_PROVIDER = {
    "amazon-bedrock": "us.anthropic.claude-opus-4-6-v1",
    anthropic: "claude-opus-4-6",
    openai: "gpt-5.4",
    "azure-openai-responses": "gpt-5.2",
    "openai-codex": "gpt-5.4",
    google: "gemini-2.5-pro",
    "google-gemini-cli": "gemini-2.5-pro",
    "google-antigravity": "gemini-3.1-pro-high",
    "google-vertex": "gemini-3-pro-preview",
    "github-copilot": "gpt-4o",
    openrouter: "openai/gpt-5.1-codex",
    "vercel-ai-gateway": "anthropic/claude-opus-4-6",
    xai: "grok-4-fast-non-reasoning",
    groq: "openai/gpt-oss-120b",
    cerebras: "zai-glm-4.7",
    zai: "glm-5",
    mistral: "devstral-medium-latest",
    minimax: "MiniMax-M2.7",
    "minimax-cn": "MiniMax-M2.7",
    huggingface: "moonshotai/Kimi-K2.5",
    opencode: "claude-opus-4-6",
    "opencode-go": "kimi-k2.5",
    "kimi-coding": "kimi-k2-thinking",
};
function buildFallbackModel(provider, modelId, models) {
    const providerModels = models.filter((m) => m.provider === provider);
    if (providerModels.length === 0)
        return undefined;
    const defaultModelId = DEFAULT_FALLBACK_MODEL_PER_PROVIDER[provider];
    const baseModel = defaultModelId
        ? providerModels.find((m) => m.id === defaultModelId) ?? providerModels[0]
        : providerModels[0];
    return {
        ...baseModel,
        id: modelId,
        name: modelId,
    };
}
function injectFavoriteFallbackModels(registry) {
    const allModels = registry.getAll();
    const registryAny = registry;
    const models = registryAny.models;
    if (!models)
        return;
    const existingKeys = new Set(allModels.map((model) => modelKey(model)));
    for (const favorite of getFavoriteModelRefs()) {
        const key = `${favorite.provider}/${favorite.id}`;
        if (existingKeys.has(key))
            continue;
        const fallback = buildFallbackModel(favorite.provider, favorite.id, allModels);
        if (!fallback)
            continue;
        existingKeys.add(key);
        models.push(fallback);
    }
}
function compareFavoriteModelOrder(left, right, favoriteOrder) {
    const leftIndex = favoriteOrder.get(modelKey(left));
    const rightIndex = favoriteOrder.get(modelKey(right));
    if (leftIndex === undefined && rightIndex === undefined)
        return 0;
    if (leftIndex === undefined)
        return 1;
    if (rightIndex === undefined)
        return -1;
    return leftIndex - rightIndex;
}
function resolveLogFilePath(globalStoragePath) {
    const logDir = path.join(globalStoragePath, "logs");
    try {
        fsSync.mkdirSync(logDir, { recursive: true });
    }
    catch {
        // ignore
    }
    return path.join(logDir, "pi-vscode-extension.log");
}
function resolveWorkspacePath(workspaceRoot, inputPath) {
    const resolved = path.resolve(workspaceRoot, inputPath);
    const relative = path.relative(workspaceRoot, resolved);
    if (relative.startsWith("..") || path.isAbsolute(relative)) {
        throw new Error("Path is outside the workspace.");
    }
    return resolved;
}
function normalizeWebText(input) {
    return input
        .replace(/<script[\s\S]*?<\/script>/gi, " ")
        .replace(/<style[\s\S]*?<\/style>/gi, " ")
        .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
        .replace(/<!--([\s\S]*?)-->/g, " ")
        .replace(/<\/(p|div|section|article|header|footer|main|nav|aside|h[1-6]|li|tr|table|blockquote)>/gi, "\n")
        .replace(/<br\s*\/?\s*>/gi, "\n")
        .replace(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi, (_match, href, text) => {
        const label = String(text).replace(/<[^>]+>/g, " ").trim();
        return label ? `${label} [${href}]` : String(href);
    })
        .replace(/<[^>]+>/g, " ")
        .replace(/[\t\r ]+/g, " ")
        .replace(/\n\s+/g, "\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}
function createTools(workspaceRoot, sdk, extensionRoot) {
    const { defineTool, Type, StringEnum } = sdk;
    const playwrightScript = path.join(extensionRoot, "scripts", "playwright-mcp.sh");
    async function runPlaywrightMcpCommand(args) {
        try {
            const { stdout, stderr } = await execFile("bash", [playwrightScript, ...args], {
                cwd: extensionRoot,
                env: { ...process.env },
            });
            return stdout.trim() || stderr.trim();
        }
        catch (error) {
            const execError = error;
            const stderr = execError.stderr ? String(execError.stderr).trim() : "";
            const stdout = execError.stdout ? String(execError.stdout).trim() : "";
            const message = execError.message ?? "Playwright MCP command failed.";
            throw new Error([message, stdout, stderr].filter(Boolean).join("\n").trim());
        }
    }
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
            const results = [];
            const max = params.maxResults ?? 50;
            const include = params.include ?? "**/*";
            const files = await vscode.workspace.findFiles(include, "**/node_modules/**", Math.max(max, 200));
            for (const file of files) {
                if (results.length >= max)
                    break;
                const fullPath = file.fsPath;
                let content;
                try {
                    content = await fs.readFile(fullPath, "utf8");
                }
                catch {
                    continue;
                }
                const lines = content.split(/\r?\n/);
                for (let index = 0; index < lines.length; index++) {
                    if (results.length >= max)
                        break;
                    const lineText = lines[index];
                    if (!lineText.includes(params.query))
                        continue;
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
    const openFileTool = defineTool({
        name: "open_file",
        label: "Open File",
        description: "Open a workspace file in the editor",
        parameters: Type.Object({
            path: Type.String({ description: "File path relative to the workspace root" }),
        }),
        execute: async (_toolCallId, params) => {
            const target = resolveWorkspacePath(workspaceRoot, params.path);
            const document = await vscode.workspace.openTextDocument(target);
            await vscode.window.showTextDocument(document, { preview: false });
            return {
                content: [{ type: "text", text: `Opened ${params.path}` }],
                details: { path: params.path },
            };
        },
    });
    const editFileTool = defineTool({
        name: "edit_file",
        label: "Edit File",
        description: "Edit a workspace file in the editor, opening it if needed.",
        parameters: Type.Object({
            path: Type.String({ description: "File path relative to the workspace root" }),
            content: Type.Optional(Type.String({ description: "Replace the entire file content" })),
            edits: Type.Optional(Type.Array(Type.Object({
                startLine: Type.Number({ description: "Start line (0-based)" }),
                startCharacter: Type.Number({ description: "Start character (0-based)" }),
                endLine: Type.Number({ description: "End line (0-based)" }),
                endCharacter: Type.Number({ description: "End character (0-based)" }),
                newText: Type.String({ description: "Replacement text" }),
            }))),
        }),
        execute: async (_toolCallId, params) => {
            const target = resolveWorkspacePath(workspaceRoot, params.path);
            const document = await vscode.workspace.openTextDocument(target);
            await vscode.window.showTextDocument(document, { preview: false });
            const workspaceEdit = new vscode.WorkspaceEdit();
            if (params.content !== undefined) {
                const start = new vscode.Position(0, 0);
                const end = new vscode.Position(document.lineCount, 0);
                workspaceEdit.replace(document.uri, new vscode.Range(start, end), params.content);
            }
            else if (params.edits && params.edits.length > 0) {
                for (const edit of params.edits) {
                    const range = new vscode.Range(new vscode.Position(edit.startLine, edit.startCharacter), new vscode.Position(edit.endLine, edit.endCharacter));
                    workspaceEdit.replace(document.uri, range, edit.newText);
                }
            }
            else {
                throw new Error("Either content or edits must be provided.");
            }
            const ok = await vscode.workspace.applyEdit(workspaceEdit);
            if (!ok) {
                throw new Error(`Failed to edit ${params.path}`);
            }
            await document.save();
            return {
                content: [{ type: "text", text: `Edited ${params.path}` }],
                details: { path: params.path, contentReplaced: params.content !== undefined, edits: params.edits?.length ?? 0 },
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
            replacements: Type.Array(Type.Object({
                oldText: Type.String(),
                newText: Type.String(),
            })),
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
    const playwrightMcpStartTool = defineTool({
        name: "playwright_mcp_start",
        label: "Start Playwright MCP",
        description: "Start the shared Playwright MCP server.",
        parameters: Type.Object({}),
        execute: async () => {
            const result = await runPlaywrightMcpCommand(["start"]);
            return {
                content: [{ type: "text", text: result }],
                details: { command: "start" },
            };
        },
    });
    const playwrightMcpStopTool = defineTool({
        name: "playwright_mcp_stop",
        label: "Stop Playwright MCP",
        description: "Stop the shared Playwright MCP server.",
        parameters: Type.Object({}),
        execute: async () => {
            const result = await runPlaywrightMcpCommand(["stop"]);
            return {
                content: [{ type: "text", text: result }],
                details: { command: "stop" },
            };
        },
    });
    const playwrightMcpStatusTool = defineTool({
        name: "playwright_mcp_status",
        label: "Playwright MCP Status",
        description: "Check whether the Playwright MCP server is running.",
        parameters: Type.Object({}),
        execute: async () => {
            try {
                const result = await runPlaywrightMcpCommand(["status"]);
                return {
                    content: [{ type: "text", text: result }],
                    details: { status: "ok" },
                };
            }
            catch (error) {
                return {
                    content: [{ type: "text", text: String(error) }],
                    details: { status: "stopped" },
                };
            }
        },
    });
    const playwrightMcpExecuteTool = defineTool({
        name: "playwright_mcp_execute",
        label: "Playwright MCP Execute",
        description: "Send a request to the Playwright MCP server.",
        parameters: Type.Object({
            method: Type.Optional(Type.String({ default: "POST" })),
            path: Type.Optional(Type.String({ default: "/execute" })),
            body: Type.Optional(Type.Any()),
            query: Type.Optional(Type.Record(Type.String(), Type.String())),
        }),
        execute: async (_toolCallId, params) => {
            const port = process.env.PLAYWRIGHT_MCP_PORT ?? "8931";
            const url = new URL(`http://localhost:${port}${params.path ?? "/execute"}`);
            if (params.query) {
                Object.entries(params.query).forEach(([key, value]) => url.searchParams.set(key, value));
            }
            const response = await fetch(url.toString(), {
                method: params.method ?? "POST",
                headers: { "content-type": "application/json" },
                body: params.body === undefined ? undefined : JSON.stringify(params.body),
            });
            const text = await response.text();
            if (!response.ok) {
                throw new Error(`Playwright MCP request failed: ${response.status} ${response.statusText}\n${text}`);
            }
            return {
                content: [{ type: "text", text }],
                details: { url: url.toString(), status: response.status },
            };
        },
    });
    const readWebPageTool = defineTool({
        name: "read_webpage",
        label: "Read Webpage",
        description: "Fetch a web page and return readable text",
        promptSnippet: "Read documentation pages and extract their readable text",
        promptGuidelines: [
            "Use this tool for public documentation pages, reference docs, and web articles.",
            "Prefer this tool when the user asks about open web pages or online documentation.",
        ],
        parameters: Type.Object({
            url: Type.String({ description: "http(s) URL to read" }),
            maxChars: Type.Optional(Type.Number({ description: "Maximum characters to return" })),
        }),
        execute: async (_toolCallId, params) => {
            const parsed = new URL(params.url);
            if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
                throw new Error("Only http and https URLs are supported.");
            }
            const response = await fetch(parsed.toString(), {
                headers: {
                    "user-agent": "Pi VS Code Extension/0.0.1",
                    accept: "text/html,application/xhtml+xml",
                },
            });
            if (!response.ok) {
                throw new Error(`Failed to fetch ${parsed.toString()}: ${response.status} ${response.statusText}`);
            }
            const html = await response.text();
            const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
            const title = titleMatch ? normalizeWebText(titleMatch[1]) : parsed.hostname;
            const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
            const source = bodyMatch ? bodyMatch[1] : html;
            const text = normalizeWebText(source);
            const maxChars = params.maxChars ?? 20000;
            const trimmed = text.length > maxChars ? `${text.slice(0, maxChars)}\n\n[truncated]` : text;
            return {
                content: [{ type: "text", text: `Title: ${title}\nURL: ${parsed.toString()}\n\n${trimmed}` }],
                details: {
                    url: parsed.toString(),
                    title,
                    truncated: text.length > maxChars,
                },
            };
        },
    });
    return [
        readFileTool,
        listDirTool,
        grepSearchTool,
        createDirectoryTool,
        createFileTool,
        openFileTool,
        editFileTool,
        replaceStringTool,
        multiReplaceTool,
        playwrightMcpStartTool,
        playwrightMcpStopTool,
        playwrightMcpStatusTool,
        playwrightMcpExecuteTool,
        readWebPageTool,
    ];
}
function getNonce() {
    let text = "";
    const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (let index = 0; index < 32; index++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
//# sourceMappingURL=extension.js.map