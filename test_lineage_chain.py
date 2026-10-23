#!/usr/bin/env python3
"""End-to-end validation for recursive Termux lineage chains.

The test copies the project into a temporary directory, creates temporary media,
starts an isolated server, verifies A+B->C and A+C->D, restarts the server,
and validates lineage restore plus the manual-review TikTok packet.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def request_json(url: str, *, method: str = "GET", payload: object | None = None, headers: dict[str, str] | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def multipart_upload(url: str, file_path: Path) -> dict:
    boundary = f"----DuetTest{uuid.uuid4().hex}"
    data = file_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="video"; filename="{file_path.name}"\r\n'
        "Content-Type: video/mp4\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class LineageChainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="duet-lineage-test-"))
        self.project = self.temp / "DuetConversationStudio"
        shutil.copytree(ROOT, self.project, ignore=shutil.ignore_patterns("__pycache__", "*.sqlite3", "audit.log"))
        self.media = self.temp / "media"
        self.media.mkdir()
        self.port = 18000 + (os.getpid() % 1000)
        self.base = f"http://127.0.0.1:{self.port}"
        self.server: subprocess.Popen[str] | None = None
        self._create_media()
        self._start_server()

    def tearDown(self) -> None:
        self._stop_server()
        shutil.rmtree(self.temp, ignore_errors=True)

    def _create_media(self) -> None:
        commands = [
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", """color=c=blue:s=320x240:d=1.2""", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.2", "-shortest", "-c:v", "libx264", "-c:a", "aac", str(self.media / "a.mp4")],
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1.0", "-c:v", "libx264", "-an", str(self.media / "b-silent.mp4")],
        ]
        for command in commands:
            subprocess.run(command, check=True, capture_output=True)
        self.original_hashes = {path.name: sha256(path) for path in self.media.glob("*.mp4")}

    def _start_server(self) -> None:
        self.server = subprocess.Popen(
            [sys.executable, "server.py", "--port", str(self.port)],
            cwd=self.project,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for _ in range(80):
            try:
                if request_json(f"{self.base}/api/status").get("ok"):
                    return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        output = self.server.stdout.read() if self.server.stdout else ""
        self.fail(f"Termux server did not start: {output}")

    def _stop_server(self) -> None:
        if not self.server:
            return
        self.server.send_signal(signal.SIGTERM)
        try:
            self.server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.server.kill()
            self.server.wait(timeout=5)
        if self.server.stdout:
            self.server.stdout.close()
        self.server = None

    def _wait_for_render(self, generation_id: int) -> dict:
        for _ in range(120):
            status = request_json(f"{self.base}/api/generations/{generation_id}/render/status")
            if status["render_status"] == "ok":
                return status
            if status["render_status"] == "failed":
                self.fail(status.get("error") or "render failed")
            time.sleep(0.25)
        self.fail("render timed out")
        return {}

    def _create_generation(self, inputs: list[dict]) -> dict:
        return request_json(f"{self.base}/api/generations", method="POST", payload={"inputs": inputs, "recipe": {"schema_version": 1, "layout": {"type": "split_screen"}}})

    def test_recursive_chain_restart_restore_and_tiktok_packet(self) -> None:
        source_a = multipart_upload(f"{self.base}/api/sources", self.media / "a.mp4")
        source_b = multipart_upload(f"{self.base}/api/sources", self.media / "b-silent.mp4")
        self.assertEqual(source_a["status"], "ok")
        self.assertEqual(source_b["status"], "ok")

        generation_c = self._create_generation([
            {"source_id": source_a["id"], "trim_start_ms": 0, "trim_end_ms": 1000, "gain": 1.0},
            {"source_id": source_b["id"], "trim_start_ms": 0, "trim_end_ms": 1000, "gain": 0.75},
        ])
        request_json(f"{self.base}/api/generations/{generation_c['id']}/render", method="POST")
        self._wait_for_render(generation_c["id"])

        generation_d = self._create_generation([
            {"source_id": source_a["id"], "trim_start_ms": 0, "trim_end_ms": 1000, "gain": 1.0},
            {"generation_id": generation_c["id"], "trim_start_ms": 0, "trim_end_ms": 1000, "gain": 0.5},
        ])
        request_json(f"{self.base}/api/generations/{generation_d['id']}/render", method="POST")
        render_d = self._wait_for_render(generation_d["id"])
        self.assertTrue(Path(render_d["render_path"]).is_file())

        lineage = request_json(f"{self.base}/api/generations/{generation_d['id']}/lineage")
        parent_refs = [ref for ref in lineage["inputs"] if ref["ref_kind"] == "generation"]
        self.assertEqual(len(parent_refs), 1)
        self.assertEqual(parent_refs[0]["parent_generation_id"], generation_c["id"])
        self.assertEqual(len({source_a["sha256"], source_b["sha256"]}), 2)

        tiktok = request_json(
            f"{self.base}/api/generations/{generation_d['id']}/export/tiktok",
            method="POST",
            payload={"rights_confirmed": True, "caption": "Recursive response", "credits": [{"creator_username": "creator", "video_url": "https://www.tiktok.com/@creator/video/example"}]},
        )
        packet = json.loads(Path(tiktok["credit_packet_path"]).read_text())
        self.assertEqual(packet["format"]["width"], 1080)
        self.assertEqual(packet["format"]["height"], 1920)
        self.assertFalse(packet["direct_posting_enabled"])
        self.assertIn("@creator", packet["caption"])

        self._stop_server()
        self._start_server()
        generations = request_json(f"{self.base}/api/generations")["generations"]
        self.assertGreaterEqual(len(generations), 2)
        restored = request_json(f"{self.base}/api/restore/lineage", method="POST", payload=lineage)
        self.assertTrue(restored["duplicate"])
        self.assertFalse(restored["restored"])
        self.assertEqual(sha256(self.media / "a.mp4"), self.original_hashes["a.mp4"])
        self.assertEqual(sha256(self.media / "b-silent.mp4"), self.original_hashes["b-silent.mp4"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
