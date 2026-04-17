# Development Setup for Pi VS Code Extension

This folder contains the Pi VS Code extension source and package metadata. The repository does not store `node_modules/` or the local Python virtual environment.

## Recreate Python virtual environment

1. Ensure you have Python 3.13+ installed.
2. From this folder:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install --upgrade pip
   if [ -s requirements.txt ]; then .venv/bin/python -m pip install -r requirements.txt; fi
   ```

## Recreate Node dependencies

1. From this folder:
   ```bash
   npm ci
   ```

## Build

1. Compile the TypeScript extension:
   ```bash
   npm run compile
   ```

2. If packaging the extension for VS Code:
   ```bash
   npm run package
   ```

## Notes

- `package-lock.json` is committed so `npm ci` should reproduce the same Node dependency tree.
- `requirements.txt` was generated from the current `.venv`; if it is empty, there are no additional Python packages beyond the venv bootstrap.
- Do not commit `node_modules/` or `.venv/.
