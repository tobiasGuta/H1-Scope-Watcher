"""
Config loader — reads config.yaml and merges environment variable overrides.

Environment variables take precedence over values in config.yaml.
Sensitive values (tokens, webhook URLs) should be set via env vars, not hardcoded
in the YAML file, especially when pushing to GitHub.
"""

import os
import yaml
from typing import Any


# Map of env variable names → nested config key paths (dot-separated)
ENV_OVERRIDES: dict[str, str] = {
    # HackerOne credentials
    "H1_USERNAME": "hackerone.username",
    "H1_API_TOKEN": "hackerone.api_token",
    # Notifiers
    "DISCORD_WEBHOOK_URL": "notifiers.discord.webhook_url",
    "TELEGRAM_BOT_TOKEN": "notifiers.telegram.bot_token",
    "TELEGRAM_CHAT_ID": "notifiers.telegram.chat_id",
    "SLACK_WEBHOOK_URL": "notifiers.slack.webhook_url",
    # General
    "CHECK_INTERVAL_MINUTES": "scheduler.interval_minutes",
    "LOG_LEVEL": "log_level",
    "STORAGE_PATH": "storage.path",
}


def _set_nested(d: dict, key_path: str, value: Any) -> None:
    """Set a value in a nested dict using a dot-separated key path."""
    keys = key_path.split(".")
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def load_config(path: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file, then apply environment variable overrides.

    Args:
        path: Path to the YAML config file.

    Returns:
        Merged configuration dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    with open(path, "r") as fh:
        cfg: dict = yaml.safe_load(fh) or {}

    # Apply environment variable overrides
    for env_key, cfg_path in ENV_OVERRIDES.items():
        value = os.environ.get(env_key)
        if value is not None:
            # Coerce integer fields
            if env_key == "CHECK_INTERVAL_MINUTES":
                try:
                    value = int(value)  # type: ignore[assignment]
                except ValueError:
                    pass
            _set_nested(cfg, cfg_path, value)

    return cfg
