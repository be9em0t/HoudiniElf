import subprocess


KEYCHAIN_SENTINEL = "__KEYCHAIN__"


def _read_keychain_password(service, account):
	result = subprocess.run(
		[
			"security",
			"find-generic-password",
			"-s",
			service,
			"-a",
			account,
			"-w",
		],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		stderr = result.stderr.strip() or "Unknown keychain error"
		raise RuntimeError(
			f"Could not read macOS Keychain item service={service!r} account={account!r}: {stderr}"
		)
	return result.stdout.strip()


def get_ini_secret(config, section, value_key, service_key=None, account_key=None):
	"""Resolve a possibly-keychain-backed secret from an INI section.

	If the INI value is a normal string, return it unchanged.
	If it is set to "__KEYCHAIN__", look up the password using the paired
	service/account keys from the same section.
	"""
	value = config[section][value_key]
	if value != KEYCHAIN_SENTINEL:
		return value

	service_name = service_key or f"{value_key}_service"
	account_name = account_key or f"{value_key}_account"
	service = config[section].get(service_name, "").strip()
	account = config[section].get(account_name, "").strip()
	if not service or not account:
		raise RuntimeError(
			f"{section}.{value_key} is set to {KEYCHAIN_SENTINEL} but {service_name} / {account_name} is missing."
		)
	return _read_keychain_password(service, account)
