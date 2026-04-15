"""Slack incoming-webhook notifier."""

import logging
from typing import Any

import requests

from core.differ import ScopeDiff
from notifiers.base import BaseNotifier

logger = logging.getLogger("h1watcher.notifiers.slack")


class SlackNotifier(BaseNotifier):
    """
    Posts messages to a Slack channel via an Incoming Webhook.

    Setup:
        1. Go to https://api.slack.com/apps → Create New App → Incoming Webhooks.
        2. Activate Incoming Webhooks, click "Add New Webhook to Workspace".
        3. Copy the Webhook URL into config.yaml or SLACK_WEBHOOK_URL env var.
    """

    name = "slack"

    def __init__(self, cfg: dict) -> None:
        self._webhook_url: str = cfg.get("webhook_url", "").strip()

    def is_configured(self) -> bool:
        return bool(self._webhook_url)

    def send(self, diff: ScopeDiff, program_info: dict[str, Any]) -> None:
        lines = self.build_message_lines(diff, program_info)
        text = "\n".join(lines)

        # Slack's Block Kit for richer formatting
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔍 Scope change — {program_info.get('name', diff.handle)}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text[:2900],  # Slack block text limit ~3000 chars
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"<{program_info.get('url', '#')}|View on HackerOne> · H1 Scope Watcher",
                        }
                    ],
                },
            ]
        }

        try:
            resp = requests.post(self._webhook_url, json=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Slack notification sent for %s", diff.handle)
        except requests.RequestException as exc:
            logger.error("Slack notification failed: %s", exc)
            raise
