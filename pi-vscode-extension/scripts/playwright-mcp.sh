#!/usr/bin/env bash

set -euo pipefail

PORT="${PLAYWRIGHT_MCP_PORT:-8931}"
STATE_DIR="${PLAYWRIGHT_MCP_STATE_DIR:-$HOME/Library/Application Support/pi-vscode-extension/playwright-mcp}"
USER_DATA_DIR="${PLAYWRIGHT_MCP_USER_DATA_DIR:-$STATE_DIR/user-data}"
OUTPUT_DIR="${PLAYWRIGHT_MCP_OUTPUT_DIR:-$STATE_DIR/output}"
LOG_FILE="${PLAYWRIGHT_MCP_LOG_FILE:-$STATE_DIR/server.log}"
PID_FILE="${PLAYWRIGHT_MCP_PID_FILE:-$STATE_DIR/server.pid}"
MCP_BIN="${PLAYWRIGHT_MCP_BIN:-npx}"
MCP_PACKAGE="${PLAYWRIGHT_MCP_PACKAGE:-@playwright/mcp@0.0.70}"

mkdir -p "$STATE_DIR" "$USER_DATA_DIR" "$OUTPUT_DIR"

pid_is_running() {
	local pid="$1"
	[[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

start_server() {
	if [[ -f "$PID_FILE" ]]; then
		local existing_pid
		existing_pid="$(<"$PID_FILE")"
		if pid_is_running "$existing_pid"; then
			echo "Playwright MCP is already running on port $PORT (pid $existing_pid)."
			exit 0
		fi
		rm -f "$PID_FILE"
	fi

	echo "Starting Playwright MCP on port $PORT..."
	nohup "$MCP_BIN" --yes "$MCP_PACKAGE" \
		--port "$PORT" \
		--shared-browser-context \
		--user-data-dir "$USER_DATA_DIR" \
		--output-dir "$OUTPUT_DIR" \
		>"$LOG_FILE" 2>&1 &
	echo $! >"$PID_FILE"
	echo "Started pid $(<"$PID_FILE")"
	echo "Log: $LOG_FILE"
	echo "Profile: $USER_DATA_DIR"
}

stop_server() {
	if [[ ! -f "$PID_FILE" ]]; then
		echo "No PID file found. Nothing to stop."
		exit 0
	fi

	local pid
	pid="$(<"$PID_FILE")"
	if ! pid_is_running "$pid"; then
		echo "Process $pid is not running; removing stale PID file."
		rm -f "$PID_FILE"
		exit 0
	fi

	echo "Stopping Playwright MCP pid $pid..."
	kill "$pid"
	for _ in {1..30}; do
		if ! pid_is_running "$pid"; then
			rm -f "$PID_FILE"
			echo "Stopped."
			exit 0
		fi
		sleep 1
	done

	echo "Process did not exit cleanly; sending SIGKILL."
	kill -9 "$pid" || true
	rm -f "$PID_FILE"
}

status_server() {
	if [[ -f "$PID_FILE" ]]; then
		local pid
		pid="$(<"$PID_FILE")"
		if pid_is_running "$pid"; then
			echo "running pid=$pid port=$PORT"
			exit 0
		fi
		echo "stale pid file pid=$pid"
		exit 1
	fi

	echo "stopped"
	exit 1
}

logs_server() {
	touch "$LOG_FILE"
	tail -f "$LOG_FILE"
}

case "${1:-start}" in
	start)
		start_server
		;;
	stop)
		stop_server
		;;
	status)
		status_server
		;;
	logs)
		logs_server
		;;
	*)
		echo "Usage: $0 {start|stop|status|logs}"
		exit 2
		;;
esac