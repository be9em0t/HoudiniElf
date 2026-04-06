from __future__ import annotations

from dataclasses import dataclass
import re


FORBIDDEN_KEYWORDS = {
    "alter",
    "analyze",
    "attach",
    "call",
    "comment",
    "commit",
    "copy",
    "create",
    "delete",
    "detach",
    "drop",
    "grant",
    "insert",
    "merge",
    "refresh",
    "replace",
    "revoke",
    "set",
    "truncate",
    "update",
    "upsert",
    "use",
    "vacuum",
}

ALLOWED_START_KEYWORDS = {
    "describe",
    "explain",
    "select",
    "show",
    "values",
    "with",
}


@dataclass(frozen=True)
class PreviewResult:
    is_safe: bool
    statement_type: str
    normalized_sql: str
    reasons: list[str]


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
    return sql


def normalize_sql(sql: str) -> str:
    return " ".join(_strip_sql_comments(sql).strip().split())


def preview_sql(sql: str) -> PreviewResult:
    normalized = normalize_sql(sql)
    reasons: list[str] = []

    if not normalized:
        reasons.append("SQL is empty after removing comments.")
        return PreviewResult(False, "unknown", normalized, reasons)

    if normalized.count(";") > 1 or (
        normalized.endswith(";") and normalized[:-1].count(";") > 0
    ):
        reasons.append("Only a single SQL statement is allowed.")

    cleaned = normalized[:-1].strip() if normalized.endswith(";") else normalized
    first_word = cleaned.split(" ", 1)[0].lower()

    if first_word not in ALLOWED_START_KEYWORDS:
        reasons.append(
            "SQL must begin with one of: SELECT, WITH, SHOW, DESCRIBE, EXPLAIN, VALUES."
        )

    tokens = set(re.findall(r"\b[a-z_]+\b", cleaned.lower()))
    forbidden = sorted(tokens.intersection(FORBIDDEN_KEYWORDS))
    if forbidden:
        reasons.append(f"Forbidden keyword(s) detected: {', '.join(forbidden)}.")

    return PreviewResult(
        is_safe=not reasons,
        statement_type=first_word,
        normalized_sql=cleaned,
        reasons=reasons,
    )
