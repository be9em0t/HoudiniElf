from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class KeychainRef:
    service: str
    account: str


@dataclass(frozen=True)
class ConnectionConfig:
    name: str
    kind: str
    description: str
    keychain: KeychainRef
    options: dict[str, object]


@dataclass(frozen=True)
class AppConfig:
    default_row_limit: int
    connections: list[ConnectionConfig]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    data = json.loads(config_path.read_text())

    connections = [
        ConnectionConfig(
            name=item["name"],
            kind=item["kind"],
            description=item.get("description", ""),
            keychain=KeychainRef(
                service=item["keychain"]["service"],
                account=item["keychain"]["account"],
            ),
            options=item["options"],
        )
        for item in data["connections"]
    ]

    return AppConfig(
        default_row_limit=int(data.get("default_row_limit", 200)),
        connections=connections,
    )
