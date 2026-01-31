#!/usr/bin/env python3
"""CLI client for CoRunner (talks to the local HTTP runner)."""

import os
import sys
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("CO_RUNNER_API_TOKEN", "changeme")
BASE_URL = os.getenv("CO_RUNNER_URL", "http://127.0.0.1:8000")

HEADERS = {"x-api-key": API_TOKEN}


def list_tasks():
    r = requests.get(f"{BASE_URL}/tasks", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    for tid, v in data.items():
        print(tid)
        print("  description:", v.get("description"))
        print("  phrases:", ", ".join(v.get("phrases", [])))
        print()


def run_by_id(task_id: str):
    r = requests.post(f"{BASE_URL}/run", json={"task_id": task_id}, headers=HEADERS)
    r.raise_for_status()
    print_output(r.json())


def run_by_phrase(phrase: str):
    r = requests.post(f"{BASE_URL}/run", json={"phrase": phrase}, headers=HEADERS)
    r.raise_for_status()
    print_output(r.json())


def print_output(o):
    print("task_id:", o.get("task_id"))
    print("returncode:", o.get("returncode"))
    print("stdout:")
    print(o.get("stdout") or "")
    print("stderr:")
    print(o.get("stderr") or "")


def main(argv=None):
    p = argparse.ArgumentParser(description="CoRunner CLI")
    sub = p.add_subparsers(dest="cmd")

    sub_list = sub.add_parser("list")

    sub_run = sub.add_parser("run")
    sub_run.add_argument("task_id", help="task_id from tasks.yml")

    sub_phrase = sub.add_parser("phrase")
    sub_phrase.add_argument("phrase", help="Exact phrase mapped in tasks.yml (quoted)")

    args = p.parse_args(argv)
    if args.cmd == "list":
        list_tasks()
    elif args.cmd == "run":
        run_by_id(args.task_id)
    elif args.cmd == "phrase":
        run_by_phrase(args.phrase)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
