#!/usr/bin/env python3
"""
Script Launcher GUI - A dynamic launcher for Python scripts with argparse support

This GUI automatically detects Python scripts in a ./tools directory and dynamically
generates forms based on each script's argparse configuration.

Requirements:
- Each script must expose a build_parser() function that returns an ArgumentParser
- PyQt6 must be installed (pip install PyQt6)

Author: Generated for HoudiniElf project
Date: November 2025
"""

import sys
import os
import importlib.util
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import argparse

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QPushButton, QTextEdit, QCheckBox,
    QLineEdit, QComboBox, QFileDialog, QFormLayout, QScrollArea,
    QSplitter, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


class ScriptRunner(QThread):
    """Thread for running scripts without blocking the GUI"""
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    
    def __init__(self, script_path: str, args: List[str]):
        super().__init__()
        self.script_path = script_path
        self.args = args
        
    def run(self):
        """Execute the script with provided arguments"""
        try:
            # Build command
            cmd = [sys.executable, self.script_path] + self.args
            
            self.output_signal.emit(f"Running: {' '.join(cmd)}\n")
            self.output_signal.emit("=" * 60 + "\n")
            
            # Run subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output in real-time
            while True:
                output = process.stdout.readline()
                if output:
                    self.output_signal.emit(output)
                elif process.poll() is not None:
                    break
                    
            # Get remaining output
            stdout, stderr = process.communicate()
            if stdout:
                self.output_signal.emit(stdout)
            if stderr:
                self.error_signal.emit(stderr)
                
            self.output_signal.emit("\n" + "=" * 60 + "\n")
            self.output_signal.emit(f"Process finished with exit code: {process.returncode}\n")
            self.finished_signal.emit(process.returncode)
            
        except Exception as e:
            self.error_signal.emit(f"Error running script: {str(e)}\n")
            self.finished_signal.emit(-1)


class ScriptLauncherGUI(QMainWindow):
    """Main GUI window for the script launcher"""
    
    def __init__(self):
        super().__init__()
        self.tools_dir = Path(__file__).parent / "tools"
        self.current_script_path: Optional[Path] = None
        self.current_parser: Optional[argparse.ArgumentParser] = None
        self.form_widgets: Dict[str, Any] = {}
        self.runner_thread: Optional[ScriptRunner] = None
        
        self.init_ui()
        self.load_scripts()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Script Launcher - Dynamic Argparse GUI")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Script list
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Form and output
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (30% left, 70% right)
        splitter.setSizes([350, 850])
        
    def create_left_panel(self) -> QWidget:
        """Create the left panel with script list"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Available Scripts")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Script list
        self.script_list = QListWidget()
        self.script_list.currentItemChanged.connect(self.on_script_selected)
        layout.addWidget(self.script_list)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Scripts")
        refresh_btn.clicked.connect(self.load_scripts)
        layout.addWidget(refresh_btn)
        
        # Info label
        self.tools_dir_label = QLabel(f"Tools folder: {self.tools_dir}")
        self.tools_dir_label.setWordWrap(True)
        self.tools_dir_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.tools_dir_label)
        
        return panel
        
    def create_right_panel(self) -> QWidget:
        """Create the right panel with form and output"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Script info
        self.script_info_label = QLabel("Select a script to begin")
        self.script_info_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(self.script_info_label)
        
        # Scrollable form area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        
        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        scroll_area.setWidget(self.form_widget)
        layout.addWidget(scroll_area)
        
        # Run button
        self.run_button = QPushButton("▶ Run Script")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_script)
        self.run_button.setMinimumHeight(40)
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.run_button)
        
        # Output log
        output_group = QGroupBox("Output Log")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        mono_font = QFont()
        mono_font.setFamily("Monaco")  # Standard macOS monospace font
        mono_font.setPointSize(10)
        self.output_text.setFont(mono_font)
        self.output_text.setMinimumHeight(200)
        output_layout.addWidget(self.output_text)
        
        # Clear output button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.output_text.clear)
        output_layout.addWidget(clear_btn)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        return panel
        
    def load_scripts(self):
        """Discover and load Python scripts from the tools directory"""
        self.script_list.clear()
        
        # Ensure tools directory exists
        if not self.tools_dir.exists():
            self.tools_dir.mkdir(parents=True, exist_ok=True)
            self.log_output(f"Created tools directory: {self.tools_dir}\n", "gray")
            return
            
        # Find Python scripts
        scripts = sorted(self.tools_dir.glob("*.py"))
        
        if not scripts:
            self.log_output("No scripts found in tools directory.\n", "gray")
            return
            
        for script in scripts:
            if script.name.startswith("__"):
                continue
            self.script_list.addItem(script.name)
            
        self.log_output(f"Loaded {len(scripts)} script(s) from {self.tools_dir}\n", "green")
        
    def on_script_selected(self, current, previous):
        """Handle script selection from the list"""
        if not current:
            return
            
        script_name = current.text()
        script_path = self.tools_dir / script_name
        
        try:
            self.load_script_parser(script_path)
        except Exception as e:
            self.log_output(f"Error loading script: {str(e)}\n", "red")
            QMessageBox.warning(self, "Script Load Error", 
                              f"Failed to load {script_name}:\n{str(e)}")
            
    def load_script_parser(self, script_path: Path):
        """Load a script and extract its argument parser"""
        self.current_script_path = script_path
        self.form_widgets.clear()
        
        # Clear previous form
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.log_output(f"\nLoading script: {script_path.name}\n", "blue")
        
        try:
            # Import the script as a module
            spec = importlib.util.spec_from_file_location("dynamic_script", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check for build_parser function
            if not hasattr(module, "build_parser"):
                raise AttributeError(
                    f"Script {script_path.name} must have a build_parser() function"
                )
                
            # Get the parser
            self.current_parser = module.build_parser()
            
            # Update UI
            self.script_info_label.setText(
                f"Script: {script_path.name}\n"
                f"Description: {self.current_parser.description or 'No description'}"
            )
            
            # Build form from parser
            self.build_form_from_parser(self.current_parser)
            self.run_button.setEnabled(True)
            
            self.log_output(f"Successfully loaded parser with {len(self.form_widgets)} arguments\n", "green")
            
        except Exception as e:
            self.log_output(f"Error: {str(e)}\n", "red")
            self.run_button.setEnabled(False)
            raise
            
    def build_form_from_parser(self, parser: argparse.ArgumentParser):
        """Dynamically build GUI form from ArgumentParser"""
        
        # Iterate through parser actions
        for action in parser._actions:
            # Skip help action
            if isinstance(action, argparse._HelpAction):
                continue
                
            # Skip version action
            if isinstance(action, argparse._VersionAction):
                continue
                
            # Get argument name
            arg_name = self.get_action_dest(action)
            if not arg_name:
                continue
                
            # Create widget based on action type
            widget = self.create_widget_for_action(action)
            if widget:
                label_text = self.format_label(action)
                self.form_layout.addRow(label_text, widget)
                self.form_widgets[arg_name] = (action, widget)
                
    def get_action_dest(self, action: argparse.Action) -> str:
        """Get the destination name for an action"""
        return action.dest if action.dest != argparse.SUPPRESS else None
        
    def format_label(self, action: argparse.Action) -> str:
        """Format a label for an action"""
        # Get primary name
        if action.option_strings:
            name = action.option_strings[0]
        else:
            name = action.dest
            
        # Add required marker
        if action.required:
            name += " *"
            
        # Add help text
        if action.help:
            name += f"\n({action.help})"
            
        return name
        
    def create_widget_for_action(self, action: argparse.Action) -> Optional[QWidget]:
        """Create appropriate widget for an argparse action"""
        
        # Boolean flags (store_true/store_false)
        if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
            checkbox = QCheckBox()
            default_val = action.default if action.default is not None else False
            checkbox.setChecked(default_val)
            return checkbox
            
        # Choice dropdown
        if action.choices:
            combo = QComboBox()
            combo.addItems([str(c) for c in action.choices])
            if action.default:
                index = combo.findText(str(action.default))
                if index >= 0:
                    combo.setCurrentIndex(index)
            return combo
            
        # File/directory path (heuristic based on name or type)
        if self.is_path_argument(action):
            return self.create_file_picker(action)
            
        # Numeric types
        if action.type in (int, float):
            line_edit = QLineEdit()
            if action.default is not None:
                line_edit.setText(str(action.default))
            line_edit.setPlaceholderText(f"Enter {action.type.__name__}")
            return line_edit
            
        # Default: text field
        line_edit = QLineEdit()
        if action.default is not None and action.default != argparse.SUPPRESS:
            line_edit.setText(str(action.default))
        if action.metavar:
            line_edit.setPlaceholderText(action.metavar)
        return line_edit
        
    def is_path_argument(self, action: argparse.Action) -> bool:
        """Determine if an argument is likely a file/directory path"""
        name_lower = action.dest.lower()
        path_keywords = ['file', 'path', 'dir', 'directory', 'input', 'output', 'folder']
        return any(keyword in name_lower for keyword in path_keywords)
        
    def create_file_picker(self, action: argparse.Action) -> QWidget:
        """Create a file picker widget"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        line_edit = QLineEdit()
        if action.default is not None and action.default != argparse.SUPPRESS:
            line_edit.setText(str(action.default))
            
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(
            lambda: self.browse_for_file(line_edit, action)
        )
        
        layout.addWidget(line_edit, stretch=3)
        layout.addWidget(browse_btn, stretch=1)
        
        # Store reference to line_edit for value retrieval
        container.line_edit = line_edit
        
        return container
        
    def browse_for_file(self, line_edit: QLineEdit, action: argparse.Action):
        """Open file browser dialog"""
        name_lower = action.dest.lower()
        
        # Determine if directory or file
        if 'dir' in name_lower or 'folder' in name_lower:
            path = QFileDialog.getExistingDirectory(self, f"Select {action.dest}")
        else:
            path, _ = QFileDialog.getOpenFileName(self, f"Select {action.dest}")
            
        if path:
            line_edit.setText(path)
            
    def collect_arguments(self) -> List[str]:
        """Collect arguments from form widgets"""
        args = []
        
        for arg_name, (action, widget) in self.form_widgets.items():
            value = self.get_widget_value(widget, action)
            
            # Handle different action types
            if isinstance(action, argparse._StoreTrueAction):
                if value:
                    args.extend(action.option_strings[:1])
            elif isinstance(action, argparse._StoreFalseAction):
                if not value:
                    args.extend(action.option_strings[:1])
            elif action.option_strings:
                # Optional argument with value
                if value is not None and value != "":
                    args.extend(action.option_strings[:1])
                    if action.type:
                        args.append(str(value))
                    else:
                        args.append(value)
            else:
                # Positional argument
                if value is not None and value != "":
                    args.append(str(value))
                elif action.required:
                    raise ValueError(f"Required argument '{arg_name}' is missing")
                    
        return args
        
    def get_widget_value(self, widget: QWidget, action: argparse.Action) -> Any:
        """Extract value from a widget"""
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QLineEdit):
            text = widget.text()
            # Convert to appropriate type
            if action.type == int:
                return int(text) if text else None
            elif action.type == float:
                return float(text) if text else None
            return text
        elif hasattr(widget, 'line_edit'):
            # File picker container
            return widget.line_edit.text()
        return None
        
    def run_script(self):
        """Execute the selected script with collected arguments"""
        if not self.current_script_path or not self.current_parser:
            return
            
        try:
            # Collect arguments
            args = self.collect_arguments()
            
            # Clear output
            self.output_text.clear()
            
            # Disable run button during execution
            self.run_button.setEnabled(False)
            self.run_button.setText("⏳ Running...")
            
            # Create and start runner thread
            self.runner_thread = ScriptRunner(str(self.current_script_path), args)
            self.runner_thread.output_signal.connect(
                lambda text: self.log_output(text, "black")
            )
            self.runner_thread.error_signal.connect(
                lambda text: self.log_output(text, "red")
            )
            self.runner_thread.finished_signal.connect(self.on_script_finished)
            self.runner_thread.start()
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))
            self.run_button.setEnabled(True)
        except Exception as e:
            self.log_output(f"Error preparing script: {str(e)}\n", "red")
            self.run_button.setEnabled(True)
            
    def on_script_finished(self, exit_code: int):
        """Handle script execution completion"""
        self.run_button.setEnabled(True)
        self.run_button.setText("▶ Run Script")
        
        if exit_code == 0:
            self.log_output("\n✓ Script completed successfully\n", "green")
        else:
            self.log_output(f"\n✗ Script failed with exit code {exit_code}\n", "red")
            
    def log_output(self, text: str, color: str = "black"):
        """Append text to output log with color"""
        from PyQt6.QtGui import QTextCursor
        
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
        
        color_map = {
            "black": "#000000",
            "red": "#cc0000",
            "green": "#00aa00",
            "blue": "#0000cc",
            "gray": "#666666"
        }
        
        html_color = color_map.get(color, "#000000")
        self.output_text.insertHtml(
            f'<span style="color: {html_color};">{text.replace("\n", "<br>")}</span>'
        )
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show window
    window = ScriptLauncherGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
