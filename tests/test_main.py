import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.main import (
    build_prompt,
    create_default_vfs,
    create_shell_state,
    execute_command,
    execute_input,
    get_node,
    load_vfs,
    normalize_path,
    parse_arguments,
    parse_command,
    run_cd,
    run_clear,
    run_echo,
    run_exit,
    run_history,
    run_ls,
    run_script,
    validate_vfs,
)


def make_vfs():
    """Create a VFS used by command tests."""
    return {
        "type": "directory",
        "children": {
            "home": {
                "type": "directory",
                "children": {
                    "user": {
                        "type": "directory",
                        "children": {},
                    }
                },
            },
            "readme.txt": {
                "type": "file",
                "content": "hello",
            },
        },
    }


class TestShellEmulator(unittest.TestCase):
    """Test the shell emulator functions."""

    def setUp(self):
        """Create a fresh shell state for every test."""
        self.vfs = make_vfs()
        self.state = create_shell_state(self.vfs)

    def test_parse_command(self):
        """Check splitting of a command and its arguments."""
        command, arguments = parse_command("echo hello world")
        self.assertEqual(command, "echo")
        self.assertEqual(arguments, ["hello", "world"])

    def test_parse_empty_command(self):
        """Check parsing of empty input."""
        command, arguments = parse_command("   ")
        self.assertEqual(command, "")
        self.assertEqual(arguments, [])

    def test_custom_prompt(self):
        """Check use of a custom prompt."""
        self.assertEqual(build_prompt("test> "), "test> ")

    def test_parse_arguments(self):
        """Check supported command-line arguments."""
        values = [
            "main.py",
            "--vfs",
            "vfs/test.json",
            "--prompt",
            "test> ",
            "--script",
            "script.txt",
        ]

        with patch("sys.argv", values):
            arguments = parse_arguments()

        self.assertEqual(arguments.vfs_path, "vfs/test.json")
        self.assertEqual(arguments.prompt, "test> ")
        self.assertEqual(arguments.script_path, "script.txt")

    def test_validate_valid_vfs(self):
        """Check validation of a correct VFS."""
        self.assertTrue(validate_vfs(self.vfs))

    def test_validate_invalid_vfs(self):
        """Check validation of an incorrect VFS."""
        self.assertFalse(validate_vfs({"type": "directory"}))

    def test_load_valid_vfs(self):
        """Check loading of a valid JSON VFS."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.json"
            path.write_text(
                json.dumps(self.vfs),
                encoding="utf-8",
            )
            loaded = load_vfs(path)

        self.assertEqual(loaded, self.vfs)

    def test_load_invalid_json(self):
        """Check handling of invalid VFS JSON."""
        output = StringIO()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.json"
            path.write_text(
                "{invalid",
                encoding="utf-8",
            )

            with redirect_stdout(output):
                loaded = load_vfs(path)

        self.assertIsNone(loaded)
        self.assertIn(
            "invalid VFS format",
            output.getvalue(),
        )

    def test_load_missing_vfs(self):
        """Check handling of a missing VFS file."""
        output = StringIO()

        with redirect_stdout(output):
            loaded = load_vfs("missing-vfs.json")

        self.assertIsNone(loaded)
        self.assertIn(
            "VFS file not found",
            output.getvalue(),
        )

    def test_create_default_vfs(self):
        """Check creation of an empty in-memory VFS."""
        vfs = create_default_vfs()

        self.assertEqual(vfs["type"], "directory")
        self.assertEqual(vfs["children"], {})

    def test_create_shell_state(self):
        """Check initial shell state values."""
        state = create_shell_state(self.vfs)

        self.assertIs(state["vfs"], self.vfs)
        self.assertEqual(state["current_path"], [])
        self.assertEqual(state["history"], [])

    def test_normalize_relative_path(self):
        """Check normalization of a relative path."""
        path = normalize_path(
            ["home"],
            "user",
        )

        self.assertEqual(
            path,
            ["home", "user"],
        )

    def test_normalize_parent_path(self):
        """Check normalization of a parent path."""
        path = normalize_path(
            ["home", "user"],
            "..",
        )

        self.assertEqual(
            path,
            ["home"],
        )

    def test_normalize_absolute_path(self):
        """Check normalization of an absolute path."""
        path = normalize_path(
            ["home"],
            "/home/user",
        )

        self.assertEqual(
            path,
            ["home", "user"],
        )

    def test_get_node(self):
        """Check VFS node lookup."""
        node = get_node(
            self.vfs,
            ["home", "user"],
        )

        self.assertEqual(
            node["type"],
            "directory",
        )

    def test_ls_current_directory(self):
        """Check listing of the current directory."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_ls(
                [],
                self.state,
            )

        self.assertFalse(has_error)
        self.assertEqual(
            output.getvalue().strip(),
            "home readme.txt",
        )

    def test_ls_directory_path(self):
        """Check listing of a specified directory."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_ls(
                ["home"],
                self.state,
            )

        self.assertFalse(has_error)
        self.assertEqual(
            output.getvalue().strip(),
            "user",
        )

    def test_ls_missing_path(self):
        """Check ls error for a missing path."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_ls(
                ["missing"],
                self.state,
            )

        self.assertTrue(has_error)
        self.assertIn(
            "path not found",
            output.getvalue(),
        )

    def test_ls_too_many_arguments(self):
        """Check ls argument validation."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_ls(
                ["one", "two"],
                self.state,
            )

        self.assertTrue(has_error)
        self.assertIn(
            "no more than one",
            output.getvalue(),
        )

    def test_cd_directory(self):
        """Check changing the current VFS directory."""
        has_error = run_cd(
            ["home"],
            self.state,
        )

        self.assertFalse(has_error)
        self.assertEqual(
            self.state["current_path"],
            ["home"],
        )

    def test_cd_parent(self):
        """Check changing to the parent directory."""
        self.state["current_path"] = [
            "home",
            "user",
        ]

        has_error = run_cd(
            [".."],
            self.state,
        )

        self.assertFalse(has_error)
        self.assertEqual(
            self.state["current_path"],
            ["home"],
        )

    def test_cd_root(self):
        """Check changing to the root directory."""
        self.state["current_path"] = [
            "home",
            "user",
        ]

        has_error = run_cd(
            ["/"],
            self.state,
        )

        self.assertFalse(has_error)
        self.assertEqual(
            self.state["current_path"],
            [],
        )

    def test_cd_file_error(self):
        """Check cd error when target is a file."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_cd(
                ["readme.txt"],
                self.state,
            )

        self.assertTrue(has_error)
        self.assertIn(
            "not a directory",
            output.getvalue(),
        )

    def test_cd_missing_path(self):
        """Check cd error for a missing path."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_cd(
                ["missing"],
                self.state,
            )

        self.assertTrue(has_error)
        self.assertIn(
            "path not found",
            output.getvalue(),
        )

    def test_echo(self):
        """Check echo output."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_echo(
                ["hello", "world"],
            )

        self.assertFalse(has_error)
        self.assertEqual(
            output.getvalue().strip(),
            "hello world",
        )

    def test_clear(self):
        """Check clear without clearing the real console."""
        with patch(
            "src.main.os.system"
        ) as system_call:
            has_error = run_clear([])

        self.assertFalse(has_error)
        system_call.assert_called_once()

    def test_clear_arguments_error(self):
        """Check clear argument validation."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_clear(
                ["extra"],
            )

        self.assertTrue(has_error)
        self.assertIn(
            "does not accept",
            output.getvalue(),
        )

    def test_history(self):
        """Check history output."""
        self.state["history"] = [
            "ls",
            "cd home",
        ]
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_history(
                [],
                self.state,
            )

        self.assertFalse(has_error)
        self.assertIn(
            "1 ls",
            output.getvalue(),
        )
        self.assertIn(
            "2 cd home",
            output.getvalue(),
        )

    def test_exit(self):
        """Check successful exit command."""
        is_running, has_error = run_exit([])

        self.assertFalse(is_running)
        self.assertFalse(has_error)

    def test_exit_arguments_error(self):
        """Check exit argument validation."""
        output = StringIO()

        with redirect_stdout(output):
            is_running, has_error = run_exit(
                ["extra"],
            )

        self.assertTrue(is_running)
        self.assertTrue(has_error)
        self.assertIn(
            "does not accept",
            output.getvalue(),
        )

    def test_unknown_command(self):
        """Check handling of an unknown command."""
        output = StringIO()

        with redirect_stdout(output):
            result = execute_command(
                "unknown",
                [],
                self.state,
            )

        self.assertEqual(
            result,
            (True, True),
        )
        self.assertIn(
            "unknown command",
            output.getvalue(),
        )

    def test_execute_input_adds_history(self):
        """Check saving entered commands to history."""
        output = StringIO()

        with redirect_stdout(output):
            result = execute_input(
                "echo hello",
                self.state,
            )

        self.assertEqual(
            result,
            (True, False),
        )
        self.assertEqual(
            self.state["history"],
            ["echo hello"],
        )

    def test_script_stops_on_error(self):
        """Check startup script stopping on first error."""
        output = StringIO()
        script_text = (
            "echo before\n"
            "unknown\n"
            "echo skipped\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "startup.txt"
            path.write_text(
                script_text,
                encoding="utf-8",
            )

            with redirect_stdout(output):
                run_script(
                    path,
                    "test> ",
                    self.state,
                )

        self.assertIn(
            "before",
            output.getvalue(),
        )
        self.assertIn(
            "unknown command",
            output.getvalue(),
        )
        self.assertNotIn(
            "echo skipped",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()