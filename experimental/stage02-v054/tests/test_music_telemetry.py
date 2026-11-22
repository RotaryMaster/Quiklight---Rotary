"""Stage02 audio-telemetry regression tests: no Qt/hardware required."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from music_telemetry import (CHANNELS, COLORS, LABELS_PT, MIN_MAX_FIELDS,
                             ON_FIELDS, clamp_range, normalize,
                             read_audio, request_audio)


class MusicTelemetryTest(unittest.TestCase):
    def test_five_distinct_channels_and_colors(self):
        self.assertEqual(len(CHANNELS), 5)
        self.assertEqual(len(set(CHANNELS)), 5)
        self.assertEqual(len(set(COLORS)), 5)
        self.assertEqual(len(LABELS_PT), 5)
        self.assertEqual(len(MIN_MAX_FIELDS), 4)
        self.assertEqual(len(ON_FIELDS), 4)

    def test_normalize(self):
        self.assertEqual(normalize("0.1 0.2 0.3 0.4 0.5"),
                         (0.1,0.2,0.3,0.4,0.5))
        self.assertEqual(normalize("-0.5 2 0.3 0.4 1.2"),
                         (0.0,1.0,0.3,0.4,1.0))
        self.assertIsNone(normalize("0.2 0.3 0.4"))
        self.assertIsNone(normalize("0.2 bad 0.3 0.4 0.5"))
        self.assertIsNone(normalize("NaN 0 0 0 0"))
        self.assertIsNone(normalize("0 inf 0 0 0"))
        self.assertIsNone(normalize("0 0 -inf 0 0"))
        self.assertEqual(normalize("0 0 0 0 0 extra"), (0.0,)*5)

    def test_audio_file_fresh_and_stale(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            file=root/"quiklight-audio.txt"
            file.write_text("0.12 0.34 0.56 0.78 0.91")
            mtime=file.stat().st_mtime
            current=read_audio(root,now=mtime+0.5)
            self.assertIsNotNone(current)
            self.assertEqual(current.levels,(0.12,0.34,0.56,0.78,0.91))
            self.assertIsNone(read_audio(root,now=mtime+3))
            self.assertIsNone(read_audio(root,now=mtime-2))
            self.assertFalse((root/"quiklight-audio.want").exists())

    def test_no_data_for_invalid_or_huge_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            file=root/"quiklight-audio.txt"
            self.assertIsNone(read_audio(root))
            file.write_text("garbage",encoding="utf8")
            self.assertIsNone(read_audio(root))
            file.write_text("0 " * 600)
            self.assertIsNone(read_audio(root))

    def test_want_throttled_and_no_directory_creation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            nonexistent=root/"missing"
            success,last=request_audio(nonexistent,now=5.0)
            self.assertFalse(success)
            self.assertFalse(nonexistent.exists())
            success,last=request_audio(root,now=5.0)
            self.assertTrue(success)
            self.assertTrue((root/"quiklight-audio.want").exists())
            success,next_request=request_audio(root,now=5.9,last_request=last)
            self.assertFalse(success)
            self.assertEqual(last,next_request)
            success,next_request=request_audio(root,now=6.5,last_request=last)
            self.assertTrue(success)

    def test_threshold_guard(self):
        self.assertEqual(clamp_range(0.2,0.8),(0.2,0.8))
        self.assertEqual(clamp_range(-1,3),(0.0,1.0))
        a,b=clamp_range(0.99,0.1)
        self.assertGreaterEqual(b-a,0.05-1e-8)
        with self.assertRaises(ValueError):
            clamp_range(float("nan"),0.8)
        with self.assertRaises(ValueError):
            clamp_range(0.2,float("inf"))

if __name__ == "__main__":
    unittest.main()
