from __future__ import annotations

from databricks import sql as databricks_sql

from .base import BaseAdapter


class DatabricksAdapter(BaseAdapter):
    def _connect(self):
        return databricks_sql.connect(
            server_hostname=str(self.options["server_hostname"]),
            http_path=str(self.options["http_path"]),
            access_token=self.secret,
        )

    def _fetch(self, sql_text: str, row_limit: int) -> dict[str, object]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql_text)
                rows = cursor.fetchmany(row_limit)
                columns = [item[0] for item in (cursor.description or [])]
        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows),
            "truncated": len(rows) == row_limit,
        }

    def list_catalogs(self) -> list[dict[str, object]]:
        result = self._fetch("SHOW CATALOGS", 1000)
        rows = result["rows"]
        return [{"catalog_name": row[0]} for row in rows]

    def list_schemas(self, catalog_name: str | None = None) -> list[dict[str, object]]:
        if catalog_name:
            sql_text = f"SHOW SCHEMAS IN `{catalog_name}`"
        else:
            sql_text = "SHOW SCHEMAS"
        result = self._fetch(sql_text, 1000)
        rows = result["rows"]
        return [{"schema_name": row[0]} for row in rows]

    def describe_table(
        self,
        schema_name: str,
        table_name: str,
        catalog_name: str | None = None,
    ) -> list[dict[str, object]]:
        if catalog_name:
            relation = f"`{catalog_name}`.`{schema_name}`.`{table_name}`"
        else:
            relation = f"`{schema_name}`.`{table_name}`"
        result = self._fetch(f"DESCRIBE {relation}", 1000)
        rows = []
        for row in result["rows"]:
            if not row or row[0] in ("", "# Partition Information", "# Detailed Table Information"):
                continue
            rows.append(
                {
                    "column_name": row[0],
                    "data_type": row[1] if len(row) > 1 else None,
                    "comment": row[2] if len(row) > 2 else None,
                }
            )
        return rows

    def execute_query(self, sql: str, row_limit: int) -> dict[str, object]:
        return self._fetch(sql, row_limit)

    def explain_query(self, sql: str, row_limit: int) -> dict[str, object]:
        return self._fetch(f"EXPLAIN {sql}", row_limit)
