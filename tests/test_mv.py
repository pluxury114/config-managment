import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from src.main import (
    create_shell_state,
    execute_input,
    get_node,
    load_vfs,
    run_mv,
)


def make_vfs():
    """Create a small VFS specifically for mv tests."""
    return {
        "type": "directory",
        "children": {
            "readme.txt": {"type": "file", "content": "hello"},
            "home": {
                "type": "directory",
                "children": {
                    "user": {"type": "directory", "children": {}},
                },
            },
        },
    }


class TestMv(unittest.TestCase):
    """Check moving VFS entries without touching real files."""

    def setUp(self):
        """Create isolated state for each test."""
        self.state = create_shell_state(make_vfs())

    def test_rename_file(self):
        """Rename a file in the same directory."""
        self.assertFalse(run_mv(["readme.txt", "notes.txt"], self.state))
        self.assertIsNone(get_node(self.state["vfs"], ["readme.txt"]))
        node = get_node(self.state["vfs"], ["notes.txt"])
        self.assertEqual(node["content"], "hello")

    def test_move_file_into_directory(self):
        """Move a file to an existing directory."""
        self.assertFalse(run_mv(["readme.txt", "home/user"], self.state))
        self.assertIsNone(get_node(self.state["vfs"], ["readme.txt"]))
        path = ["home", "user", "readme.txt"]
        self.assertIsNotNone(get_node(self.state["vfs"], path))

    def test_move_directory_and_update_current_path(self):
        """Track the working directory after moving its parent."""
        self.state["current_path"] = ["home", "user"]
        self.assertFalse(run_mv(["/home", "/moved"], self.state))
        self.assertIsNone(get_node(self.state["vfs"], ["home"]))
        self.assertIsNotNone(get_node(self.state["vfs"], ["moved", "user"]))
        self.assertEqual(self.state["current_path"], ["moved", "user"])

    def test_relative_destination(self):
        """Resolve a relative destination against the virtual cwd."""
        self.state["current_path"] = ["home", "user"]
        self.assertFalse(run_mv(["/readme.txt", "notes.txt"], self.state))
        path = ["home", "user", "notes.txt"]
        self.assertIsNotNone(get_node(self.state["vfs"], path))

    def test_missing_source(self):
        """Keep VFS unchanged when the source is missing."""
        original = json.dumps(self.state["vfs"], sort_keys=True)
        with redirect_stdout(StringIO()):
            self.assertTrue(run_mv(["missing", "new.txt"], self.state))
        current = json.dumps(self.state["vfs"], sort_keys=True)
        self.assertEqual(current, original)

    def test_existing_file_destination(self):
        """Reject a destination occupied by another file."""
        with redirect_stdout(StringIO()):
            self.assertTrue(run_mv(["/home", "/readme.txt"], self.state))
        self.assertIsNotNone(get_node(self.state["vfs"], ["home"]))

    def test_conflict_inside_directory(self):
        """Reject moving a file where the same name already exists."""
        folder = get_node(self.state["vfs"], ["home", "user"])
        folder["children"]["readme.txt"] = {"type": "file", "content": "other"}
        with redirect_stdout(StringIO()):
            self.assertTrue(run_mv(["/readme.txt", "/home/user"], self.state))
        node = get_node(self.state["vfs"], ["readme.txt"])
        self.assertEqual(node["content"], "hello")

    def test_missing_destination_parent(self):
        """Reject destination if its parent is missing."""
        with redirect_stdout(StringIO()):
            arguments = ["readme.txt", "missing/new.txt"]
            self.assertTrue(run_mv(arguments, self.state))
        self.assertIsNotNone(get_node(self.state["vfs"], ["readme.txt"]))

    def test_move_directory_into_itself(self):
        """Prevent cyclic directory structure."""
        with redirect_stdout(StringIO()):
            self.assertTrue(run_mv(["home", "/home/user"], self.state))
        self.assertIsNotNone(get_node(self.state["vfs"], ["home", "user"]))

    def test_move_root(self):
        """Reject moving the VFS root."""
        with redirect_stdout(StringIO()):
            self.assertTrue(run_mv(["/", "/other"], self.state))
        self.assertIsNotNone(get_node(self.state["vfs"], []))

    def test_wrong_argument_count(self):
        """Require exactly two arguments."""
        for arguments in ([], ["readme.txt"], ["a", "b", "c"]):
            with self.subTest(arguments=arguments):
                with redirect_stdout(StringIO()):
                    self.assertTrue(run_mv(arguments, self.state))

    def test_dispatcher(self):
        """Make mv available through the normal command parser."""
        result = execute_input("mv readme.txt renamed.txt", self.state)
        self.assertEqual(result, (True, False))
        self.assertIsNotNone(get_node(self.state["vfs"], ["renamed.txt"]))

    def test_original_json_unchanged(self):
        """Change the VFS only in memory."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.json"
            path.write_text(json.dumps(make_vfs()), encoding="utf-8")
            before = path.read_bytes()
            state = create_shell_state(load_vfs(path))
            self.assertFalse(run_mv(["readme.txt", "renamed.txt"], state))
            self.assertEqual(path.read_bytes(), before)
            self.assertIsNone(get_node(state["vfs"], ["readme.txt"]))
            self.assertIsNotNone(get_node(state["vfs"], ["renamed.txt"]))


if __name__ == "__main__":
    unittest.main()
