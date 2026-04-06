from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    def __init__(self, options: dict[str, object], secret: str) -> None:
        self.options = options
        self.secret = secret

    @abstractmethod
    def list_schemas(self, catalog_name: str | None = None) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def list_catalogs(self) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def describe_table(
        self,
        schema_name: str,
        table_name: str,
        catalog_name: str | None = None,
    ) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def execute_query(
        self,
        sql: str,
        row_limit: int,
    ) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def explain_query(self, sql: str, row_limit: int) -> dict[str, object]:
        raise NotImplementedError
