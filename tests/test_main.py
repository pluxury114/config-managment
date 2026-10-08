import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.main import (
    build_prompt,
    execute_command,
    load_vfs,
    parse_arguments,
    parse_command,
    run_cd,
    run_exit,
    run_ls,
    run_script,
    validate_vfs,
)


class TestShellEmulator(unittest.TestCase):
    """Test the shell emulator functionality."""

    def test_validate_empty_vfs(self):
        """Check validation of an empty VFS."""
        vfs = {
            "type": "directory",
            "children": {},
        }

        self.assertTrue(validate_vfs(vfs))

    def test_validate_nested_vfs(self):
        """Check validation of nested directories and files."""
        vfs = {
            "type": "directory",
            "children": {
                "home": {
                    "type": "directory",
                    "children": {
                        "file.txt": {
                            "type": "file",
                            "content": "text",
                        }
                    },
                }
            },
        }

        self.assertTrue(validate_vfs(vfs))

    def test_reject_invalid_nested_vfs(self):
        """Check rejection of an invalid nested VFS node."""
        vfs = {
            "type": "directory",
            "children": {
                "broken": {
                    "type": "unknown",
                }
            },
        }

        self.assertFalse(validate_vfs(vfs))

    def test_load_valid_vfs(self):
        """Check loading of a valid JSON VFS."""
        vfs_text = '{"type": "directory", "children": {}}'

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.json"
            path.write_text(
                vfs_text,
                encoding="utf-8",
            )
            vfs = load_vfs(str(path))

        self.assertIsNotNone(vfs)

    def test_load_missing_vfs(self):
        """Check handling of a missing VFS file."""
        output = StringIO()

        with redirect_stdout(output):
            vfs = load_vfs("missing-vfs.json")

        self.assertIsNone(vfs)
        self.assertIn(
            "VFS file not found",
            output.getvalue(),
        )

    def test_load_invalid_json(self):
        """Check handling of malformed VFS JSON."""
        output = StringIO()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vfs.json"
            path.write_text(
                "{invalid",
                encoding="utf-8",
            )

            with redirect_stdout(output):
                vfs = load_vfs(str(path))

        self.assertIsNone(vfs)
        self.assertIn(
            "invalid VFS format",
            output.getvalue(),
        )

    def test_build_default_prompt(self):
        """Check prompt creation from operating system data."""
        with patch(
            "src.main.getpass.getuser",
            return_value="user",
        ):
            with patch(
                "src.main.socket.gethostname",
                return_value="host",
            ):
                prompt = build_prompt()

        self.assertEqual(prompt, "user@host:~$ ")

    def test_build_custom_prompt(self):
        """Check use of a custom prompt."""
        self.assertEqual(
            build_prompt("shell> "),
            "shell> ",
        )

    def test_parse_arguments(self):
        """Check supported command-line arguments."""
        command_line = [
            "main.py",
            "--vfs",
            "vfs.json",
            "--prompt",
            "shell> ",
            "--script",
            "startup.txt",
        ]

        with patch("sys.argv", command_line):
            arguments = parse_arguments()

        self.assertEqual(
            arguments.vfs_path,
            "vfs.json",
        )
        self.assertEqual(
            arguments.prompt,
            "shell> ",
        )
        self.assertEqual(
            arguments.script_path,
            "startup.txt",
        )

    def test_parse_command(self):
        """Check splitting input into command and arguments."""
        command, arguments = parse_command(
            "ls folder file.txt"
        )

        self.assertEqual(command, "ls")
        self.assertEqual(
            arguments,
            ["folder", "file.txt"],
        )

    def test_parse_empty_command(self):
        """Check parsing of an empty input string."""
        command, arguments = parse_command("")

        self.assertEqual(command, "")
        self.assertEqual(arguments, [])

    def test_ls_stub(self):
        """Check output of the ls stub."""
        output = StringIO()

        with redirect_stdout(output):
            run_ls(["folder"])

        self.assertEqual(
            output.getvalue(),
            "ls arguments: ['folder']\n",
        )

    def test_cd_stub(self):
        """Check output of the cd stub."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_cd(["folder"])

        self.assertFalse(has_error)
        self.assertEqual(
            output.getvalue(),
            "cd arguments: ['folder']\n",
        )

    def test_cd_invalid_arguments(self):
        """Check that cd rejects too many arguments."""
        output = StringIO()

        with redirect_stdout(output):
            has_error = run_cd(
                ["one", "two"]
            )

        self.assertTrue(has_error)
        self.assertIn(
            "cd accepts no more than one argument",
            output.getvalue(),
        )

    def test_exit_without_arguments(self):
        """Check that exit stops the REPL."""
        is_running, has_error = run_exit([])

        self.assertFalse(is_running)
        self.assertFalse(has_error)

    def test_exit_with_arguments(self):
        """Check that exit rejects arguments."""
        output = StringIO()

        with redirect_stdout(output):
            is_running, has_error = run_exit(
                ["now"]
            )

        self.assertTrue(is_running)
        self.assertTrue(has_error)
        self.assertIn(
            "exit does not accept arguments",
            output.getvalue(),
        )

    def test_unknown_command(self):
        """Check reporting of an unknown command."""
        output = StringIO()

        with redirect_stdout(output):
            is_running, has_error = execute_command(
                "unknown",
                [],
            )

        self.assertTrue(is_running)
        self.assertTrue(has_error)
        self.assertIn(
            "unknown command",
            output.getvalue(),
        )

    def test_script_stops_on_error(self):
        """Check that a startup script stops after an error."""
        script_text = (
            "ls first\n"
            "unknown\n"
            "ls skipped\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "startup.txt"
            script_path.write_text(
                script_text,
                encoding="utf-8",
            )
            output = StringIO()

            with redirect_stdout(output):
                run_script(
                    str(script_path),
                    "test> ",
                )

        self.assertIn(
            "ls arguments: ['first']",
            output.getvalue(),
        )
        self.assertNotIn(
            "ls arguments: ['skipped']",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()