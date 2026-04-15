"""Centralised logger configuration."""

import logging
import sys


def setup_logger(level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root application logger.

    Outputs structured log lines to stdout with timestamp, level, and message.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger("h1watcher")
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False

    return root
