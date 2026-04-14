"""
tests/test_database.py
Unit tests for core/database.py — uses a temporary CSV file so the real
data/users.csv and data/attendance.csv are never touched.
"""

import os
import sys
import shutil
import tempfile
import unittest

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Redirect CSV paths to a temp directory before importing anything
TMP_DIR = tempfile.mkdtemp()

import config.settings as S
S.DATA_DIR        = TMP_DIR
S.USERS_CSV       = os.path.join(TMP_DIR, "users.csv")
S.ATTENDANCE_CSV  = os.path.join(TMP_DIR, "attendance.csv")
S.LOGS_TXT        = os.path.join(TMP_DIR, "logs.txt")

from core.database import (
    initialise_db, add_user, get_user, get_all_users,
    delete_user, user_exists, get_user_count,
    log_attendance, get_last_log, get_attendance_today,
)
from config.settings import ATTENDANCE_ENTRY, ATTENDANCE_EXIT


class TestUserOperations(unittest.TestCase):

    def setUp(self):
        # Fresh CSVs for every test
        for f in (S.USERS_CSV, S.ATTENDANCE_CSV):
            if os.path.exists(f):
                os.remove(f)
        initialise_db()

    # ── add_user ───────────────────────────────────────────────────────────────

    def test_add_user_success(self):
        ok = add_user(101, "Aarav Sharma", "/dataset/101")
        self.assertTrue(ok)

    def test_add_user_duplicate_fails(self):
        add_user(101, "Aarav Sharma", "/dataset/101")
        ok = add_user(101, "Another Name", "/dataset/101")
        self.assertFalse(ok)

    def test_get_user_found(self):
        add_user(202, "Priya Iyer", "/dataset/202")
        user = get_user(202)
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Priya Iyer")

    def test_get_user_not_found(self):
        user = get_user(9999)
        self.assertIsNone(user)

    def test_get_all_users(self):
        add_user(101, "User A", "/a")
        add_user(102, "User B", "/b")
        users = get_all_users()
        self.assertEqual(len(users), 2)

    def test_delete_user(self):
        add_user(301, "Delete Me", "/d")
        ok = delete_user(301)
        self.assertTrue(ok)
        self.assertIsNone(get_user(301))

    def test_delete_nonexistent_user(self):
        ok = delete_user(9999)
        self.assertFalse(ok)

    def test_user_exists(self):
        add_user(401, "Exists", "/e")
        self.assertTrue(user_exists(401))
        self.assertFalse(user_exists(9999))

    def test_user_count(self):
        self.assertEqual(get_user_count(), 0)
        add_user(101, "A", "/a")
        add_user(102, "B", "/b")
        self.assertEqual(get_user_count(), 2)


class TestAttendanceOperations(unittest.TestCase):

    def setUp(self):
        for f in (S.USERS_CSV, S.ATTENDANCE_CSV):
            if os.path.exists(f):
                os.remove(f)
        initialise_db()
        add_user(101, "Test User", "/dataset/101")

    def test_log_entry(self):
        log_id = log_attendance(101, "Test User", ATTENDANCE_ENTRY)
        self.assertIsNotNone(log_id)
        self.assertEqual(len(log_id), 8)

    def test_get_last_log(self):
        log_attendance(101, "Test User", ATTENDANCE_ENTRY)
        last = get_last_log(101)
        self.assertIsNotNone(last)
        self.assertEqual(last["type"], ATTENDANCE_ENTRY)

    def test_get_last_log_none(self):
        last = get_last_log(9999)
        self.assertIsNone(last)

    def test_attendance_today(self):
        log_attendance(101, "Test User", ATTENDANCE_ENTRY)
        log_attendance(101, "Test User", ATTENDANCE_EXIT)
        today = get_attendance_today()
        self.assertEqual(len(today), 2)

    def test_multiple_logs(self):
        for i in range(5):
            log_attendance(101, "Test User", ATTENDANCE_ENTRY if i % 2 == 0 else ATTENDANCE_EXIT)
        today = get_attendance_today()
        self.assertEqual(len(today), 5)


# ── Cleanup ────────────────────────────────────────────────────────────────────

def tearDownModule():
    shutil.rmtree(TMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
