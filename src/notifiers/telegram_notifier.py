"""Telegram notifier – sends job postings via the Telegram Bot API."""

from __future__ import annotations

import logging
from typing import List, Optional

import requests

from ..models import JobPosting
from .base import BaseNotifier

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4096


def _format_posting(posting: JobPosting, index: int) -> str:
    """Format a single posting as a Telegram message snippet."""
    parts = [f"*{index}. {posting.title}*"]
    if posting.company:
        parts.append(f"🏢 {posting.company}")
    if posting.location:
        parts.append(f"📍 {posting.location}")
    if posting.rate:
        parts.append(f"💶 {posting.rate}")
    if posting.relevance_summary:
        parts.append(f"🔍 {posting.relevance_summary}")
    parts.append(f"🔗 {posting.url}")
    parts.append(f"📡 Source: {posting.source_site}")
    return "\n".join(parts)


def _split_messages(text: str, max_len: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """Split text into chunks that fit within Telegram's message size limit."""
    if len(text) <= max_len:
        return [text]
    chunks: List[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks


class TelegramNotifier(BaseNotifier):
    """Sends job digest messages via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = bot_token
        self._chat_id = chat_id

    def send(self, postings: List[JobPosting]) -> None:
        if not postings:
            logger.info("Telegram: no postings to send")
            return

        header = f"🚀 *Freelance Job Finder – {len(postings)} new posting(s)*\n\n"
        body_parts = [
            _format_posting(p, i + 1) for i, p in enumerate(postings)
        ]
        full_text = header + "\n\n---\n\n".join(body_parts)

        for chunk in _split_messages(full_text):
            self._send_message(chunk)

    def _send_message(self, text: str) -> None:
        url = TELEGRAM_API_BASE.format(token=self._token)
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Telegram message sent successfully")
        except requests.RequestException as exc:
            logger.error("Failed to send Telegram message: %s", exc)
