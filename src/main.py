import argparse
import getpass
import socket


MAX_CD_ARGUMENTS = 1


def parse_arguments():
    """Parse command-line arguments of the emulator."""
    parser = argparse.ArgumentParser(
        description="UNIX-like shell emulator",
    )
    parser.add_argument(
        "--vfs",
        dest="vfs_path",
        help="Path to the VFS file",
    )
    parser.add_argument(
        "--prompt",
        help="Custom REPL prompt",
    )
    parser.add_argument(
        "--script",
        dest="script_path",
        help="Path to the startup script",
    )
    return parser.parse_args()


def print_configuration(arguments):
    """Print command-line configuration values."""
    print("Configuration:")
    print(f"VFS path: {arguments.vfs_path}")
    print(f"Prompt: {arguments.prompt}")
    print(f"Startup script: {arguments.script_path}")


def build_prompt(custom_prompt=None):
    """Create a shell prompt or use a custom prompt."""
    if custom_prompt is not None:
        return custom_prompt

    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"{username}@{hostname}:~$ "


def parse_command(user_input):
    """Split user input into a command and its arguments."""
    parts = user_input.split()

    if not parts:
        return "", []

    return parts[0], parts[1:]


def run_ls(arguments):
    """Print the name and arguments of the ls stub command."""
    print(f"ls arguments: {arguments}")


def run_cd(arguments):
    """Print cd arguments and report whether an error occurred."""
    if len(arguments) > MAX_CD_ARGUMENTS:
        print("Error: cd accepts no more than one argument.")
        return True

    print(f"cd arguments: {arguments}")
    return False


def run_exit(arguments):
    """Process exit and return running and error states."""
    if arguments:
        print("Error: exit does not accept arguments.")
        return True, True

    return False, False


def execute_command(command, arguments):
    """Execute a command and return running and error states."""
    if not command:
        return True, False

    if command == "ls":
        run_ls(arguments)
        return True, False

    if command == "cd":
        has_error = run_cd(arguments)
        return True, has_error

    if command == "exit":
        return run_exit(arguments)

    print(f"Error: unknown command: {command}")
    return True, True


def run_repl(prompt):
    """Run the interactive shell loop."""
    is_running = True

    while is_running:
        user_input = input(prompt)
        command, arguments = parse_command(user_input)
        is_running, _ = execute_command(command, arguments)


def run_script(script_path, prompt):
    """Run startup commands until completion, exit, or an error."""
    try:
        script_file = open(script_path, encoding="utf-8")
    except OSError:
        print(f"Error: cannot open startup script: {script_path}")
        return True

    with script_file:
        for raw_line in script_file:
            user_input = raw_line.strip()

            if not user_input:
                continue

            print(f"{prompt}{user_input}")
            command, arguments = parse_command(user_input)
            is_running, has_error = execute_command(
                command,
                arguments,
            )

            if has_error or not is_running:
                return is_running

    return True


def main():
    """Configure and run the shell emulator."""
    arguments = parse_arguments()
    print_configuration(arguments)

    prompt = build_prompt(arguments.prompt)

    if arguments.script_path:
        is_running = run_script(
            arguments.script_path,
            prompt,
        )
        if not is_running:
            return

    run_repl(prompt)


if __name__ == "__main__":
    main()