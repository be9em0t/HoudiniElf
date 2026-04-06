from __future__ import annotations

import subprocess


class KeychainError(RuntimeError):
    """Raised when a secret cannot be retrieved from the macOS Keychain."""


def read_generic_password(service: str, account: str) -> str:
    command = [
        "security",
        "find-generic-password",
        "-s",
        service,
        "-a",
        account,
        "-w",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown keychain error"
        raise KeychainError(
            f"Unable to read keychain item service={service!r} account={account!r}: {stderr}"
        )
    return result.stdout.strip()
