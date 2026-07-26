"""Main entry point for the freelance job finder."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List

from .config import AppConfig
from .deduplicator import Deduplicator
from .models import JobPosting, RunSummary
from .normalizer import normalize_postings
from .notifiers.base import BaseNotifier
from .ranker import Ranker
from .scrapers.freelance_de import FreelanceDeScraper
from .scrapers.freelancermap import FreelancermapScraper
from .scrapers.gulp import GulpScraper
from .scrapers.jobserve import JobserveScraper
from .storage import Storage


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def _build_notifiers(cfg: AppConfig) -> List[BaseNotifier]:
    """Build enabled notification channels."""
    notifiers: List[BaseNotifier] = []

    if cfg.telegram_enabled:
        token = cfg.telegram_bot_token
        chat_id = cfg.telegram_chat_id
        if token and chat_id:
            from .notifiers.telegram_notifier import TelegramNotifier
            notifiers.append(TelegramNotifier(token, chat_id))
            logging.getLogger(__name__).info("Telegram notifier enabled")
        else:
            logging.getLogger(__name__).warning(
                "Telegram enabled in config but TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID "
                "env vars are missing – skipping"
            )

    if cfg.email_enabled:
        host = cfg.smtp_host
        username = cfg.smtp_username
        password = cfg.smtp_password
        from_addr = cfg.smtp_from
        to_addr = cfg.smtp_to
        if all([host, username, password, from_addr, to_addr]):
            from .notifiers.email_notifier import EmailNotifier
            notifiers.append(
                EmailNotifier(
                    host=host,  # type: ignore[arg-type]
                    port=cfg.smtp_port,
                    username=username,  # type: ignore[arg-type]
                    password=password,  # type: ignore[arg-type]
                    from_addr=from_addr,  # type: ignore[arg-type]
                    to_addr=to_addr,  # type: ignore[arg-type]
                )
            )
            logging.getLogger(__name__).info("Email notifier enabled")
        else:
            logging.getLogger(__name__).warning(
                "Email enabled in config but one or more SMTP env vars are missing – skipping"
            )

    return notifiers


def _build_scrapers(cfg: AppConfig) -> dict:
    """Build enabled scrapers."""
    all_scrapers = {
        "freelancermap": FreelancermapScraper(
            min_delay=cfg.rate_limit_min, max_delay=cfg.rate_limit_max
        ),
        "freelance_de": FreelanceDeScraper(
            min_delay=cfg.rate_limit_min, max_delay=cfg.rate_limit_max
        ),
        "gulp": GulpScraper(
            min_delay=cfg.rate_limit_min, max_delay=cfg.rate_limit_max
        ),
        "jobserve": JobserveScraper(
            min_delay=cfg.rate_limit_min, max_delay=cfg.rate_limit_max
        ),
    }
    enabled = cfg.enabled_sites
    if enabled:
        return {k: v for k, v in all_scrapers.items() if k in enabled}
    return all_scrapers


def run(cfg: AppConfig) -> RunSummary:
    """Main pipeline: scrape → normalize → deduplicate → rank → notify."""
    logger = logging.getLogger(__name__)
    summary = RunSummary()

    # ── Storage & deduplicator ────────────────────────────────────────────
    db_path = cfg.db_path
    storage = Storage(db_path)
    deduplicator = Deduplicator(storage)
    ranker = Ranker(
        weights=cfg.ranking_weights or None,
        location_boost=cfg.location_boost,
    )

    # ── Scrape ────────────────────────────────────────────────────────────
    scrapers = _build_scrapers(cfg)
    all_postings: List[JobPosting] = []

    for name, scraper in scrapers.items():
        try:
            logger.info("Running scraper: %s", name)
            results = scraper.search(cfg.keywords, cfg.locations)
            all_postings.extend(results)
            summary.sites_searched.append(name)
            logger.info("Scraper %s: %d postings", name, len(results))
        except Exception as exc:  # noqa: BLE001
            msg = f"Scraper {name} failed: {exc}"
            logger.error(msg)
            summary.errors.append(msg)

    summary.total_fetched = len(all_postings)
    logger.info("Total fetched: %d", summary.total_fetched)

    # ── Normalize ─────────────────────────────────────────────────────────
    normalized = normalize_postings(all_postings)

    # ── Deduplicate ───────────────────────────────────────────────────────
    new_postings = deduplicator.filter_new(normalized)
    summary.total_new = len(new_postings)
    logger.info("New postings (after dedup): %d", summary.total_new)

    # ── Rank ──────────────────────────────────────────────────────────────
    ranked = ranker.rank(new_postings)

    # ── Notify ────────────────────────────────────────────────────────────
    if not ranked and not cfg.heartbeat_when_empty:
        logger.info("No new postings; skipping notifications")
        storage.close()
        return summary

    notifiers = _build_notifiers(cfg)
    for notifier in notifiers:
        try:
            notifier.send(ranked)
        except Exception as exc:  # noqa: BLE001
            msg = f"Notifier {type(notifier).__name__} failed: {exc}"
            logger.error(msg)
            summary.errors.append(msg)

    storage.close()
    return summary


def main() -> None:
    cfg = AppConfig()
    _setup_logging(cfg.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting freelance job finder run")
    summary = run(cfg)
    logger.info(
        "Run complete: fetched=%d new=%d errors=%d",
        summary.total_fetched,
        summary.total_new,
        len(summary.errors),
    )
    if summary.errors:
        logger.warning("Errors encountered: %s", summary.errors)


if __name__ == "__main__":
    main()
