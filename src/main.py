import argparse
import getpass
import json
import os
import socket


MAX_CD_ARGUMENTS = 1
MAX_LS_ARGUMENTS = 1
PARENT_DIRECTORY = ".."
ROOT_PATH = "/"


def load_vfs(vfs_path):
    """Load a virtual file system from a JSON file."""
    if vfs_path is None:
        return None

    try:
        with open(vfs_path, encoding="utf-8") as vfs_file:
            vfs = json.load(vfs_file)
    except FileNotFoundError:
        print(f"Error: VFS file not found: {vfs_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: invalid VFS format: {vfs_path}")
        return None

    if not validate_vfs(vfs):
        print(f"Error: invalid VFS structure: {vfs_path}")
        return None

    return vfs


def validate_node(node):
    """Check one file or directory node of the VFS."""
    if not isinstance(node, dict):
        return False

    node_type = node.get("type")

    if node_type == "directory":
        children = node.get("children")

        if not isinstance(children, dict):
            return False

        return all(validate_node(child) for child in children.values())

    if node_type == "file":
        return isinstance(node.get("content"), str)

    return False


def validate_vfs(vfs):
    """Check the complete virtual file system structure."""
    return validate_node(vfs)


def create_default_vfs():
    """Create an empty virtual file system in memory."""
    return {
        "type": "directory",
        "children": {},
    }


def create_shell_state(vfs):
    """Create the initial state of the shell emulator."""
    return {
        "vfs": vfs,
        "current_path": [],
        "history": [],
    }


def normalize_path(current_path, path):
    """Convert a shell path to a normalized VFS path."""
    if path.startswith(ROOT_PATH):
        result = []
    else:
        result = current_path.copy()

    for part in path.split("/"):
        if not part or part == ".":
            continue

        if part == PARENT_DIRECTORY:
            if result:
                result.pop()
            continue

        result.append(part)

    return result


def get_node(vfs, path):
    """Return a VFS node located at the specified path."""
    node = vfs

    for part in path:
        if node.get("type") != "directory":
            return None

        children = node.get("children", {})

        if part not in children:
            return None

        node = children[part]

    return node


def resolve_path(state, path):
    """Resolve a shell path and return its VFS node and path."""
    target_path = normalize_path(
        state["current_path"],
        path,
    )
    node = get_node(
        state["vfs"],
        target_path,
    )
    return node, target_path


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


def run_ls(arguments, state):
    """List files and directories in the virtual file system."""
    if len(arguments) > MAX_LS_ARGUMENTS:
        print("Error: ls accepts no more than one argument.")
        return True

    target = arguments[0] if arguments else "."
    node, _ = resolve_path(state, target)

    if node is None:
        print(f"Error: ls: path not found: {target}")
        return True

    if node["type"] == "file":
        print(target)
        return False

    names = sorted(node["children"])
    print(" ".join(names))
    return False


def run_cd(arguments, state):
    """Change the current directory in the virtual file system."""
    if len(arguments) > MAX_CD_ARGUMENTS:
        print("Error: cd accepts no more than one argument.")
        return True

    target = arguments[0] if arguments else ROOT_PATH
    node, target_path = resolve_path(state, target)

    if node is None:
        print(f"Error: cd: path not found: {target}")
        return True

    if node["type"] != "directory":
        print(f"Error: cd: not a directory: {target}")
        return True

    state["current_path"] = target_path
    return False


def run_echo(arguments):
    """Print command arguments to the console."""
    print(" ".join(arguments))
    return False


def run_clear(arguments):
    """Clear the terminal screen."""
    if arguments:
        print("Error: clear does not accept arguments.")
        return True

    clear_command = "cls" if os.name == "nt" else "clear"
    os.system(clear_command)
    return False


def run_history(arguments, state):
    """Print commands entered during the current session."""
    if arguments:
        print("Error: history does not accept arguments.")
        return True

    for index, command in enumerate(state["history"], start=1):
        print(f"{index} {command}")

    return False


def run_exit(arguments):
    """Process exit and return running and error states."""
    if arguments:
        print("Error: exit does not accept arguments.")
        return True, True

    return False, False


def execute_command(command, arguments, state):
    """Execute a command and return running and error states."""
    if command == "ls":
        return True, run_ls(arguments, state)

    if command == "cd":
        return True, run_cd(arguments, state)

    if command == "echo":
        return True, run_echo(arguments)

    if command == "clear":
        return True, run_clear(arguments)

    if command == "history":
        return True, run_history(arguments, state)

    if command == "exit":
        return run_exit(arguments)

    print(f"Error: unknown command: {command}")
    return True, True


def execute_input(user_input, state):
    """Parse and execute one line of shell input."""
    command, arguments = parse_command(user_input)

    if not command:
        return True, False

    state["history"].append(user_input.strip())
    return execute_command(
        command,
        arguments,
        state,
    )


def run_repl(prompt, state):
    """Run the interactive shell loop."""
    is_running = True

    while is_running:
        user_input = input(prompt)
        is_running, _ = execute_input(
            user_input,
            state,
        )


def run_script(script_path, prompt, state):
    """Run startup commands until completion, exit, or an error."""
    try:
        script_file = open(script_path, encoding="utf-8")
    except OSError:
        print(f"Error: cannot open startup script: {script_path}")
        return False

    with script_file:
        for raw_line in script_file:
            user_input = raw_line.strip()

            if not user_input:
                continue

            print(f"{prompt}{user_input}")
            is_running, has_error = execute_input(
                user_input,
                state,
            )

            if has_error or not is_running:
                return is_running

    return True


def main():
    """Configure and run the shell emulator."""
    arguments = parse_arguments()
    print_configuration(arguments)

    vfs = load_vfs(arguments.vfs_path)

    if arguments.vfs_path and vfs is None:
        return

    if vfs is None:
        vfs = create_default_vfs()

    state = create_shell_state(vfs)
    prompt = build_prompt(arguments.prompt)

    if arguments.script_path:
        is_running = run_script(
            arguments.script_path,
            prompt,
            state,
        )
        if not is_running:
            return

    run_repl(prompt, state)


if __name__ == "__main__":
    main()