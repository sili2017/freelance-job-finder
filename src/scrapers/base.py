"""Base scraper interface."""

from __future__ import annotations

import logging
import random
import time
import urllib.robotparser
from abc import ABC, abstractmethod
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests

from ..models import JobPosting

logger = logging.getLogger(__name__)

# Realistic User-Agent string
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    #: Site name, must be set in subclasses
    site_name: str = ""

    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        max_retries: int = 3,
    ) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT

    def _sleep(self) -> None:
        """Sleep for a random duration between min_delay and max_delay."""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug("Rate-limiting: sleeping %.1fs", delay)
        time.sleep(delay)

    def _get(self, url: str, **kwargs: object) -> Optional[requests.Response]:
        """GET with retry-backoff. Returns None on permanent failure."""
        for attempt in range(1, self.max_retries + 1):
            try:
                self._sleep()
                resp = self._session.get(url, timeout=30, **kwargs)  # type: ignore[arg-type]
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                logger.warning(
                    "Request failed (%s/%s) for %s: %s",
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(2**attempt)  # exponential back-off
        return None

    def _is_allowed_by_robots(self, base_url: str, path: str = "/") -> bool:
        """Check robots.txt; returns True if scraping is allowed."""
        try:
            robots_url = urljoin(base_url, "/robots.txt")
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            allowed = rp.can_fetch(USER_AGENT, urljoin(base_url, path))
            if not allowed:
                logger.warning("robots.txt disallows scraping %s%s", base_url, path)
            return allowed
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not read robots.txt for %s: %s", base_url, exc)
            return True  # Assume allowed on error

    @abstractmethod
    def search(self, keywords: List[str], locations: List[str]) -> List[JobPosting]:
        """
        Search for job postings matching keywords and locations.

        Must be implemented by each concrete scraper.
        """
