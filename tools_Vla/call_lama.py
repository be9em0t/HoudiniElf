import sys
import requests
import json
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QComboBox, QCheckBox, QLabel,
    QDialog, QFormLayout, QSpinBox, QColorDialog, QFontComboBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QTextCursor, QFont, QColor, QIcon, QTextCharFormat, QPixmap

# Configuration - will be overridden by settings
DEFAULT_OLLAMA_HOST = "192.168.1.28"
DEFAULT_OLLAMA_PORT = "11434"

# Get script directory for portable settings
SCRIPT_DIR = Path(__file__).parent
SETTINGS_FILE = SCRIPT_DIR / "callama.ini"
ICON_FILE = SCRIPT_DIR / "callama512.png"

# Create session for connection pooling
session = requests.Session()
session.headers.update({"Connection": "keep-alive"})


class StyleSettingsDialog(QDialog):
    """Dialog for customizing text styles."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Display Options")
        self.setModal(True)
        self.resize(500, 700)
        
        self.settings = QSettings(str(SETTINGS_FILE), QSettings.IniFormat)
        
        layout = QVBoxLayout(self)
        
        # Server settings
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        
        self.server_host = QLineEdit()
        self.server_host.setText(self.settings.value("server_host", DEFAULT_OLLAMA_HOST))
        server_layout.addRow("Host/IP:", self.server_host)
        
        self.server_port = QLineEdit()
        self.server_port.setText(self.settings.value("server_port", DEFAULT_OLLAMA_PORT))
        server_layout.addRow("Port:", self.server_port)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # User prompt styling
        user_group = QGroupBox("User Prompt Style")
        user_layout = QFormLayout()
        
        self.user_name = QLineEdit()
        self.user_name.setText(self.settings.value("user_name", "Hooman"))
        user_layout.addRow("Name:", self.user_name)
        
        self.user_font = QFontComboBox()
        self.user_font.setCurrentFont(QFont(self.settings.value("user_font", "Arial")))
        user_layout.addRow("Font:", self.user_font)
        
        self.user_size = QSpinBox()
        self.user_size.setRange(8, 72)
        self.user_size.setValue(int(self.settings.value("user_size", 11)))
        user_layout.addRow("Size:", self.user_size)
        
        self.user_bold = QCheckBox()
        self.user_bold.setChecked(self.settings.value("user_bold", "true") == "true")
        user_layout.addRow("Bold:", self.user_bold)
        
        self.user_italic = QCheckBox()
        self.user_italic.setChecked(self.settings.value("user_italic", "false") == "true")
        user_layout.addRow("Italic:", self.user_italic)
        
        self.user_color_btn = QPushButton("Choose Color")
        self.user_color = QColor(self.settings.value("user_color", "#2196F3"))
        self.user_color_btn.setStyleSheet(f"background-color: {self.user_color.name()};")
        self.user_color_btn.clicked.connect(self.choose_user_color)
        user_layout.addRow("Color:", self.user_color_btn)
        
        self.user_align = QComboBox()
        self.user_align.addItems(["Left", "Right"])
        self.user_align.setCurrentText(self.settings.value("user_align", "Right"))
        user_layout.addRow("Alignment:", self.user_align)
        
        self.user_spacing = QSpinBox()
        self.user_spacing.setRange(0, 50)
        self.user_spacing.setValue(int(self.settings.value("user_spacing", 10)))
        self.user_spacing.setSuffix(" px")
        user_layout.addRow("Spacing above:", self.user_spacing)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        # Assistant response styling
        assistant_group = QGroupBox("Assistant Response Style")
        assistant_layout = QFormLayout()
        
        self.assistant_name = QLineEdit()
        self.assistant_name.setText(self.settings.value("assistant_name", "Ollama"))
        assistant_layout.addRow("Name:", self.assistant_name)
        
        self.assistant_font = QFontComboBox()
        self.assistant_font.setCurrentFont(QFont(self.settings.value("assistant_font", "Arial")))
        assistant_layout.addRow("Font:", self.assistant_font)
        
        self.assistant_size = QSpinBox()
        self.assistant_size.setRange(8, 72)
        self.assistant_size.setValue(int(self.settings.value("assistant_size", 11)))
        assistant_layout.addRow("Size:", self.assistant_size)
        
        self.assistant_bold = QCheckBox()
        self.assistant_bold.setChecked(self.settings.value("assistant_bold", "false") == "true")
        assistant_layout.addRow("Bold:", self.assistant_bold)
        
        self.assistant_italic = QCheckBox()
        self.assistant_italic.setChecked(self.settings.value("assistant_italic", "false") == "true")
        assistant_layout.addRow("Italic:", self.assistant_italic)
        
        self.assistant_color_btn = QPushButton("Choose Color")
        self.assistant_color = QColor(self.settings.value("assistant_color", "#4CAF50"))
        self.assistant_color_btn.setStyleSheet(f"background-color: {self.assistant_color.name()};")
        self.assistant_color_btn.clicked.connect(self.choose_assistant_color)
        assistant_layout.addRow("Color:", self.assistant_color_btn)
        
        self.assistant_align = QComboBox()
        self.assistant_align.addItems(["Left", "Right"])
        self.assistant_align.setCurrentText(self.settings.value("assistant_align", "Left"))
        assistant_layout.addRow("Alignment:", self.assistant_align)
        
        self.assistant_spacing = QSpinBox()
        self.assistant_spacing.setRange(0, 50)
        self.assistant_spacing.setValue(int(self.settings.value("assistant_spacing", 10)))
        self.assistant_spacing.setSuffix(" px")
        assistant_layout.addRow("Spacing above:", self.assistant_spacing)
        
        assistant_group.setLayout(assistant_layout)
        layout.addWidget(assistant_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.ok_clicked)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def choose_user_color(self):
        color = QColorDialog.getColor(self.user_color, self)
        if color.isValid():
            self.user_color = color
            self.user_color_btn.setStyleSheet(f"background-color: {color.name()};")
    
    def choose_assistant_color(self):
        color = QColorDialog.getColor(self.assistant_color, self)
        if color.isValid():
            self.assistant_color = color
            self.assistant_color_btn.setStyleSheet(f"background-color: {color.name()};")
    
    def save_settings(self):
        """Save settings to persistent storage."""
        self.settings.setValue("server_host", self.server_host.text())
        self.settings.setValue("server_port", self.server_port.text())
        self.settings.setValue("user_name", self.user_name.text())
        self.settings.setValue("assistant_name", self.assistant_name.text())
        
        self.settings.setValue("user_font", self.user_font.currentFont().family())
        self.settings.setValue("user_size", self.user_size.value())
        self.settings.setValue("user_bold", "true" if self.user_bold.isChecked() else "false")
        self.settings.setValue("user_italic", "true" if self.user_italic.isChecked() else "false")
        self.settings.setValue("user_color", self.user_color.name())
        self.settings.setValue("user_align", self.user_align.currentText())
        self.settings.setValue("user_spacing", self.user_spacing.value())
        
        self.settings.setValue("assistant_font", self.assistant_font.currentFont().family())
        self.settings.setValue("assistant_size", self.assistant_size.value())
        self.settings.setValue("assistant_bold", "true" if self.assistant_bold.isChecked() else "false")
        self.settings.setValue("assistant_italic", "true" if self.assistant_italic.isChecked() else "false")
        self.settings.setValue("assistant_color", self.assistant_color.name())
        self.settings.setValue("assistant_align", self.assistant_align.currentText())
        self.settings.setValue("assistant_spacing", self.assistant_spacing.value())
    
    def apply_settings(self):
        """Apply settings without closing dialog."""
        self.save_settings()
        if self.parent():
            self.parent().refresh_display()
    
    def ok_clicked(self):
        """Save and close dialog."""
        self.save_settings()
        if self.parent():
            self.parent().refresh_display()
        self.accept()


class OllamaWorker(QThread):
    """Worker thread to handle Ollama API calls without blocking UI."""
    token_received = Signal(str)  # For streaming response tokens
    thinking_received = Signal(str)  # For thinking tokens
    response_complete = Signal(dict)  # Final stats
    error_occurred = Signal(str)
    
    def __init__(self, prompt, model, streaming=True, ollama_url="http://192.168.1.28:11434"):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.streaming = streaming
        self.ollama_url = ollama_url
    
    def run(self):
        try:
            if self.streaming:
                self._run_streaming()
            else:
                self._run_non_streaming()
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _run_streaming(self):
        resp = session.post(
            f"{self.ollama_url}/api/generate",
            json={"model": self.model, "prompt": self.prompt, "stream": True},
            stream=True,
            timeout=120
        )
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                
                # Emit thinking tokens (but we won't display them in chat)
                if data.get("thinking"):
                    self.thinking_received.emit(data["thinking"])
                
                # Emit response tokens
                if data.get("response"):
                    self.token_received.emit(data["response"])
                
                # Send final stats
                if data.get("done"):
                    self.response_complete.emit(data)
                    break
    
    def _run_non_streaming(self):
        resp = session.post(
            f"{self.ollama_url}/api/generate",
            json={"model": self.model, "prompt": self.prompt, "stream": False},
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Emit the full response at once
        if data.get("response"):
            self.token_received.emit(data["response"])
        
        self.response_complete.emit(data)


class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ollama Chat")
        self.resize(800, 600)
        
        # Set application icon
        if ICON_FILE.exists():
            icon = QIcon(str(ICON_FILE))
            self.setWindowIcon(icon)
            # Also set for the application (affects dock/taskbar)
            QApplication.instance().setWindowIcon(icon)
        
        self.current_worker = None
        self.models = []
        self.settings = QSettings(str(SETTINGS_FILE), QSettings.IniFormat)
        self.chat_history = []  # Store chat history for rebuilding
        
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Chat display area (full width)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        
        # Stats label
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.stats_label)
        
        # Controls row
        controls_layout = QHBoxLayout()
        
        # Model selector
        controls_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        controls_layout.addWidget(self.model_combo)
        
        # Streaming toggle
        self.streaming_checkbox = QCheckBox("Streaming")
        self.streaming_checkbox.setChecked(True)
        controls_layout.addWidget(self.streaming_checkbox)
        
        # Push settings button to the right
        controls_layout.addStretch()
        
        # Options button (gear icon)
        self.options_button = QPushButton("⚙")
        self.options_button.setFixedSize(32, 32)
        self.options_button.setToolTip("Display Options")
        self.options_button.clicked.connect(self.open_style_settings)
        controls_layout.addWidget(self.options_button)
        
        layout.addLayout(controls_layout)
        
        # Input area (multi-line with resizable height)
        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message here... (Enter to send, Shift+Enter for new line)")
        self.input_field.setMinimumHeight(60)  # At least 3 lines
        self.input_field.setMaximumHeight(200)  # Max height before scrolling
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("➤")
        self.send_button.setFixedSize(32, 32)
        self.send_button.setToolTip("Send message")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button, alignment=Qt.AlignBottom)
        
        layout.addLayout(input_layout)
        
        # Install event filter for input field
        self.input_field.installEventFilter(self)
        
        # Load models
        self.load_models()
        
        # Welcome message
        self.append_system_message("Connected to Ollama server. Ready to chat!")
    
    def eventFilter(self, obj, event):
        """Filter events for input field to handle Enter key."""
        if obj == self.input_field and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if event.modifiers() == Qt.ShiftModifier:
                    # Shift+Enter: insert new line (default behavior)
                    return False
                else:
                    # Enter alone: send message
                    self.send_message()
                    return True
        return super().eventFilter(obj, event)
    
    def open_style_settings(self):
        """Open the style settings dialog."""
        dialog = StyleSettingsDialog(self)
        dialog.exec()
    
    def refresh_display(self):
        """Refresh the display after settings change."""
        # Save current history
        saved_history = self.chat_history.copy()
        
        # Clear display and history
        self.chat_display.clear()
        self.chat_history = []
        
        # Reload models if server settings changed
        self.model_combo.clear()
        self.models = []
        self.load_models()
        
        # Rebuild chat history with new styles
        for msg_type, text in saved_history:
            if msg_type == "user":
                self.append_user_message(text)
            elif msg_type == "assistant":
                self.append_assistant_message(text)
            elif msg_type == "system":
                self.append_system_message(text)
    
    def load_models(self):
        """Load available models from Ollama server."""
        try:
            host = self.settings.value("server_host", DEFAULT_OLLAMA_HOST)
            port = self.settings.value("server_port", DEFAULT_OLLAMA_PORT)
            ollama_url = f"http://{host}:{port}"
            
            resp = session.get(f"{ollama_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.models = [model["name"] for model in data.get("models", [])]
            self.model_combo.addItems(self.models)
            
            if not self.models:
                self.append_system_message("Warning: No models found on server!")
        except Exception as e:
            self.append_system_message(f"Error loading models: {e}")
    
    def append_user_message(self, text):
        """Add user message to chat with custom styling."""
        self.chat_history.append(("user", text))
        
        user_name = self.settings.value("user_name", "Hooman")
        spacing = int(self.settings.value("user_spacing", 10))
        font_family = self.settings.value("user_font", "Arial")
        font_size = int(self.settings.value("user_size", 11))
        is_bold = self.settings.value("user_bold", "true") == "true"
        is_italic = self.settings.value("user_italic", "false") == "true"
        color = self.settings.value("user_color", "#2196F3")
        align = self.settings.value("user_align", "Right")
        
        weight = "bold" if is_bold else "normal"
        style = "italic" if is_italic else "normal"
        alignment = "right" if align == "Right" else "left"
        
        html = f"""
        <div style="margin-top: {spacing}px; text-align: {alignment};">
            <span style="font-family: {font_family}; font-size: {font_size}pt; 
                         font-weight: {weight}; font-style: {style}; color: {color};">
                <b>{user_name}:</b> {text}
            </span>
        </div>
        """
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)
    
    def append_assistant_message(self, text):
        """Add assistant message to chat with custom styling."""
        self.chat_history.append(("assistant", text))
        
        assistant_name = self.settings.value("assistant_name", "Ollama")
        spacing = int(self.settings.value("assistant_spacing", 10))
        font_family = self.settings.value("assistant_font", "Arial")
        font_size = int(self.settings.value("assistant_size", 11))
        is_bold = self.settings.value("assistant_bold", "false") == "true"
        is_italic = self.settings.value("assistant_italic", "false") == "true"
        color = self.settings.value("assistant_color", "#4CAF50")
        align = self.settings.value("assistant_align", "Left")
        
        weight = "bold" if is_bold else "normal"
        style = "italic" if is_italic else "normal"
        alignment = "right" if align == "Right" else "left"
        
        html = f"""
        <div style="margin-top: {spacing}px; text-align: {alignment};">
            <span style="font-family: {font_family}; font-size: {font_size}pt; 
                         font-weight: {weight}; font-style: {style}; color: {color};">
                <b>{assistant_name}:</b> {text}
            </span>
        </div>
        """
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)
    
    def append_system_message(self, text):
        """Add system message to chat."""
        self.chat_history.append(("system", text))
        self.chat_display.append(f"\n<i style='color: #888;'>{text}</i>")
        self.chat_display.moveCursor(QTextCursor.End)
    
    def append_token(self, token):
        """Append a token to the current response (for streaming)."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(token)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
    def send_message(self):
        """Send message to Ollama."""
        prompt = self.input_field.toPlainText().strip()
        if not prompt:
            return
        
        if self.current_worker and self.current_worker.isRunning():
            self.append_system_message("Please wait for the current response to complete.")
            return
        
        selected_model = self.model_combo.currentText()
        if not selected_model:
            self.append_system_message("Please select a model first!")
            return
        
        # Display user message
        self.append_user_message(prompt)
        self.input_field.clear()
        
        # Start assistant response
        self.append_assistant_message("")
        
        # Disable input while processing
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.stats_label.setText("Processing...")
        
        # Create worker thread
        streaming = self.streaming_checkbox.isChecked()
        host = self.settings.value("server_host", DEFAULT_OLLAMA_HOST)
        port = self.settings.value("server_port", DEFAULT_OLLAMA_PORT)
        ollama_url = f"http://{host}:{port}"
        
        self.current_worker = OllamaWorker(prompt, selected_model, streaming, ollama_url)
        self.current_worker.token_received.connect(self.on_token_received)
        self.current_worker.response_complete.connect(self.on_response_complete)
        self.current_worker.error_occurred.connect(self.on_error)
        self.current_worker.start()
    
    def on_token_received(self, token):
        """Handle received token from streaming."""
        self.append_token(token)
    
    def on_response_complete(self, data):
        """Handle response completion and display stats."""
        # Build stats string
        stats_parts = []
        if 'load_duration' in data and data['load_duration'] > 0:
            stats_parts.append(f"Load: {data['load_duration'] / 1e9:.2f}s")
        if 'prompt_eval_duration' in data:
            stats_parts.append(f"Prompt: {data['prompt_eval_duration'] / 1e9:.2f}s")
        if 'eval_duration' in data:
            stats_parts.append(f"Response: {data['eval_duration'] / 1e9:.2f}s")
        if 'total_duration' in data:
            stats_parts.append(f"Total: {data['total_duration'] / 1e9:.2f}s")
        
        stats_text = " | ".join(stats_parts) if stats_parts else "Complete"
        self.stats_label.setText(stats_text)
        
        # Re-enable input
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
    
    def on_error(self, error_msg):
        """Handle errors."""
        self.append_system_message(f"Error: {error_msg}")
        self.stats_label.setText("Error occurred")
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Ollama Chat")
    
    # Set application icon for dock/taskbar (backup if window icon fails)
    if ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(ICON_FILE)))
    
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
