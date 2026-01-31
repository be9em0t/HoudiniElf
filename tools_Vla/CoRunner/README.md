# CoRunner — Local always-on runner

Purpose
- Run a small, always-on local service that executes a *whitelisted* set of scripts/commands quickly and safely.
- Ideal for agents or local hotkeys that should trigger scripts with minimal latency.

Key design points
- Whitelist-only: commands in `tasks.yml` are the only allowed actions.
- Local-only: binds to `127.0.0.1` (not exposed on the network).
- API token: requires `x-api-key` header.

Quick start
1. Copy `.env.example` to `.env` and set a strong `CO_RUNNER_API_TOKEN`.
2. Install Python deps: `pip install fastapi uvicorn pyyaml python-dotenv requests`
3. Start server for testing:

```bash
cd tools_Vla/CoRunner
python3 -m runner_server
# or (recommended for production-like):
uvicorn runner_server:app --host 127.0.0.1 --port 8000 --workers 1
```

4. From another shell you can run:

```bash
python tools_Vla/CoRunner/runner_cli.py list
python tools_Vla/CoRunner/runner_cli.py phrase "wake remote tuffbox"
```

Security notes
- Only add trusted commands to `tasks.yml`.
- Keep the service bound to `127.0.0.1`.
- Protect `CO_RUNNER_API_TOKEN` and restrict file permissions.

Auto-start (macOS)
- Use a LaunchAgent to start at login, or add a system service. A sample `com.user.corunner.plist` is provided.

Integration guidance for agents
- Keep the agent’s call minimal: always call the runner using the canonical `task_id` or exact `phrase` from `tasks.yml`.
- Avoid letting the agent craft shell commands — it should map user intent to an existing `task_id`.
