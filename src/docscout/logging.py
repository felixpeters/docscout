"""Verbose logging for docscout."""

import sys

_verbose = False


def set_verbose(enabled: bool) -> None:
    """Enable or disable verbose logging."""
    global _verbose
    _verbose = enabled


def is_verbose() -> bool:
    """Return whether verbose logging is enabled."""
    return _verbose


def log(message: str) -> None:
    """Print a verbose message to stderr if verbose mode is on."""
    if _verbose:
        print(f"[docscout] {message}", file=sys.stderr)
