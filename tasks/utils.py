from pathlib import Path

path = Path(__file__)
TASKS_DIR = path.parent
REPO_BASE = TASKS_DIR.parent


def escape_path(path: Path) -> str:
    """Escape special characters in the provided path string to make it shell-safe."""
    translation_table: dict[int, str] = {
        ord("-"): r"\-",
        ord("]"): r"\]",
        ord("\\"): r"\\",
        ord("^"): r"\^",
        ord("$"): r"\$",
        ord("*"): r"\*",
        ord("("): r"\(",
        ord(")"): r"\)",
        ord("."): r"\.",
    }
    return str(path).translate(translation_table)


ESCAPED_REPO_PATH = escape_path(REPO_BASE)
