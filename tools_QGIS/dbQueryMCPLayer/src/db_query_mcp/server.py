from __future__ import annotations

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import AppConfig, ConnectionConfig, load_config
from .guards import preview_sql as inspect_sql
from .keychain import read_generic_password


CONFIG: AppConfig | None = None
mcp = FastMCP("tomtom-db-query-mcp")


def _require_config() -> AppConfig:
    if CONFIG is None:
        raise RuntimeError("Server config has not been loaded.")
    return CONFIG


def _find_connection(name: str) -> ConnectionConfig:
    config = _require_config()
    for connection in config.connections:
        if connection.name == name:
            return connection
    available = ", ".join(item.name for item in config.connections)
    raise ValueError(f"Unknown connection {name!r}. Available: {available}")


def _get_adapter(name: str):
    connection = _find_connection(name)
    secret = read_generic_password(
        service=connection.keychain.service,
        account=connection.keychain.account,
    )
    if connection.kind == "databricks":
        from .adapters.databricks_adapter import DatabricksAdapter

        return DatabricksAdapter(connection.options, secret)
    if connection.kind == "postgres":
        from .adapters.postgres_adapter import PostgresAdapter

        return PostgresAdapter(connection.options, secret)
    raise ValueError(f"Unsupported connection kind: {connection.kind}")


@mcp.tool()
def list_connections() -> list[dict[str, object]]:
    """List configured read-only database connections."""
    config = _require_config()
    return [
        {
            "name": item.name,
            "kind": item.kind,
            "description": item.description,
        }
        for item in config.connections
    ]


@mcp.tool()
def list_catalogs(connection_name: str) -> list[dict[str, object]]:
    """List catalogs for a configured connection."""
    adapter = _get_adapter(connection_name)
    return adapter.list_catalogs()


@mcp.tool()
def list_schemas(
    connection_name: str,
    catalog_name: str | None = None,
) -> list[dict[str, object]]:
    """List schemas for a configured connection."""
    adapter = _get_adapter(connection_name)
    return adapter.list_schemas(catalog_name=catalog_name)


@mcp.tool()
def describe_table(
    connection_name: str,
    schema_name: str,
    table_name: str,
    catalog_name: str | None = None,
) -> list[dict[str, object]]:
    """Describe columns for a table or view."""
    adapter = _get_adapter(connection_name)
    return adapter.describe_table(
        schema_name=schema_name,
        table_name=table_name,
        catalog_name=catalog_name,
    )


@mcp.tool()
def preview_sql(sql: str) -> dict[str, object]:
    """Validate a SQL statement against local read-only guardrails."""
    result = inspect_sql(sql)
    return {
        "is_safe": result.is_safe,
        "statement_type": result.statement_type,
        "normalized_sql": result.normalized_sql,
        "reasons": result.reasons,
    }


@mcp.tool()
def execute_readonly_sql(
    connection_name: str,
    sql: str,
    row_limit: int | None = None,
) -> dict[str, object]:
    """Execute a guarded read-only SQL statement."""
    config = _require_config()
    preview = inspect_sql(sql)
    if not preview.is_safe:
        return {
            "ok": False,
            "preview": {
                "is_safe": preview.is_safe,
                "statement_type": preview.statement_type,
                "normalized_sql": preview.normalized_sql,
                "reasons": preview.reasons,
            },
        }
    adapter = _get_adapter(connection_name)
    effective_limit = row_limit or config.default_row_limit
    result = adapter.execute_query(preview.normalized_sql, effective_limit)
    return {
        "ok": True,
        "preview": {
            "is_safe": preview.is_safe,
            "statement_type": preview.statement_type,
            "normalized_sql": preview.normalized_sql,
            "reasons": preview.reasons,
        },
        "result": result,
    }


@mcp.tool()
def explain_sql(
    connection_name: str,
    sql: str,
    row_limit: int | None = None,
) -> dict[str, object]:
    """Run EXPLAIN on a guarded read-only SQL statement."""
    config = _require_config()
    preview = inspect_sql(sql)
    if not preview.is_safe:
        return {
            "ok": False,
            "preview": {
                "is_safe": preview.is_safe,
                "statement_type": preview.statement_type,
                "normalized_sql": preview.normalized_sql,
                "reasons": preview.reasons,
            },
        }
    adapter = _get_adapter(connection_name)
    effective_limit = row_limit or config.default_row_limit
    result = adapter.explain_query(preview.normalized_sql, effective_limit)
    return {
        "ok": True,
        "preview": {
            "is_safe": preview.is_safe,
            "statement_type": preview.statement_type,
            "normalized_sql": preview.normalized_sql,
            "reasons": preview.reasons,
        },
        "result": result,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only database MCP server")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "config.json"),
        help="Path to the JSON config file.",
    )
    return parser


def main() -> None:
    global CONFIG
    parser = build_arg_parser()
    args = parser.parse_args()
    CONFIG = load_config(args.config)
    mcp.run()


if __name__ == "__main__":
    main()
