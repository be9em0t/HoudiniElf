from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    class FastMCP:  # type: ignore[no-redef]
        def __init__(self, name: str) -> None:
            self.name = name

        def tool(self):
            def decorator(func):
                return func

            return decorator

        def run(self) -> None:
            raise RuntimeError(
                "mcp package is required at runtime. Start with: uv run --with mcp python <server.py>"
            )

mcp = FastMCP("copilot-bridge-mcp")

DEFAULT_MEMORY_FILE = Path.home() / ".codex" / "memory" / "copilot_bridge_memory.json"
DEFAULT_RESTART_STATE_FILE = Path.home() / ".codex" / "state" / "vscode_restart_state.json"
DEFAULT_COPILOT_MEMORY_FILE = (
    Path.home()
    / "Applications/VS Code Portable/code-portable-data/user-data/User/globalStorage"
    / "github.copilot-chat/memory-tool/memories/debugging.md"
)
CODEX_PREFIX = "[codex:"


@dataclass
class UsageMatch:
    file: str
    line: int
    content: str


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _empty(self) -> dict[str, list[dict[str, Any]]]:
        return {"items": []}

    def _load_json(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return self._empty()
        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
            raise ValueError(f"Invalid memory file schema: {self.path}")
        return data

    def _save_json(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def _parse_markdown_items(self, text: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            payload = stripped[2:].strip()
            item: dict[str, Any] = {
                "key": None,
                "value": payload,
                "tags": ["copilot_markdown"],
                "updated_at": None,
            }
            match = re.match(r"^\[codex:(?P<key>[^\]]+)\]\s+(?P<value>.*)$", payload)
            if match:
                item["key"] = match.group("key")
                item["value"] = match.group("value")
                item["tags"] = ["codex", "copilot_markdown"]
            items.append(item)
        return items

    def _load_markdown(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return self._empty()
        raw = self.path.read_text(encoding="utf-8")
        return {"items": self._parse_markdown_items(raw)}

    def load(self) -> dict[str, list[dict[str, Any]]]:
        if self.path.suffix.lower() == ".md":
            return self._load_markdown()
        return self._load_json()

    def _save_markdown(self, data: dict[str, list[dict[str, Any]]]) -> None:
        existing_lines: list[str] = []
        if self.path.exists():
            existing_lines = self.path.read_text(encoding="utf-8").splitlines()
        kept = []
        for line in existing_lines:
            if line.strip().startswith(f"- {CODEX_PREFIX}"):
                continue
            kept.append(line)
        codex_lines = []
        for item in data["items"]:
            key = item.get("key")
            value = str(item.get("value", ""))
            if key:
                codex_lines.append(f"- [codex:{key}] {value}")
        merged = kept[:]
        if merged and merged[-1].strip():
            merged.append("")
        merged.extend(codex_lines)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(merged).rstrip() + "\n", encoding="utf-8")

    def save(self, data: dict[str, list[dict[str, Any]]]) -> None:
        if self.path.suffix.lower() == ".md":
            self._save_markdown(data)
            return
        self._save_json(data)


STORE = MemoryStore(DEFAULT_MEMORY_FILE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_items() -> list[dict[str, Any]]:
    data = STORE.load()
    return data["items"]


def _save_memory_items(items: list[dict[str, Any]]) -> None:
    STORE.save({"items": items})


@mcp.tool()
def memory(
    action: str,
    key: str | None = None,
    value: str | None = None,
    tags: list[str] | None = None,
    query: str | None = None,
    limit: int = 50,
) -> dict[str, object]:
    """Manage persistent memory entries. Actions: upsert, get, delete, list, search, clear."""
    normalized = action.strip().lower()

    if normalized == "upsert":
        if not key:
            raise ValueError("'key' is required for action=upsert")
        if value is None:
            raise ValueError("'value' is required for action=upsert")
        items = _memory_items()
        updated = False
        for item in items:
            if item.get("key") == key:
                item["value"] = value
                item["tags"] = tags or []
                item["updated_at"] = _now_iso()
                updated = True
                break
        if not updated:
            items.append(
                {
                    "key": key,
                    "value": value,
                    "tags": tags or [],
                    "updated_at": _now_iso(),
                }
            )
        _save_memory_items(items)
        return {"ok": True, "action": "upsert", "key": key, "updated": updated}

    if normalized == "get":
        if not key:
            raise ValueError("'key' is required for action=get")
        for item in _memory_items():
            if item.get("key") == key:
                return {"ok": True, "action": "get", "item": item}
        return {"ok": False, "action": "get", "key": key, "error": "not_found"}

    if normalized == "delete":
        if not key:
            raise ValueError("'key' is required for action=delete")
        items = _memory_items()
        kept = [item for item in items if item.get("key") != key]
        deleted = len(kept) != len(items)
        if deleted:
            _save_memory_items(kept)
        return {"ok": True, "action": "delete", "key": key, "deleted": deleted}

    if normalized == "clear":
        _save_memory_items([])
        return {"ok": True, "action": "clear"}

    if normalized == "list":
        items = sorted(_memory_items(), key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return {"ok": True, "action": "list", "count": len(items), "items": items[: max(1, limit)]}

    if normalized == "search":
        if not query:
            raise ValueError("'query' is required for action=search")
        needle = query.lower()
        matches = []
        for item in _memory_items():
            key_text = str(item.get("key", "")).lower()
            value_text = str(item.get("value", "")).lower()
            tags_text = " ".join(str(tag).lower() for tag in item.get("tags", []))
            if needle in key_text or needle in value_text or needle in tags_text:
                matches.append(item)
        matches.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return {"ok": True, "action": "search", "query": query, "count": len(matches), "items": matches[: max(1, limit)]}

    raise ValueError("Unsupported action. Use: upsert, get, delete, list, search, clear")


def _run_rg(pattern: str, root_path: str, list_files_only: bool = False) -> list[str]:
    cmd = [
        "rg",
        "--line-number",
        "--with-filename",
        "--no-heading",
        "--color",
        "never",
        pattern,
        root_path,
    ]
    if list_files_only:
        cmd = ["rg", "-l", "--color", "never", pattern, root_path]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "rg failed")
    out = result.stdout.strip()
    if not out:
        return []
    return out.splitlines()


def _write_restart_state(
    workspace: Path,
    session_note: str | None,
    state_file: Path,
    mode: str,
    app_name: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp_utc": _now_iso(),
        "workspace_path": str(workspace),
        "cwd": str(Path.cwd()),
        "mode": mode,
        "app_name": app_name,
        "session_note": (session_note or "").strip(),
        "resume_prompt": (
            "Please continue the previous session after VS Code restart. "
            "If needed, read this restart state file for context."
        ),
    }
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return payload


def _create_macos_restart_script(workspace: Path, app_name: str, delay_sec: float) -> Path:
    # Detached script survives the MCP process termination caused by app quit.
    script_path = Path(tempfile.gettempdir()) / f"codex-vscode-restart-{uuid.uuid4().hex}.sh"
    script = f"""#!/usr/bin/env bash
set -euo pipefail
sleep {delay_sec}
osascript -e 'tell application "{app_name}" to quit' >/dev/null 2>&1 || true
sleep 1
open -a {shlex.quote(app_name)} {shlex.quote(str(workspace))} >/dev/null 2>&1 || open {shlex.quote(str(workspace))} >/dev/null 2>&1
rm -- "$0" >/dev/null 2>&1 || true
"""
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o700)
    return script_path


def _launch_detached(script_path: Path) -> None:
    with open(os.devnull, "w", encoding="utf-8") as sink:
        subprocess.Popen(
            ["/bin/bash", str(script_path)],
            stdout=sink,
            stderr=sink,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )


@mcp.tool()
def vscode_listCodeUsages(
    symbol: str,
    root_path: str = ".",
    max_results: int = 200,
    case_sensitive: bool = False,
) -> dict[str, object]:
    """Find code usages of a symbol in workspace files using ripgrep."""
    if not symbol.strip():
        raise ValueError("'symbol' cannot be empty")

    escaped = re.escape(symbol)
    pattern = rf"\b{escaped}\b"
    if not case_sensitive:
        pattern = rf"(?i){pattern}"

    lines = _run_rg(pattern=pattern, root_path=root_path, list_files_only=False)
    matches: list[UsageMatch] = []

    for line in lines:
        split = line.split(":", 2)
        if len(split) != 3:
            continue
        file_path, line_no_raw, content = split
        if not line_no_raw.isdigit():
            continue
        matches.append(UsageMatch(file=file_path, line=int(line_no_raw), content=content))
        if len(matches) >= max_results:
            break

    files = sorted({m.file for m in matches})
    return {
        "ok": True,
        "symbol": symbol,
        "root_path": str(Path(root_path).resolve()),
        "count": len(matches),
        "files_count": len(files),
        "files": files,
        "matches": [m.__dict__ for m in matches],
    }


@mcp.tool()
def vscode_renameSymbol(
    old_name: str,
    new_name: str,
    root_path: str = ".",
    dry_run: bool = True,
    max_files: int = 200,
    case_sensitive: bool = True,
) -> dict[str, object]:
    """Rename symbol occurrences across files in a workspace using whole-word matching."""
    if not old_name.strip() or not new_name.strip():
        raise ValueError("'old_name' and 'new_name' must be non-empty")
    if old_name == new_name:
        return {"ok": True, "changed_files": 0, "changes": [], "note": "old_name equals new_name"}

    escaped = re.escape(old_name)
    pattern = rf"\b{escaped}\b"
    rg_pattern = pattern if case_sensitive else rf"(?i){pattern}"
    candidate_files = _run_rg(pattern=rg_pattern, root_path=root_path, list_files_only=True)

    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(pattern, flags)

    changes: list[dict[str, object]] = []

    for raw_path in candidate_files[:max_files]:
        path = Path(raw_path)
        if not path.is_file():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated, count = regex.subn(new_name, original)
        if count == 0:
            continue
        changes.append({"file": str(path), "replacements": count})
        if not dry_run:
            path.write_text(updated, encoding="utf-8")

    return {
        "ok": True,
        "old_name": old_name,
        "new_name": new_name,
        "dry_run": dry_run,
        "changed_files": len(changes),
        "changes": changes,
    }


@mcp.tool()
def resolve_memory_file_uri(path_or_uri: str | None = None) -> dict[str, object]:
    """Resolve a memory file path/URI to absolute path and file URI."""
    raw = (path_or_uri or "").strip()

    if not raw:
        resolved = DEFAULT_COPILOT_MEMORY_FILE.expanduser().resolve()
    elif raw.startswith("file://"):
        parsed = urlparse(raw)
        resolved = Path(unquote(parsed.path)).expanduser().resolve()
    else:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = DEFAULT_COPILOT_MEMORY_FILE.parent / candidate
        resolved = candidate.resolve()

    return {
        "ok": True,
        "input": path_or_uri,
        "resolved_path": str(resolved),
        "resolved_uri": resolved.as_uri(),
        "exists": resolved.exists(),
        "is_file": resolved.is_file(),
    }


@mcp.tool()
def vscode_restart(
    workspace_path: str = ".",
    session_note: str | None = None,
    dry_run: bool = False,
    app_name: str = "Visual Studio Code",
    relaunch_delay_sec: float = 0.8,
    state_file: str | None = None,
) -> dict[str, object]:
    """Restart VS Code on macOS and reopen the same workspace, with a handoff state file for session continuity."""
    workspace = Path(workspace_path).expanduser().resolve()
    if not workspace.exists():
        raise ValueError(f"workspace_path does not exist: {workspace}")

    platform_name = os.uname().sysname.lower()
    if platform_name != "darwin":
        return {
            "ok": False,
            "error": "unsupported_platform",
            "platform": platform_name,
            "note": "vscode_restart currently supports macOS only.",
        }

    target_state = Path(state_file).expanduser().resolve() if state_file else DEFAULT_RESTART_STATE_FILE
    state_payload = _write_restart_state(
        workspace=workspace,
        session_note=session_note,
        state_file=target_state,
        mode="hard_restart",
        app_name=app_name,
    )

    script_path = _create_macos_restart_script(
        workspace=workspace,
        app_name=app_name,
        delay_sec=max(0.2, float(relaunch_delay_sec)),
    )

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "workspace_path": str(workspace),
            "platform": platform_name,
            "app_name": app_name,
            "restart_script": str(script_path),
            "restart_state_file": str(target_state),
            "state": state_payload,
            "resume_hint": (
                "After restart, ask Codex to read the restart state file and continue from previous context."
            ),
        }

    _launch_detached(script_path)

    return {
        "ok": True,
        "dry_run": False,
        "workspace_path": str(workspace),
        "platform": platform_name,
        "app_name": app_name,
        "restart_state_file": str(target_state),
        "note": "Restart has been scheduled. This MCP session will likely disconnect momentarily.",
        "resume_hint": (
            "After VS Code relaunches, ask Codex to continue from the restart state file."
        ),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge MCP for memory + code usage + rename tools")
    parser.add_argument(
        "--memory-file",
        default=str(DEFAULT_COPILOT_MEMORY_FILE),
        help="Path to memory file (.md for Copilot-compatible markdown, .json for key/value JSON).",
    )
    return parser


def main() -> None:
    global STORE
    args = build_arg_parser().parse_args()
    STORE = MemoryStore(Path(args.memory_file).expanduser().resolve())
    mcp.run()


if __name__ == "__main__":
    main()
