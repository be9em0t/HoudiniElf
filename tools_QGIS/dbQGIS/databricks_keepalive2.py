"""
databricks_keepalive2.py — keep Databricks SQL warehouse awake

Purpose:
  Periodically issues a lightweight SQL query (SELECT 1) to keep a Databricks SQL warehouse/cluster warm so it doesn't need a long cold-start.

Quick setup:
  1. (recommended) Create & activate a virtual environment:
       source .venv/bin/activate
	   e.g. source /Users/dunevv/WorkLocal/_AI_/HoudiniElf/.venv/bin/activate
  2. Install required packages:
       pip install -r requirements.txt
     or explicitly:
       pip install python-dotenv databricks-sql-connector

Running (examples):
  - Using python-dotenv CLI (preferred):
      # From repo root (dotenv will pick up .env next to the script)
	  dotenv run -- python databricks_keepalive2.py -c /dev/null -i 500

      # Or run inside the dbQGIS folder where the script and .env live
      cd dbQGIS && dotenv run -- python databricks_keepalive2.py -c /dev/null -i 240

  - Load `.env` in a subshell for a single run (no long-lived env changes):
      # if already in dbQGIS:
      ( set -o allexport; source .env; set +o allexport; python databricks_keepalive2.py -c /dev/null -i 240 )

  - Direct run (script auto-loads `.env` from the script directory or parent dirs if present):
      # Run from dbQGIS so the script finds .env automatically
      cd dbQGIS && python databricks_keepalive2.py -c /dev/null -i 240

Stopping:
  - Press Ctrl+C to stop gracefully.

Notes:
  - Keep tokens secret; prefer using environment variables or a secrets manager where possible.
  - The script will prefer environment variables (or a .env file) over values found in the INI.
"""

import time
import argparse
import logging
import os
from pathlib import Path
from datetime import timedelta
import configparser
from databricks import sql


def read_config(ini_file):
	config = configparser.ConfigParser()
	# config.read returns list of files read; if empty file may not exist — that's OK: we'll fall back to env vars
	config.read(ini_file)
	return config


def load_dotenv_if_present():
	"""Attempt to load a .env file if available. Tries python-dotenv first, then falls back to a simple parser."""
	loaded = False
	# Try python-dotenv if installed
	try:
		from dotenv import load_dotenv, find_dotenv
		dotenv_path = find_dotenv(usecwd=True)
		if dotenv_path:
			load_dotenv(dotenv_path, override=False)
			logging.info(f"Loaded .env from {dotenv_path}")
			return True
	except Exception:
		pass

	# Fall back to searching for a .env file upwards from cwd
	p = Path.cwd()
	for d in [p] + list(p.parents):
		candidate = d / '.env'
		if candidate.is_file():
			try:
				with candidate.open() as fh:
					for line in fh:
						line = line.strip()
						if not line or line.startswith('#'):
							continue
						if '=' in line:
							k, v = line.split('=', 1)
							os.environ.setdefault(k.strip(), v.strip())
				logging.info(f"Loaded .env from {candidate}")
				return True
			except Exception:
				logging.debug(f"Failed to read {candidate}")
	return False


def get_config_values(config):
	"""Gather configuration from environment variables (preferred) or fall back to the INI file.

	Returns a dict with keys: server_hostname, http_path, access_token, dirCommonGeopack
	"""
	vals = {}
	vals['server_hostname'] = os.getenv('DATABRICKS_SERVER_HOSTNAME') or os.getenv('DATABRICKS_HOSTNAME') or config.get('mcr', 'server_hostname', fallback=None)
	vals['http_path'] = os.getenv('DATABRICKS_HTTP_PATH') or config.get('mcr', 'http_path', fallback=None)
	vals['access_token'] = os.getenv('DATABRICKS_TOKEN') or os.getenv('DATABRICKS_ACCESS_TOKEN') or config.get('mcr', 'access_token', fallback=None)
	vals['dirCommonGeopack'] = os.getenv('DIR_COMMON_GEOPACK') or config.get('directories', 'dirCommonGeopack', fallback=None)
	# Validate required fields
	missing = [k for k in ('server_hostname', 'http_path', 'access_token') if not vals[k]]
	if missing:
		raise RuntimeError(f"Missing required Databricks config: {', '.join(missing)}. Set them either as environment variables (DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN) or in the INI under [mcr].")
	return vals


def connect_to_databricks(server_hostname, http_path, access_token):
	logging.info("Attempting connection to Databricks SQL endpoint")
	return sql.connect(server_hostname=server_hostname, http_path=http_path, access_token=access_token)


def keep_alive(server_hostname, http_path, access_token, interval_seconds=240):
	"""Keep a Databricks SQL connection alive by periodically issuing a lightweight query.

	Parameters:
	- server_hostname, http_path, access_token: connection params
	- interval_seconds: how long to sleep between pings (default 240s)
	"""
	ping_count = 0
	start_time = time.time()
	backoff = 5  # seconds, for reconnect attempts
	connection = None
	cursor = None

	try:
		while True:
			try:
				if connection is None:
					connection = connect_to_databricks(server_hostname, http_path, access_token)
					cursor = connection.cursor()
					logging.info("Connected to Databricks SQL endpoint")

				# Perform a lightweight query
				cursor.execute("SELECT 1 AS test_column;")
				result = cursor.fetchall()
				ping_count += 1
				elapsed_time = timedelta(seconds=int(time.time() - start_time))
				for row in result:
					logging.info(f"Ping #{ping_count}, Elapsed: {elapsed_time}, Result: {row}")

				# Sleep for the configured interval
				time.sleep(interval_seconds)

			except KeyboardInterrupt:
				logging.info("Keepalive script terminated by user via keyboard interrupt")
				break
			except Exception as e:
				logging.warning(f"Error during keepalive loop: {e}. Will attempt reconnect in {backoff}s.")
				# Close and reset to trigger reconnect
				try:
					if cursor:
						cursor.close()
				except Exception:
					pass
				try:
					if connection:
						connection.close()
				except Exception:
					pass
				cursor = None
				connection = None
				time.sleep(backoff)
				# Exponential backoff up to a cap
				backoff = min(backoff * 2, 300)

	finally:
		# Ensure resources closed
		if cursor:
			try:
				cursor.close()
			except Exception:
				pass
		if connection:
			try:
				connection.close()
			except Exception:
				pass
		logging.info("Connection closed and resources cleaned up")


def main():
	parser = argparse.ArgumentParser(description="Databricks keepalive script")
	parser.add_argument("--config", "-c", default="b9QGISdata.ini", help="Path to INI config file")
	parser.add_argument("--interval", "-i", type=int, default=None, help="Ping interval in seconds (overrides config)")
	args = parser.parse_args()

	logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

	config = read_config(args.config)
	# Load variables from .env (if present) and prefer environment variables over INI values
	load_dotenv_if_present()
	vals = get_config_values(config)
	server_hostname = vals['server_hostname']
	http_path = vals['http_path']
	access_token = vals['access_token']
	dirCommonGeopack = vals.get('dirCommonGeopack')
	if dirCommonGeopack:
		logging.info(f"dirCommonGeopack: {dirCommonGeopack}")

	# Interval: CLI > config > default
	if args.interval is not None:
		interval = args.interval
	else:
		interval = int(config['keepalive'].get('interval_seconds', 240))

	logging.info(f"Starting keepalive with interval {interval}s")	
	keep_alive(server_hostname, http_path, access_token, interval_seconds=interval)


if __name__ == "__main__":
	main()
