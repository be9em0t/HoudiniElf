# Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Script Launcher GUI                         │
│                        (lcc_GUI.py)                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────┐
        │      User Starts Application          │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Scan ./tools for .py files         │
        │    (load_scripts method)              │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Display script list in left panel  │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    User selects a script              │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Import script as module            │
        │    (importlib.util)                   │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Call script.build_parser()         │
        │    Returns: ArgumentParser object     │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Iterate through parser._actions    │
        │    (build_form_from_parser)           │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    For each action, create widget:    │
        │    • Boolean → QCheckBox              │
        │    • Choices → QComboBox              │
        │    • Path → QLineEdit + Browse        │
        │    • Int/Float → QLineEdit            │
        │    • String → QLineEdit               │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Display dynamic form in right panel│
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    User fills form & clicks Run       │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Collect values from widgets        │
        │    (collect_arguments)                │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Build command line args list       │
        │    e.g., ['--verbose', '--output',    │
        │          'file.txt', 'input.txt']     │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Create ScriptRunner thread         │
        │    (QThread for non-blocking)         │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Execute: python script.py [args]   │
        │    via subprocess.Popen               │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Stream stdout/stderr in real-time  │
        │    → Emit signals to GUI              │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Display output in log window       │
        │    • stdout → black text              │
        │    • stderr → red text                │
        │    • status → green/blue text         │
        └───────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │    Process finishes                   │
        │    Show exit code & re-enable button  │
        └───────────────────────────────────────┘
```

## Class Structure

```
ScriptLauncherGUI (QMainWindow)
│
├── __init__()
│   ├── tools_dir: Path to ./tools
│   ├── current_script_path: Currently selected script
│   ├── current_parser: Loaded ArgumentParser
│   ├── form_widgets: Dict of argument → (action, widget)
│   └── runner_thread: ScriptRunner instance
│
├── UI Components
│   ├── script_list: QListWidget (left panel)
│   ├── form_layout: QFormLayout (dynamic form)
│   ├── run_button: QPushButton
│   └── output_text: QTextEdit (log window)
│
├── Script Management
│   ├── load_scripts()              # Discover .py files
│   ├── on_script_selected()        # Handle selection
│   └── load_script_parser()        # Import & extract parser
│
├── Form Generation
│   ├── build_form_from_parser()    # Main form builder
│   ├── create_widget_for_action()  # Widget factory
│   ├── is_path_argument()          # Path detection
│   └── create_file_picker()        # File browser widget
│
├── Execution
│   ├── run_script()                # Start execution
│   ├── collect_arguments()         # Gather form values
│   ├── get_widget_value()          # Extract widget values
│   └── on_script_finished()        # Handle completion
│
└── Output
    └── log_output()                # Colored text output

ScriptRunner (QThread)
│
├── output_signal: pyqtSignal(str)     # For stdout
├── error_signal: pyqtSignal(str)      # For stderr
├── finished_signal: pyqtSignal(int)   # For exit code
│
└── run()                               # Execute subprocess
```

## Widget Creation Logic Flow

```
create_widget_for_action(action)
    │
    ├─ Is store_true/store_false?
    │   └─→ Return QCheckBox
    │
    ├─ Has choices?
    │   └─→ Return QComboBox
    │
    ├─ Is path argument?
    │   └─→ Return QWidget(QLineEdit + QPushButton)
    │
    ├─ Type is int or float?
    │   └─→ Return QLineEdit (with numeric validation)
    │
    └─ Default:
        └─→ Return QLineEdit
```

## Argument Collection Logic Flow

```
collect_arguments()
    │
    └─ For each (action, widget) in form_widgets:
        │
        ├─ Get value from widget
        │   ├─ QCheckBox → isChecked()
        │   ├─ QComboBox → currentText()
        │   ├─ QLineEdit → text()
        │   └─ File picker → line_edit.text()
        │
        ├─ Format based on action type:
        │   ├─ store_true → ['--flag'] if checked
        │   ├─ store_false → ['--flag'] if not checked
        │   ├─ Optional → ['--option', 'value']
        │   └─ Positional → ['value']
        │
        └─ Append to args list

    Return: Complete args list
```

## Script Requirements

```python
# Every compatible script must have:

def build_parser():
    """
    Required function that the GUI calls.
    Must return an ArgumentParser object.
    """
    parser = argparse.ArgumentParser(...)
    parser.add_argument(...)
    return parser  # ← Must return this

def main():
    """Main logic goes here"""
    parser = build_parser()
    args = parser.parse_args()
    # ... your code ...
    return 0  # Exit code

if __name__ == "__main__":
    sys.exit(main())
```

## Data Flow

```
Script File (.py)
    ↓
[importlib.util.spec_from_file_location]
    ↓
Python Module Object
    ↓
[module.build_parser()]
    ↓
ArgumentParser Object
    ↓
[parser._actions iteration]
    ↓
List of Action Objects
    ↓
[create_widget_for_action()]
    ↓
QWidget Objects in Form
    ↓
[User interaction]
    ↓
[collect_arguments()]
    ↓
List of String Arguments
    ↓
[subprocess.Popen()]
    ↓
Process Execution
    ↓
[stdout/stderr streams]
    ↓
[Signal emission]
    ↓
GUI Log Display
```

## Threading Model

```
Main Thread (GUI)
    │
    ├─ UI Rendering
    ├─ Event Handling
    ├─ Form Generation
    │
    └─ When "Run" clicked:
        │
        └─→ Create ScriptRunner(QThread)
            │
            ├─ Run in separate thread
            │   ├─ subprocess.Popen()
            │   ├─ Read stdout/stderr
            │   └─ Emit signals
            │
            └─→ Signals received by main thread
                │
                └─ Update GUI (log_output())
```

## File System Structure

```
SingleGUI/
│
├── lcc_GUI.py                  ← Main application
│   └── Contains:
│       ├── ScriptLauncherGUI class
│       ├── ScriptRunner class
│       └── main() entry point
│
├── tools/                      ← Scripts directory
│   ├── simple_calculator.py    ← Example scripts
│   ├── sample_text_processor.py
│   └── your_script.py          ← User adds here
│
└── Documentation
    ├── README.md               ← User guide
    ├── SCRIPT_TEMPLATE.md      ← Developer guide
    └── PROJECT_SUMMARY.md      ← Technical overview
```

## Signal Flow (Threading)

```
ScriptRunner Thread          Main GUI Thread
      │                            │
      │  output_signal.emit("text")│
      ├─────────────────────────→  │
      │                            │ log_output("text")
      │                            ├─→ Update QTextEdit
      │                            │
      │  error_signal.emit("err")  │
      ├─────────────────────────→  │
      │                            │ log_output("err", "red")
      │                            ├─→ Update QTextEdit
      │                            │
      │  finished_signal.emit(0)   │
      ├─────────────────────────→  │
      │                            │ on_script_finished(0)
      │                            ├─→ Enable run button
      │                            └─→ Show status message
      │
    [Exit]                         │
                              [Continue running]
```
