#!/usr/bin/env python3
"""CoRunner — small always-on runner for trusted tasks

- Runs only whitelisted tasks from `tasks.yml`.
- Listens on 127.0.0.1 and requires an API token (header `x-api-key`).
- Endpoints: GET /tasks (list), POST /run (run task_id or phrase)
"""

from __future__ import annotations
import os
import yaml
import logging
import subprocess
import shlex
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("CO_RUNNER_API_TOKEN", "changeme")
BASE_DIR = os.path.dirname(__file__)
TASKS_PATH = os.path.join(BASE_DIR, "tasks.yml")
LOG_PATH = os.path.join(BASE_DIR, "corunner.log")

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="CoRunner", docs_url="/docs")

class RunRequest(BaseModel):
    task_id: str | None = None
    phrase: str | None = None


def load_tasks():
    if not os.path.exists(TASKS_PATH):
        return {}
    with open(TASKS_PATH, "r") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("tasks", {})


@app.get("/tasks")
def list_tasks(x_api_key: str | None = Header(None)):
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Invalid API token")
    tasks = load_tasks()
    return {tid: {"description": v.get("description"), "phrases": v.get("phrases", [])} for tid, v in tasks.items()}


@app.post("/run")
def run(req: RunRequest, x_api_key: str | None = Header(None)):
    """Run task by task_id or by exact phrase match (case-insensitive)."""
    if x_api_key != API_TOKEN:
        raise HTTPException(401, "Invalid API token")

    tasks = load_tasks()

    cmd = None
    task_id = None

    if req.task_id:
        task_id = req.task_id
        entry = tasks.get(task_id)
        if not entry:
            raise HTTPException(404, f"task_id {task_id} not found")
        cmd = entry["command"]

    elif req.phrase:
        phrase = req.phrase.strip().lower()
        for tid, v in tasks.items():
            for p in v.get("phrases", []):
                if p.strip().lower() == phrase:
                    cmd = v["command"]
                    task_id = tid
                    break
            if cmd:
                break
        if not cmd:
            raise HTTPException(404, "phrase not matched to any task")
    else:
        raise HTTPException(400, "Provide `task_id` or `phrase` in JSON body")

    logging.info("Executing task %s -> %s", task_id, cmd)

    try:
        def find_venv_python_for_path(p: Path) -> str | None:
            """Search upward from `p` for a `.venv` directory and return its python executable if found."""
            for parent in p.resolve().parents:
                venv_dir = parent / '.venv'
                if venv_dir.is_dir():
                    candidate = venv_dir / 'bin' / 'python'
                    if candidate.exists():
                        return str(candidate)
            return None

        # If the command is a path to an existing file, handle directly.
        if os.path.exists(cmd):
            p = Path(cmd)
            # Python script -> prefer project's .venv python if available.
            if p.suffix == '.py':
                venv_python = find_venv_python_for_path(p)
                if venv_python:
                    logging.info("Using venv %s to run %s", venv_python, cmd)
                    proc = subprocess.run([venv_python, str(p)], capture_output=True, text=True)
                elif os.access(cmd, os.X_OK):
                    proc = subprocess.run([str(p)], capture_output=True, text=True)
                else:
                    # Fallback to the server interpreter
                    proc = subprocess.run([sys.executable, str(p)], capture_output=True, text=True)
            elif os.access(cmd, os.X_OK):
                proc = subprocess.run([str(p)], capture_output=True, text=True)
            else:
                # File exists but not executable; run via shell as a last resort
                proc = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True)
        else:
            # If it's a shell command, inspect for python script tokens to determine a venv.
            try:
                tokens = shlex.split(cmd)
            except Exception:
                tokens = []

            script_venv = None
            if tokens:
                for i, t in enumerate(tokens):
                    if t.endswith('.py') and os.path.exists(t):
                        v = find_venv_python_for_path(Path(t))
                        if v:
                            script_venv = (v, i)
                            break

            if script_venv:
                venv_python, script_index = script_venv
                new_cmd = [venv_python] + tokens[script_index:]
                logging.info("Using venv %s for script invocation: %s", venv_python, new_cmd)
                proc = subprocess.run(new_cmd, capture_output=True, text=True)
            else:
                # Fallback: run with bash -lc (still safe because commands are whitelisted in tasks.yml).
                proc = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True)
    except Exception as exc:
        logging.exception("Execution failed for %s", task_id)
        raise HTTPException(500, str(exc))

    logging.info("Task %s finished rc=%s", task_id, proc.returncode)

    return {
        "task_id": task_id,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("runner_server:app", host="127.0.0.1", port=8000, log_level="info", workers=1)