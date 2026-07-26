"""Configuration loader for freelance job finder."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# Default path for config file
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


class AppConfig:
    """Application configuration loaded from config.yaml and environment variables."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._path = config_path or DEFAULT_CONFIG_PATH
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {}
        with open(self._path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    # ── Search config ──────────────────────────────────────────────────────
    @property
    def keywords(self) -> List[str]:
        return self._data.get("search", {}).get("keywords", [])

    @property
    def locations(self) -> List[str]:
        return self._data.get("search", {}).get("locations", [])

    # ── Site config ────────────────────────────────────────────────────────
    @property
    def enabled_sites(self) -> List[str]:
        sites = self._data.get("sites", {})
        return [name for name, cfg in sites.items() if cfg.get("enabled", True)]

    def site_config(self, name: str) -> Dict[str, Any]:
        return self._data.get("sites", {}).get(name, {})

    # ── Rate limits ────────────────────────────────────────────────────────
    @property
    def rate_limit_min(self) -> float:
        return float(self._data.get("rate_limit", {}).get("min_delay", 2.0))

    @property
    def rate_limit_max(self) -> float:
        return float(self._data.get("rate_limit", {}).get("max_delay", 5.0))

    # ── Notifications ──────────────────────────────────────────────────────
    @property
    def telegram_enabled(self) -> bool:
        return bool(
            self._data.get("notifications", {}).get("telegram", {}).get("enabled", True)
        )

    @property
    def email_enabled(self) -> bool:
        return bool(
            self._data.get("notifications", {}).get("email", {}).get("enabled", True)
        )

    @property
    def heartbeat_when_empty(self) -> bool:
        """Send notifications even when there are no new postings."""
        return bool(
            self._data.get("notifications", {}).get("heartbeat_when_empty", False)
        )

    # ── Telegram secrets (from env) ────────────────────────────────────────
    @property
    def telegram_bot_token(self) -> Optional[str]:
        return os.environ.get("TELEGRAM_BOT_TOKEN")

    @property
    def telegram_chat_id(self) -> Optional[str]:
        return os.environ.get("TELEGRAM_CHAT_ID")

    # ── SMTP secrets (from env) ────────────────────────────────────────────
    @property
    def smtp_host(self) -> Optional[str]:
        return os.environ.get("SMTP_HOST")

    @property
    def smtp_port(self) -> int:
        return int(os.environ.get("SMTP_PORT", "587"))

    @property
    def smtp_username(self) -> Optional[str]:
        return os.environ.get("SMTP_USERNAME")

    @property
    def smtp_password(self) -> Optional[str]:
        return os.environ.get("SMTP_PASSWORD")

    @property
    def smtp_from(self) -> Optional[str]:
        return os.environ.get("SMTP_FROM")

    @property
    def smtp_to(self) -> Optional[str]:
        return os.environ.get("SMTP_TO")

    # ── Ranking weights ────────────────────────────────────────────────────
    @property
    def ranking_weights(self) -> Dict[str, float]:
        return self._data.get("ranking", {}).get("weights", {})

    @property
    def location_boost(self) -> float:
        return float(self._data.get("ranking", {}).get("location_boost", 1.5))

    # ── Database ───────────────────────────────────────────────────────────
    @property
    def db_path(self) -> Path:
        raw = self._data.get("database", {}).get("path", "data/seen_postings.db")
        return Path(raw)

    # ── Logging ────────────────────────────────────────────────────────────
    @property
    def log_level(self) -> str:
        return os.environ.get("LOG_LEVEL", self._data.get("log_level", "INFO")).upper()
