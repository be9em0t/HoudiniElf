const vscode = acquireVsCodeApi();

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const modelValueEl = document.getElementById("model-value");
const selectModelBtn = document.getElementById("select-model");

let currentAssistantEl = null;

function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const content = document.createElement("div");
  content.className = "content";
  content.textContent = text;

  wrapper.appendChild(content);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return content;
}

function appendAssistantDelta(text) {
  if (!currentAssistantEl) {
    currentAssistantEl = appendMessage("assistant", "");
  }
  currentAssistantEl.textContent += text;
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function sendComposerMessage() {
  const text = inputEl.value.trim();
  if (!text) return;
  vscode.postMessage({ type: "userMessage", text });
  inputEl.value = "";
  inputEl.focus();
}

sendBtn.addEventListener("click", () => {
  sendComposerMessage();
});

selectModelBtn?.addEventListener("click", () => {
  vscode.postMessage({ type: "selectModel" });
});

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    if (event.shiftKey) {
      return; // allow newline
    }
    event.preventDefault();
    sendComposerMessage();
  }
});

window.addEventListener("message", (event) => {
  const message = event.data;
  if (!message || typeof message.type !== "string") return;

  switch (message.type) {
    case "userMessage":
      appendMessage("user", message.text);
      currentAssistantEl = null;
      break;
    case "assistantStart":
      currentAssistantEl = appendMessage("assistant", "");
      break;
    case "assistantDelta":
      appendAssistantDelta(message.text);
      break;
    case "assistantEnd":
      currentAssistantEl = null;
      break;
    case "modelInfo":
      if (modelValueEl) {
        const label = message.model || "unknown";
        const name = message.name ? ` (${message.name})` : "";
        modelValueEl.textContent = `${label}${name}`;
      }
      break;
    case "error":
      appendMessage("error", message.text);
      currentAssistantEl = null;
      break;
    default:
      break;
  }
});
