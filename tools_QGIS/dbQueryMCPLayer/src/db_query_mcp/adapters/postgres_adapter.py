from __future__ import annotations

import psycopg

from .base import BaseAdapter


class PostgresAdapter(BaseAdapter):
    def _connect(self):
        return psycopg.connect(
            host=str(self.options["host"]),
            port=int(self.options.get("port", 5432)),
            dbname=str(self.options["dbname"]),
            user=str(self.options["user"]),
            password=self.secret,
            sslmode=str(self.options.get("sslmode", "prefer")),
        )

    def _fetch(self, sql_text: str, row_limit: int) -> dict[str, object]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql_text)
                rows = cursor.fetchmany(row_limit)
                columns = [item.name for item in (cursor.description or [])]
        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows),
            "truncated": len(rows) == row_limit,
        }

    def list_catalogs(self) -> list[dict[str, object]]:
        return [{"catalog_name": str(self.options["dbname"])}]

    def list_schemas(self, catalog_name: str | None = None) -> list[dict[str, object]]:
        sql_text = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema')
        ORDER BY schema_name
        """
        if catalog_name and catalog_name != str(self.options["dbname"]):
            raise ValueError(
                f"catalog_name {catalog_name!r} does not match PostgreSQL database {self.options['dbname']!r}."
            )
        result = self._fetch(sql_text, 1000)
        return [{"schema_name": row[0]} for row in result["rows"]]

    def describe_table(
        self,
        schema_name: str,
        table_name: str,
        catalog_name: str | None = None,
    ) -> list[dict[str, object]]:
        sql_text = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            ordinal_position
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ordinal_position
        """
        if catalog_name:
            raise ValueError("catalog_name is not used for PostgreSQL connections.")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql_text, (schema_name, table_name))
                rows = cursor.fetchall()
        return [
            {
                "column_name": row[0],
                "data_type": row[1],
                "is_nullable": row[2],
                "ordinal_position": row[3],
            }
            for row in rows
        ]

    def execute_query(self, sql: str, row_limit: int) -> dict[str, object]:
        return self._fetch(sql, row_limit)

    def explain_query(self, sql: str, row_limit: int) -> dict[str, object]:
        return self._fetch(f"EXPLAIN {sql}", row_limit)
