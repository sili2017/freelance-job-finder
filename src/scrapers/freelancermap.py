"""Scraper for freelancermap.de.

NOTE: CSS selectors and URL patterns are best-effort placeholders based on
publicly observable site structure at time of writing.  They **must** be
validated against the live site before production use, as markup may change
without notice.  Always check the site's robots.txt and Terms of Service
before running automated requests.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

# ── Selector constants (best-effort placeholders) ─────────────────────────────
BASE_URL = "https://www.freelancermap.de"
SEARCH_URL = f"{BASE_URL}/projektboerse.html"

# TODO: validate these selectors against live site markup
SEL_LISTING = "div.project-container, article.project"
SEL_TITLE = "h2.project-title a, h3 a, .title a"
SEL_COMPANY = ".company-name, .client"
SEL_LOCATION = ".location, .project-location"
SEL_DATE = ".project-date, time[datetime], .date"
SEL_RATE = ".rate, .budget, .honorar"
SEL_DESCRIPTION = ".description, .project-description, .excerpt"
SEL_URL = "h2.project-title a, h3 a, .title a"


class FreelancermapScraper(BaseScraper):
    """Scraper for freelancermap.de project listings."""

    site_name = "freelancermap.de"

    def search(self, keywords: List[str], locations: List[str]) -> List[JobPosting]:
        """Search freelancermap.de for matching projects."""
        if not self._is_allowed_by_robots(BASE_URL, "/projektboerse.html"):
            logger.warning("robots.txt disallows scraping %s – skipping", BASE_URL)
            return []

        postings: List[JobPosting] = []

        for keyword in keywords:
            logger.info("Searching %s for keyword: %s", self.site_name, keyword)
            params = {
                "projectContractTypes[]": "contracting",
                "query": keyword,
                "country": "de",
                "projectLocations[]": "remote",
                "remoteInPercent[]": "100",
                "nameOnly": "0",
            }
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
        """Parse HTML and return a list of JobPosting objects."""
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
        """Parse a single listing element."""
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

        date_el = item.select_one(SEL_DATE)
        raw_date = None
        if date_el:
            raw_date = date_el.get("datetime") or date_el.get_text(strip=True)

        rate_el = item.select_one(SEL_RATE)
        rate = rate_el.get_text(strip=True) if rate_el else None

        desc_el = item.select_one(SEL_DESCRIPTION)
        description = desc_el.get_text(strip=True) if desc_el else None

        return JobPosting(
            title=title,
            company=company,
            location=location,
            url=url,
            posted_date=None,  # parsed in normalizer
            rate=rate,
            source_site=self.site_name,
            description=description,
            matched_keywords=[matched_keyword],
        )
