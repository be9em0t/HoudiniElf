# Script Launcher GUI

A dynamic Python GUI application that automatically generates user interfaces for Python scripts based on their `argparse` configurations.

## 🎯 Overview

This launcher provides a graphical interface for running command-line Python scripts without needing to remember argument syntax. Simply select a script from the list, and the GUI automatically creates appropriate input widgets based on the script's argument parser.

## 📋 Requirements

- Python 3.7+
- PyQt6

### Installation

```bash
pip install PyQt6
```

## 🚀 Usage

### Running the Launcher

```bash
python lcc_GUI.py
```

Or make it executable:
```bash
chmod +x lcc_GUI.py
./lcc_GUI.py
```

### How It Works

1. **Select a script** from the left panel
2. **Fill in the form** that appears automatically based on the script's arguments
3. **Click "Run Script"** to execute
4. **View output** in the log window at the bottom

## 📝 Creating Compatible Scripts

To make your script compatible with the launcher, it must expose a `build_parser()` function that returns an `ArgumentParser`:

```python
import argparse

def build_parser():
    """Build and return the argument parser"""
    parser = argparse.ArgumentParser(
        description="Your script description"
    )
    
    parser.add_argument("input_file", help="Input file path")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose mode")
    
    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()
    # Your script logic here

if __name__ == "__main__":
    main()
```

### Supported Argument Types

The launcher automatically creates appropriate widgets for:

| Argument Type | GUI Widget | Example |
|--------------|------------|---------|
| Boolean flags (`store_true`/`store_false`) | Checkbox | `--verbose` |
| Choices | Dropdown menu | `choices=["opt1", "opt2"]` |
| File/directory paths | Text field + Browse button | `input_file`, `--output-path` |
| Integers | Text field (numeric) | `type=int` |
| Floats | Text field (numeric) | `type=float` |
| Strings | Text field | Default type |
| Positional arguments | Text field | Required fields |

### Path Detection

The launcher automatically adds file picker buttons for arguments with names containing:
- `file`
- `path`
- `dir`/`directory`
- `folder`
- `input`
- `output`

## 📂 Directory Structure

```
SingleGUI/
├── lcc_GUI.py              # Main launcher application
├── tools/                  # Place your scripts here
│   ├── sample_text_processor.py
│   ├── simple_calculator.py
│   └── your_script.py
└── README.md
```

## 🎨 Features

- ✅ **Automatic GUI generation** from argparse configuration
- ✅ **Real-time output streaming** in log window
- ✅ **File picker dialogs** for path arguments
- ✅ **Error handling** with user-friendly messages
- ✅ **Multi-script support** - add unlimited scripts to tools/
- ✅ **Cross-platform** - works on Windows, macOS, and Linux
- ✅ **Non-blocking execution** - GUI remains responsive during script execution
- ✅ **Colored output** - distinguishes stdout, stderr, and status messages

## 📖 Example Scripts

### Simple Calculator (`simple_calculator.py`)

Demonstrates basic numeric inputs and choice dropdowns.

**Usage in GUI:**
1. Enter two numbers
2. Select operation (add/subtract/multiply/divide)
3. Set precision
4. Toggle verbose mode
5. Click Run

### Text Processor (`sample_text_processor.py`)

Demonstrates all argument types including file paths, flags, choices, and text inputs.

**Features:**
- Case conversion
- Text find/replace
- Line repetition
- Whitespace handling
- Multiple encoding options

## 🔧 Extending the Launcher

### Adding New Scripts

1. Create a Python script in the `tools/` directory
2. Add a `build_parser()` function that returns an `ArgumentParser`
3. Implement your script logic in a `main()` function
4. Restart the launcher or click "Refresh Scripts"

### Customizing Widget Generation

The widget creation logic is in the `create_widget_for_action()` method of `ScriptLauncherGUI`. You can extend it to support additional argument types or custom widget styles.

## 🐛 Troubleshooting

### Script doesn't appear in list
- Ensure the script is in the `tools/` directory
- Check that the filename ends with `.py`
- Click the "Refresh Scripts" button

### Script fails to load
- Verify the script has a `build_parser()` function
- Check for syntax errors in the script
- Look at the error message in the output log

### Arguments not showing correctly
- Ensure `build_parser()` returns an `ArgumentParser` object
- Check that argument definitions are valid
- Review the argument type and action settings

## 📄 License

This tool is part of the HoudiniElf project.

## 🤝 Contributing

To add new features or fix bugs:

1. Modify `lcc_GUI.py` as needed
2. Test with the sample scripts
3. Document any new features in this README

## 💡 Tips

- Use descriptive argument names for better UI labels
- Add help text to arguments - it shows in the form
- Mark required arguments with `required=True`
- Use `choices` for fixed options to get dropdown menus
- Include path keywords in argument names to get file pickers automatically
- Test your script's `build_parser()` function independently before adding to the launcher
