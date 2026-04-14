"""
tests/test_recognition.py
Unit tests for models/face_model.py and core/train.py logic.
Tests that don't require a physical camera or GPU.
"""

import os
import sys
import shutil
import tempfile
import unittest
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TMP_DIR = tempfile.mkdtemp()

import config.settings as S
S.ENCODINGS_DIR = TMP_DIR
S.ENCODINGS_PKL = os.path.join(TMP_DIR, "face_encodings.pkl")
S.DATASET_DIR   = os.path.join(TMP_DIR, "dataset")
os.makedirs(S.DATASET_DIR, exist_ok=True)

from models.face_model import (
    load_encodings, save_encodings, encodings_exist,
    identify_faces_in_frame, remove_user_encodings,
)
from utils.face_utils import (
    bgr_to_rgb, scale_frame, scale_face_locations,
    is_blurry, is_too_dark, frame_to_jpeg_bytes,
)
from utils.time_utils import (
    current_timestamp, current_date, seconds_since, friendly_time
)
from utils.id_generator import generate_user_id, format_id
from utils.helpers import sanitize_name, is_valid_name, percentage


class TestEncodingPersistence(unittest.TestCase):

    def setUp(self):
        if os.path.exists(S.ENCODINGS_PKL):
            os.remove(S.ENCODINGS_PKL)

    def test_load_empty(self):
        data = load_encodings()
        self.assertEqual(data["encodings"], [])
        self.assertEqual(data["user_ids"], [])
        self.assertEqual(data["names"], [])

    def test_save_and_load(self):
        enc = np.random.rand(128).astype(np.float64)
        data = {"encodings": [enc], "user_ids": [101], "names": ["Test User"]}
        ok = save_encodings(data)
        self.assertTrue(ok)

        loaded = load_encodings()
        self.assertEqual(len(loaded["encodings"]), 1)
        self.assertEqual(loaded["user_ids"][0], 101)
        self.assertEqual(loaded["names"][0], "Test User")
        np.testing.assert_array_almost_equal(loaded["encodings"][0], enc)

    def test_encodings_exist(self):
        self.assertFalse(encodings_exist())
        save_encodings({"encodings": [np.zeros(128)], "user_ids": [1], "names": ["X"]})
        self.assertTrue(encodings_exist())

    def test_remove_user_encodings(self):
        enc_a = np.random.rand(128)
        enc_b = np.random.rand(128)
        data = {
            "encodings": [enc_a, enc_b],
            "user_ids":  [101, 102],
            "names":     ["Alice", "Bob"],
        }
        save_encodings(data)
        remove_user_encodings(101)
        loaded = load_encodings()
        self.assertEqual(len(loaded["encodings"]), 1)
        self.assertEqual(loaded["user_ids"][0], 102)


class TestFaceUtils(unittest.TestCase):

    def _blank_frame(self, h=480, w=640):
        return np.zeros((h, w, 3), dtype=np.uint8)

    def _bright_frame(self, h=480, w=640):
        return np.full((h, w, 3), 200, dtype=np.uint8)

    def test_bgr_to_rgb(self):
        frame = self._blank_frame()
        frame[:, :, 0] = 255   # Blue channel in BGR
        rgb = bgr_to_rgb(frame)
        self.assertEqual(rgb[:, :, 2].max(), 255)   # Blue → channel 2 in RGB

    def test_scale_frame(self):
        frame = self._blank_frame(480, 640)
        scaled = scale_frame(frame, 0.5)
        self.assertEqual(scaled.shape, (240, 320, 3))

    def test_scale_face_locations(self):
        locs = [(100, 200, 150, 50)]
        scaled = scale_face_locations(locs, scale=0.5)
        self.assertEqual(scaled[0], (200, 400, 300, 100))

    def test_is_blurry_dark_frame(self):
        dark = self._blank_frame()
        # A completely black frame has zero Laplacian variance → very blurry
        self.assertTrue(is_blurry(dark, threshold=1.0))

    def test_is_too_dark(self):
        dark = self._blank_frame()
        self.assertTrue(is_too_dark(dark, threshold=10.0))
        bright = self._bright_frame()
        self.assertFalse(is_too_dark(bright, threshold=10.0))

    def test_frame_to_jpeg_bytes(self):
        frame = self._bright_frame()
        bts = frame_to_jpeg_bytes(frame)
        self.assertIsInstance(bts, bytes)
        self.assertGreater(len(bts), 0)


class TestTimeUtils(unittest.TestCase):

    def test_current_timestamp_format(self):
        ts = current_timestamp()
        from datetime import datetime
        from config.settings import LOG_DATETIME_FORMAT
        dt = datetime.strptime(ts, LOG_DATETIME_FORMAT)
        self.assertIsNotNone(dt)

    def test_seconds_since_recent(self):
        ts = current_timestamp()
        elapsed = seconds_since(ts)
        self.assertLess(elapsed, 2.0)

    def test_seconds_since_old(self):
        old = "2000-01-01 00:00:00"
        elapsed = seconds_since(old)
        self.assertGreater(elapsed, 1_000_000)

    def test_seconds_since_invalid(self):
        result = seconds_since("not-a-date")
        self.assertEqual(result, float("inf"))

    def test_friendly_time_recent(self):
        ts = current_timestamp()
        label = friendly_time(ts)
        self.assertEqual(label, "Just now")


class TestIdGenerator(unittest.TestCase):

    def test_format_id(self):
        self.assertEqual(format_id(101), "0101")
        self.assertEqual(format_id(1),   "0001")
        self.assertEqual(format_id(9999), "9999")


class TestHelpers(unittest.TestCase):

    def test_sanitize_name(self):
        self.assertEqual(sanitize_name("  john doe  "), "John Doe")
        self.assertEqual(sanitize_name("PRIYA   IYER"), "Priya Iyer")
        self.assertEqual(sanitize_name("a-b-c 123"), "A B C")

    def test_is_valid_name(self):
        self.assertTrue(is_valid_name("Aarav"))
        self.assertFalse(is_valid_name("A"))
        self.assertFalse(is_valid_name(""))
        self.assertFalse(is_valid_name("  "))

    def test_percentage(self):
        self.assertEqual(percentage(1, 4), 25.0)
        self.assertEqual(percentage(0, 0), 0.0)
        self.assertEqual(percentage(3, 3), 100.0)


def tearDownModule():
    shutil.rmtree(TMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
