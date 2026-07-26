"""Scraper for freelance.de.

NOTE: CSS selectors and URL patterns are best-effort placeholders.
Validate against the live site before use. Check robots.txt and ToS.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.freelance.de"
ACCESS_TOKEN_URL = f"{BASE_URL}/api/ui/users/access-token"
SEARCH_API_URL = f"{BASE_URL}/api/ui/projects/search"
# Example query format:
# https://www.freelance.de/projekte?skills=mulesoft&sortBy=last_update

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
        if not self._is_allowed_by_robots(BASE_URL, "/projekte"):
            logger.warning("robots.txt disallows scraping %s – skipping", BASE_URL)
            return []

        postings: List[JobPosting] = []
        token = self._get_access_token()
        if not token:
            logger.warning("Could not obtain API token from %s", self.site_name)
            return []

        for keyword in keywords:
            logger.info("Searching %s for keyword: %s", self.site_name, keyword)
            try:
                batch = self._search_projects_api(token, keyword)
                postings.extend(batch)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Search error on %s (keyword=%s): %s", self.site_name, keyword, exc)

        logger.info("Fetched %d postings from %s", len(postings), self.site_name)
        return postings

    def _get_access_token(self) -> Optional[str]:
        resp = self._get(ACCESS_TOKEN_URL)
        if resp is None:
            return None

        token: Optional[str] = None
        try:
            payload = resp.json()
            if isinstance(payload, str):
                token = payload
        except ValueError:
            token = resp.text.strip().strip('"')

        if token:
            return token.strip()
        return None

    def _search_projects_api(self, token: str, keyword: str) -> List[JobPosting]:
        payload = {
            "keywords": [{"skillName": keyword}],
            "projectsFilter": {
                "remotePreference": [],
                "city": [],
                "county": [],
                "country": [],
                "projectStart": [],
                "projectDuration": [],
                "lastUpdate": [],
                "includeExclude": [],
                "typeOfContract": [],
                "suggestedTerms": [],
                "profession": [],
                "lastChangedFilter": {"filterSectionId": None, "filterItemId": None},
            },
            "pagination": {"currentPage": 1, "pageSize": 25, "sortBy": "last_update", "asc": False},
            "category": "",
            "locale": "de-DE",
            "searchAgentId": None,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        resp = self._get(SEARCH_API_URL, headers=headers, json=payload)
        if resp is None:
            logger.warning("No API response from %s for keyword=%s", self.site_name, keyword)
            return []

        try:
            data = resp.json()
        except ValueError:
            logger.warning("Invalid JSON response from %s for keyword=%s", self.site_name, keyword)
            return []

        projects = data.get("projects", []) if isinstance(data, dict) else []
        results: List[JobPosting] = []
        for project in projects:
            posting = self._project_to_posting(project, keyword)
            if posting:
                results.append(posting)
        return results

    def _project_to_posting(self, project: Dict[str, Any], matched_keyword: str) -> Optional[JobPosting]:
        title = str(project.get("projectTitle") or "").strip()
        if not title:
            return None

        detail_url = str(project.get("linkToDetail") or "").strip()
        if not detail_url:
            project_id = str(project.get("id") or "").strip()
            if not project_id:
                return None
            detail_url = f"/projekte/{project_id}"

        url = detail_url if detail_url.startswith("http") else f"{BASE_URL}{detail_url}"

        company = project.get("companyName")
        company_str = str(company).strip() if company else None

        locations = project.get("locations") or []
        location = None
        if isinstance(locations, list) and locations:
            location = ", ".join(str(loc).strip() for loc in locations if str(loc).strip()) or None

        remote = project.get("remote")
        if remote and not location:
            location = str(remote).strip()

        description = None
        hint = project.get("hint")
        if isinstance(hint, list) and hint:
            description = ", ".join(str(part).strip() for part in hint if str(part).strip()) or None

        return JobPosting(
            title=title,
            company=company_str,
            location=location,
            url=url,
            posted_date=None,
            rate=None,
            source_site=self.site_name,
            description=description,
            matched_keywords=[matched_keyword],
        )

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
