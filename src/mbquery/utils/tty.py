"""TTY detection for auto-format selection."""
import sys


def is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def auto_format() -> str:
    return "table" if is_tty() else "json"
