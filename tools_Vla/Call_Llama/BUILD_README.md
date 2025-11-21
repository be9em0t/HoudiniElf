# Building Ollama Chat

This guide explains how to build standalone executables of Ollama Chat for distribution.

## Prerequisites

1. **Python 3.8 or newer** installed
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

## Building

### macOS / Linux

```bash
chmod +x build.sh
./build.sh
```

Output: `dist/Ollama Chat.app` (macOS) or `dist/Ollama Chat` (Linux)

### Windows

```cmd
build.bat
```

Output: `dist\Ollama Chat.exe`

## Distribution

### What to share:

**macOS:**
- Share the entire `Ollama Chat.app` bundle (right-click → Compress to create a .zip)
- Recipients can drag it to Applications folder

**Windows:**
- Share `Ollama Chat.exe`
- Users can run it directly - no installation needed

**Linux:**
- Share `Ollama Chat` executable
- Users may need to: `chmod +x "Ollama Chat" && ./Ollama\ Chat`

### Settings File

On first run, `callama.ini` will be created in:
- **macOS/Linux:** Same directory as the .app/executable
- **Windows:** Same directory as the .exe

Users can share their `callama.ini` to transfer settings.

## Troubleshooting

### "Application can't be opened" (macOS)

If macOS blocks the app:
```bash
xattr -cr "dist/Ollama Chat.app"
```

### Missing icon

If `callama512.png` is not found, the build will proceed without an icon.

### Import errors

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Large file size

The executable includes Python interpreter + all dependencies. Typical size: 40-80 MB.

To reduce size, use `--onedir` instead of `--onefile` in the build scripts (creates a folder with multiple files instead of single executable).

## Development Mode

To run without building:
```bash
python call_lama.py
```

## Clean Build

To start fresh:
```bash
# macOS/Linux
rm -rf build dist *.spec

# Windows
rmdir /s /q build dist
del *.spec
```
