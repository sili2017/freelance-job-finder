"""Scraper for freelance.de.

NOTE: CSS selectors and URL patterns are best-effort placeholders.
Validate against the live site before use. Check robots.txt and ToS.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.freelance.de"
#SEARCH_URL = f"{BASE_URL}/Projekte/Suche/"

SEARCH_URL = f"{BASE_URL}/projekte"
https://www.freelance.de/projekte?skills=mulesoft&sortBy=last_update

# TODO: validate selectors against live site markup
SEL_LISTING = "div.project-list-item, article.project-item, .project"
SEL_TITLE = "h2 a, h3 a, .project-title a"
SEL_COMPANY = ".company, .client-name"
SEL_LOCATION = ".location, .project-location"
SEL_DATE = ".date, time, .publish-date"
SEL_RATE = ".rate, .budget, .tagessatz"
SEL_DESCRIPTION = ".description, .excerpt, .teaser"


class FreelanceDeScraper(BaseScraper):
    """Scraper for freelance.de project listings."""

    site_name = "freelance.de"

    def search(self, keywords: List[str], locations: List[str]) -> List[JobPosting]:
        if not self._is_allowed_by_robots(BASE_URL, "/Projekte/Suche/"):
            logger.warning("robots.txt disallows scraping %s – skipping", BASE_URL)
            return []

        postings: List[JobPosting] = []

        for keyword in keywords:
            logger.info("Searching %s for keyword: %s", self.site_name, keyword)
            params = {"suchart": "ALL", "query": keyword}
            url = f"{SEARCH_URL}?{urlencode(params)}"
            resp = self._get(url)
            if resp is None:
                logger.warning("No response from %s for keyword=%s", self.site_name, keyword)
                continue

            try:
                batch = self._parse(resp.text, keyword)
                postings.extend(batch)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Parse error on %s (keyword=%s): %s", self.site_name, keyword, exc)

        logger.info("Fetched %d postings from %s", len(postings), self.site_name)
        return postings

    def _parse(self, html: str, matched_keyword: str) -> List[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        listings = soup.select(SEL_LISTING)
        results: List[JobPosting] = []

        for item in listings:
            try:
                posting = self._parse_item(item, matched_keyword)
                if posting:
                    results.append(posting)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error parsing listing on %s: %s", self.site_name, exc)

        return results

    def _parse_item(self, item: BeautifulSoup, matched_keyword: str) -> Optional[JobPosting]:  # type: ignore[valid-type]
        # TODO: validate selectors against live site
        title_el = item.select_one(SEL_TITLE)
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title:
            return None

        href = title_el.get("href", "")
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        company_el = item.select_one(SEL_COMPANY)
        company = company_el.get_text(strip=True) if company_el else None

        location_el = item.select_one(SEL_LOCATION)
        location = location_el.get_text(strip=True) if location_el else None

        rate_el = item.select_one(SEL_RATE)
        rate = rate_el.get_text(strip=True) if rate_el else None

        desc_el = item.select_one(SEL_DESCRIPTION)
        description = desc_el.get_text(strip=True) if desc_el else None

        return JobPosting(
            title=title,
            company=company,
            location=location,
            url=url,
            posted_date=None,
            rate=rate,
            source_site=self.site_name,
            description=description,
            matched_keywords=[matched_keyword],
        )
