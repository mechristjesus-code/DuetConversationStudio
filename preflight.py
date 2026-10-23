#!/usr/bin/env python3
"""Read-only environment audit for Duet Conversation Studio.

This script does not create, delete, or modify project files. It prints JSON by
 default and exits 0 only when required tools are present and port 8765 is free
(or an existing local health endpoint answers).
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = Path.home() / "DuetConversationStudio"
HOST = "127.0.0.1"
PORT = 8765


def command_info(name: str) -> dict:
    path = shutil.which(name)
    result = {"present": bool(path), "path": path, "version": None}
    if path:
        try:
            proc = subprocess.run(
                [name, "--version"], capture_output=True, text=True,
                timeout=3, check=False
            )
            text = (proc.stdout or proc.stderr).splitlines()
            result["version"] = text[0] if text else None
        except (OSError, subprocess.SubprocessError) as exc:
            result["error"] = str(exc)
    return result


def port_info() -> dict:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        rc = sock.connect_ex((HOST, PORT))
        if rc != 0:
            return {"available": True, "server_responding": False}
        try:
            with urllib.request.urlopen(
                f"http://{HOST}:{PORT}/api/status", timeout=1
            ) as response:
                return {
                    "available": False,
                    "server_responding": True,
                    "http_status": response.status,
                }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {
                "available": False,
                "server_responding": False,
                "occupied_by_unknown_service": True,
                "error": str(exc),
            }
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    tools = {name: command_info(name) for name in
             ("python3", "ffmpeg", "ffprobe", "git", "sqlite3")}
    project_exists = PROJECT.exists()
    port = port_info()
    required_ok = all(item["present"] for item in tools.values())
    port_ok = port["available"] or port["server_responding"]
    report = {
        "project": str(PROJECT),
        "tools": tools,
        "project_exists": project_exists,
        "port_8765": port,
        "writes_performed": False,
        "pass": required_ok and port_ok,
    }
    print(json.dumps(report, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
