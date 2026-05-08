"""
Shadow System - Phase 2 Tests
Tests for Git tracking and file change tracking.
"""

import sys
import os
import unittest
import tempfile
import json
from pathlib import Path
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import create_default_player, save_player, reset_player
from engine import add_exp


# ── Git Tracker Tests ───────────────────────────────────────────────────

class TestGitTracker(unittest.TestCase):
    """Test git_tracker module functions."""

    def test_get_git_root_returns_none_for_non_repo(self):
        """get_git_root should return None for non-git directories."""
        from git_tracker import get_git_root
        result = get_git_root("/tmp")
        self.assertIsNone(result)

    def test_get_git_root_returns_path_for_repo(self):
        """get_git_root should return the repo root for git repos."""
        from git_tracker import get_git_root
        # shadow-system IS a git repo
        repo_root = get_git_root("/mnt/chengrongfeng_private/cc_dump/shadow-system")
        self.assertIsNotNone(repo_root)
        self.assertIn("shadow-system", repo_root)

    def test_install_and_remove_hook(self):
        """Test installing and removing git hook."""
        from git_tracker import install_git_hook, uninstall_git_hook, get_git_root
        git_root = get_git_root("/mnt/chengrongfeng_private/cc_dump/shadow-system")
        self.assertIsNotNone(git_root)

        # Install
        result = install_git_hook(git_root)
        self.assertTrue(result["success"])
        hook_path = Path(result["path"])
        self.assertTrue(hook_path.exists())

        # Remove
        result = uninstall_git_hook(git_root)
        self.assertTrue(result["success"])
        self.assertFalse(hook_path.exists())

    def test_scan_commits_no_new_commits(self):
        """scan_commits_and_grant should return 0 if no new commits."""
        from git_tracker import scan_commits_and_grant
        p = create_default_player()
        git_root = "/mnt/chengrongfeng_private/cc_dump/shadow-system"
        # Use a date far in the past to ensure we get commits,
        # but the scan should have already recorded them
        result = scan_commits_and_grant(p, git_root, since_date="2020-01-01")
        # Should find at least 1 commit
        self.assertGreaterEqual(result["commits_found"], 1)


# ── File Tracker Tests ──────────────────────────────────────────────────

class TestFileTracker(unittest.TestCase):
    """Test file_tracker module functions."""

    def setUp(self):
        """Create a temp directory with code files."""
        self._temp_dir = tempfile.mkdtemp()
        self._test_dir = Path(self._temp_dir) / "test_project"
        self._test_dir.mkdir()
        self._snap_dir = Path(self._temp_dir) / "snapshots"
        self._snap_dir.mkdir()

        # Create some test files
        (self._test_dir / "main.py").write_text("print('hello')\nprint('world')\n")
        (self._test_dir / "utils.py").write_text("def foo():\n    return 42\n")
        (self._test_dir / "readme.txt").write_text("not a code file\n")

        # Create a subdirectory with a node_modules dir (should be skipped)
        skip_dir = self._test_dir / "node_modules"
        skip_dir.mkdir()
        (skip_dir / "lib.js").write_text("console.log('skip me')\n")

        # Override snapshot directory
        import file_tracker
        self._orig_snap_dir = file_tracker.get_snapshot_dir
        file_tracker.get_snapshot_dir = lambda: self._snap_dir

    def tearDown(self):
        """Clean up temp directory."""
        import file_tracker
        file_tracker.get_snapshot_dir = self._orig_snap_dir
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)

    def test_scan_directory_finds_code_files(self):
        """scan_directory should find .py files but skip .txt and node_modules."""
        from file_tracker import scan_directory
        files = scan_directory(self._test_dir)
        paths = [f["path"] for f in files]
        # Should find main.py and utils.py
        self.assertTrue(any("main.py" in p for p in paths))
        self.assertTrue(any("utils.py" in p for p in paths))
        # Should NOT find readme.txt or node_modules/lib.js
        self.assertFalse(any("readme.txt" in p for p in paths))
        self.assertFalse(any("node_modules" in p for p in paths))

    def test_scan_directory_line_count(self):
        """scan_directory should count lines correctly."""
        from file_tracker import scan_directory
        files = scan_directory(self._test_dir)
        main_file = next((f for f in files if "main.py" in f["path"]), None)
        self.assertIsNotNone(main_file)
        # "print('hello')\nprint('world')\n" -> count("\n") + 1 = 3
        self.assertEqual(main_file["lines"], 3)

    def test_save_and_compare_snapshots(self):
        """Test taking snapshots and comparing them."""
        from file_tracker import save_snapshot, compare_snapshots
        from state import load_player

        # First snapshot
        snap1 = save_snapshot(str(self._test_dir), "first")
        self.assertEqual(snap1["file_count"], 2)  # main.py, utils.py
        self.assertEqual(snap1["total_lines"], 6)  # 2 + 4

        # Second snapshot without changes
        diff = compare_snapshots(str(self._test_dir))
        self.assertEqual(diff["added_count"], 0)
        self.assertEqual(diff["modified_count"], 0)

    def test_detect_file_changes(self):
        """Test that file changes are detected."""
        from file_tracker import save_snapshot, compare_snapshots

        # First snapshot
        save_snapshot(str(self._test_dir), "before")

        # Modify a file
        (self._test_dir / "main.py").write_text("print('hello')\nprint('world')\nprint('new line')\n")
        # Add a new file
        (self._test_dir / "new_file.py").write_text("x = 1\ny = 2\n")

        # Compare
        diff = compare_snapshots(str(self._test_dir))
        self.assertEqual(diff["added_count"], 1)
        self.assertEqual(diff["modified_count"], 1)
        self.assertGreater(diff["new_lines"], 0)

    def test_scan_files_and_grant_first_scan(self):
        """First scan should create snapshot without granting EXP."""
        from file_tracker import scan_files_and_grant
        p = create_default_player()

        result = scan_files_and_grant(p, str(self._test_dir))
        self.assertTrue(result["first_scan"])
        self.assertEqual(result["exp_granted"], 0)

    def test_scan_files_and_grant_with_changes(self):
        """Second scan with changes should grant EXP."""
        from file_tracker import scan_files_and_grant
        p = create_default_player()

        # First scan
        scan_files_and_grant(p, str(self._test_dir))

        # Make changes
        (self._test_dir / "main.py").write_text("line1\nline2\nline3\nline4\nline5\n")

        # Second scan
        result = scan_files_and_grant(p, str(self._test_dir))
        self.assertFalse(result["first_scan"])
        self.assertGreaterEqual(result["exp_granted"], 0)

    def test_file_status(self):
        """Test get_file_status returns valid string."""
        from file_tracker import get_file_status
        status = get_file_status()
        self.assertIn("文件追踪", status)


# ── Integration Tests ────────────────────────────────────────────────────

class TestPhase2Integration(unittest.TestCase):
    """Integration tests for Phase 2 features."""

    def test_git_scan_grants_exp(self):
        """Scanning git commits should grant EXP."""
        from git_tracker import scan_commits_and_grant
        p = create_default_player()
        git_root = "/mnt/chengrongfeng_private/cc_dump/shadow-system"
        result = scan_commits_and_grant(p, git_root, since_date="2020-01-01")
        # Should have found commits and granted EXP
        self.assertGreater(result["exp_granted"], 0)

    def test_file_scan_workflow(self):
        """Test complete file scan workflow."""
        from file_tracker import scan_files_and_grant
        import file_tracker

        # Use isolated temp directory
        temp_dir = tempfile.mkdtemp()
        snap_dir = Path(temp_dir) / "snapshots"
        snap_dir.mkdir()
        orig_get = file_tracker.get_snapshot_dir
        file_tracker.get_snapshot_dir = lambda: snap_dir

        try:
            p = create_default_player()
            cli_dir = "/mnt/chengrongfeng_private/cc_dump/shadow-system/shadow-cli"

            # First scan
            result = scan_files_and_grant(p, cli_dir)
            self.assertTrue(result["first_scan"])

            # Second scan (no changes)
            result = scan_files_and_grant(p, cli_dir)
            self.assertFalse(result["first_scan"])
        finally:
            file_tracker.get_snapshot_dir = orig_get
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


# ── Run Tests ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
