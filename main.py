#!/usr/bin/env python3
"""
H1 Scope Watcher — HackerOne program scope change detector.
Entry point: run once or in scheduled loop.
"""

import sys
import logging
import argparse

from core.watcher import ScopeWatcher
from core.config_loader import load_config
from core.logger import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="H1 Scope Watcher — Monitor HackerOne program scope changes"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run a single check then exit (ignores scheduler interval)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override log level from config",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Bootstrap minimal logging before config loads
    logging.basicConfig(level=logging.INFO)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as exc:
        logging.error("Config file not found: %s", exc)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to load config: %s", exc)
        sys.exit(1)

    log_level = args.log_level or cfg.get("log_level", "INFO")
    logger = setup_logger(log_level)
    logger.info("H1 Scope Watcher starting up…")

    watcher = ScopeWatcher(cfg, logger)

    # Send startup health ping to configured notifiers (if any)
    try:
        watcher.send_health()
    except Exception:
        logger.exception("Health ping failed")

    if args.run_once:
        logger.info("Running single check (--run-once)")
        watcher.run_check()
    else:
        watcher.run_scheduled()


if __name__ == "__main__":
    main()
