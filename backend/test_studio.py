import os
import sys
import pathlib
import sqlite3
import subprocess
import json
import unittest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from database import init_db, get_connection, DB_PATH
from video_processor import get_video_metadata, compute_checksum, trim_video, render_duet

class DuetStudioTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = ROOT / "test_data"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        cls.vid1 = cls.test_dir / "test_vid1.mp4"
        cls.vid2 = cls.test_dir / "test_vid2.mp4"
        cls.vid_silent = cls.test_dir / "test_silent.mp4"
        cls.output_c = cls.test_dir / "test_duet_c.mp4"
        cls.output_d = cls.test_dir / "test_duet_d.mp4"

        # Generate synthetic video 1 with audio (3 seconds)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
            "-t", "3", "-c:v", "libx264", "-c:a", "aac", str(cls.vid1)
        ], check=True, capture_output=True)

        # Generate synthetic video 2 with audio (3 seconds)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=44100",
            "-t", "3", "-c:v", "libx264", "-c:a", "aac", str(cls.vid2)
        ], check=True, capture_output=True)

        # Generate synthetic video without audio (3 seconds)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:size=320x240:rate=30",
            "-t", "3", "-c:v", "libx264", str(cls.vid_silent)
        ], check=True, capture_output=True)

    def setUp(self):
        # Reset DB for tests
        if DB_PATH.exists():
            DB_PATH.unlink()
        init_db()

    def test_01_python_syntax_and_db(self):
        self.assertTrue(DB_PATH.exists())
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        self.assertIn("assets", tables)
        self.assertIn("generations", tables)
        self.assertIn("conversation_turns", tables)

    def test_02_metadata_extraction(self):
        meta = get_video_metadata(str(self.vid1))
        self.assertGreater(meta["duration"], 2.0)
        self.assertEqual(meta["width"], 320)
        self.assertEqual(meta["height"], 240)
        self.assertTrue(meta["has_audio"])

        meta_silent = get_video_metadata(str(self.vid_silent))
        self.assertFalse(meta_silent["has_audio"])

    def test_03_render_duet_with_audio(self):
        render_duet(str(self.vid1), str(self.vid2), str(self.output_c), layout="side-by-side")
        self.assertTrue(self.output_c.exists())
        meta = get_video_metadata(str(self.output_c))
        self.assertGreater(meta["duration"], 2.0)
        self.assertTrue(meta["has_audio"])

    def test_04_render_duet_mixed_audio(self):
        # One with audio, one silent
        output_mixed = self.test_dir / "test_mixed.mp4"
        render_duet(str(self.vid1), str(self.vid_silent), str(output_mixed), layout="stacked")
        self.assertTrue(output_mixed.exists())
        meta = get_video_metadata(str(output_mixed))
        self.assertTrue(meta["has_audio"])

    def test_05_failed_render_does_not_record_generation(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM generations")
        count_before = cursor.fetchone()[0]
        conn.close()

        with self.assertRaises(Exception):
            render_duet("nonexistent_video.mp4", str(self.vid2), str(self.output_d))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM generations")
        count_after = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count_before, count_after)

    def test_06_recursive_workflow(self):
        # Step 1: Render A + B -> C
        render_duet(str(self.vid1), str(self.vid2), str(self.output_c), layout="side-by-side")
        
        # Register C as asset in DB
        meta_c = get_video_metadata(str(self.output_c))
        checksum_c = compute_checksum(str(self.output_c))
        asset_c_id = "asset_c_synthetic"
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO assets (asset_id, file_path, duration, width, height, checksum) VALUES (?, ?, ?, ?, ?, ?)",
            (asset_c_id, str(self.output_c), meta_c["duration"], meta_c["width"], meta_c["height"], checksum_c)
        )
        conn.commit()
        conn.close()

        # Step 2: Render C + vid_silent -> D (Recursive workflow)
        render_duet(str(self.output_c), str(self.vid_silent), str(self.output_d), layout="stacked")
        self.assertTrue(self.output_d.exists())
        meta_d = get_video_metadata(str(self.output_d))
        self.assertGreater(meta_d["duration"], 2.0)

    @classmethod
    def tearDownClass(cls):
        # Clean up test dir
        import shutil
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

if __name__ == "__main__":
    unittest.main()
