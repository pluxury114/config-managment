import getpass
import socket


MAX_CD_ARGUMENTS = 1


def build_prompt():
    """Create a shell prompt from the current user and host names."""
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
    """Print cd arguments or report an invalid argument count."""
    if len(arguments) > MAX_CD_ARGUMENTS:
        print("Error: cd accepts no more than one argument.")
        return

    print(f"cd arguments: {arguments}")


def run_exit(arguments):
    """Validate exit arguments and return the REPL state."""
    if arguments:
        print("Error: exit does not accept arguments.")
        return True

    return False


def execute_command(command, arguments):
    """Execute one emulator command and return the REPL state."""
    if not command:
        return True

    if command == "ls":
        run_ls(arguments)
        return True

    if command == "cd":
        run_cd(arguments)
        return True

    if command == "exit":
        return run_exit(arguments)

    print(f"Error: unknown command: {command}")
    return True


def main():
    """Run the interactive shell emulator."""
    prompt = build_prompt()
    is_running = True

    while is_running:
        user_input = input(prompt)
        command, arguments = parse_command(user_input)
        is_running = execute_command(command, arguments)


if __name__ == "__main__":
    main()