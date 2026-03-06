"""Logging setup utilities with level-based colors."""

from __future__ import annotations

import logging
import os
import sys
from typing import TextIO


_RESET = "\x1b[0m"
_LEVEL_COLORS: dict[int, str] = {
    logging.DEBUG: "\x1b[36m",
    logging.INFO: "\x1b[32m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[1;31m",
}


class ColorLevelFormatter(logging.Formatter):
    """Format logger output and colorize level name by severity."""

    def __init__(self, fmt: str, *, use_color: bool) -> None:
        super().__init__(fmt=fmt)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if not self._use_color:
            return super().format(record)

        color = _LEVEL_COLORS.get(record.levelno)
        if not color:
            return super().format(record)

        original_level_name = record.levelname
        try:
            record.levelname = f"{color}{original_level_name}{_RESET}"
            return super().format(record)
        finally:
            record.levelname = original_level_name


def configure_colored_logging(
    *,
    level: int = logging.INFO,
    fmt: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream: TextIO | None = None,
    force: bool = True,
) -> None:
    """Configure root logger with optional ANSI colors."""
    target_stream = stream or sys.stdout
    _enable_windows_ansi(target_stream)
    use_color = _should_use_color(target_stream)

    handler = logging.StreamHandler(target_stream)
    handler.setFormatter(ColorLevelFormatter(fmt=fmt, use_color=use_color))

    root = logging.getLogger()
    if force:
        root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def _should_use_color(stream: TextIO) -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def _enable_windows_ansi(stream: TextIO) -> None:
    if os.name != "nt":
        return
    try:
        isatty = getattr(stream, "isatty", None)
        if not (isatty and isatty()):
            return

        import ctypes

        kernel32 = ctypes.windll.kernel32
        std_output_handle = -11
        enable_virtual_terminal_processing = 0x0004

        handle = kernel32.GetStdHandle(std_output_handle)
        if handle in (0, -1):
            return

        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return

        kernel32.SetConsoleMode(handle, mode.value | enable_virtual_terminal_processing)
    except Exception:
        return
