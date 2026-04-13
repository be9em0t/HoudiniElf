const vscode = acquireVsCodeApi();

const messagesEl = document.getElementById("PNL_Messages");
const inputEl = document.getElementById("TXT_UserInput");
const addBtn = document.getElementById("BTN_Add");
const sendBtn = document.getElementById("BTN_Send");
const selectModelBtn = document.getElementById("BTN_SelectModel");
const modelStatusEl = document.getElementById("TXT_ModelStatus");

let selectedModelLabel = "unknown";
let respondingModelLabel = "unknown";

const userInputPanel = document.getElementById("PNL_UserInput");
console.log("[Pi Sidebar] init", {
  userInputPanelPresent: !!userInputPanel,
  messagesPanel: !!messagesEl,
  inputElPresent: !!inputEl,
  addBtnPresent: !!addBtn,
  sendBtnPresent: !!sendBtn,
  selectModelBtnPresent: !!selectModelBtn,
});
if (userInputPanel) {
  console.log("[Pi Sidebar] PNL_UserInput computed style", window.getComputedStyle(userInputPanel));
}

let currentAssistantEl = null;

function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `PNL_Message ${role}`;

  const content = document.createElement("div");
  content.className = "TXT_MessageContent";
  content.textContent = text;

  wrapper.appendChild(content);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  console.log("[Pi Sidebar] appendMessage", { role, className: wrapper.className, text });
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

addBtn?.addEventListener("click", () => {
  vscode.postMessage({ type: "addInput" });
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
      selectedModelLabel = message.selectedModel || "unknown";
      if (selectModelBtn) {
        const label = message.name || "Select model";
        const labelEl = selectModelBtn.querySelector(".TXT_ModelLabel");
        if (labelEl) {
          labelEl.textContent = label;
        } else {
          selectModelBtn.textContent = label;
        }
        selectModelBtn.title = message.name || message.selectedModel || "Select model";
      }
      updateModelStatus();
      break;
    case "respondingModelInfo":
      respondingModelLabel = message.respondingModel || "unknown";
      selectedModelLabel = message.selectedModel || selectedModelLabel;
      updateModelStatus();
      break;
    case "error":
      appendMessage("error", message.text);
      currentAssistantEl = null;
      break;
    default:
      break;
  }
});

function updateModelStatus() {
  if (!modelStatusEl) return;
  modelStatusEl.textContent = `Selected: ${selectedModelLabel} · Responding: ${respondingModelLabel}`;
}
