import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from src.main import (
    build_prompt,
    execute_command,
    parse_command,
    run_cd,
    run_exit,
    run_ls,
)


class TestShellEmulator(unittest.TestCase):
    """Test the first-stage shell emulator functionality."""

    def test_build_prompt(self):
        """Check that the prompt uses the OS user and host names."""
        with patch("src.main.getpass.getuser", return_value="user"):
            with patch("src.main.socket.gethostname", return_value="host"):
                self.assertEqual(build_prompt(), "user@host:~$ ")

    def test_parse_command(self):
        """Check splitting input into a command and arguments."""
        command, arguments = parse_command("ls folder file.txt")

        self.assertEqual(command, "ls")
        self.assertEqual(arguments, ["folder", "file.txt"])

    def test_parse_empty_command(self):
        """Check parsing of an empty input string."""
        command, arguments = parse_command("")

        self.assertEqual(command, "")
        self.assertEqual(arguments, [])

    def test_ls_stub(self):
        """Check output of the ls stub command."""
        output = StringIO()

        with redirect_stdout(output):
            run_ls(["folder"])

        self.assertEqual(
            output.getvalue(),
            "ls arguments: ['folder']\n",
        )

    def test_cd_stub(self):
        """Check output of the cd stub command."""
        output = StringIO()

        with redirect_stdout(output):
            run_cd(["folder"])

        self.assertEqual(
            output.getvalue(),
            "cd arguments: ['folder']\n",
        )

    def test_cd_invalid_arguments(self):
        """Check that cd rejects too many arguments."""
        output = StringIO()

        with redirect_stdout(output):
            run_cd(["one", "two"])

        self.assertEqual(
            output.getvalue(),
            "Error: cd accepts no more than one argument.\n",
        )

    def test_exit_without_arguments(self):
        """Check that exit stops the REPL."""
        self.assertFalse(run_exit([]))

    def test_exit_with_arguments(self):
        """Check that exit rejects arguments."""
        output = StringIO()

        with redirect_stdout(output):
            is_running = run_exit(["now"])

        self.assertTrue(is_running)
        self.assertEqual(
            output.getvalue(),
            "Error: exit does not accept arguments.\n",
        )

    def test_unknown_command(self):
        """Check reporting of an unknown command."""
        output = StringIO()

        with redirect_stdout(output):
            is_running = execute_command("unknown", [])

        self.assertTrue(is_running)
        self.assertEqual(
            output.getvalue(),
            "Error: unknown command: unknown\n",
        )


if __name__ == "__main__":
    unittest.main()