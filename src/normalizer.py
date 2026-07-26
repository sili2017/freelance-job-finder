"""Normalizes job posting fields to consistent formats."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional

from .models import JobPosting

logger = logging.getLogger(__name__)

# German city/location name mappings → normalised English/canonical name
LOCATION_NORMALISATION: dict[str, str] = {
    "münchen": "Munich",
    "muenchen": "Munich",
    "köln": "Cologne",
    "koeln": "Cologne",
    "frankfurt am main": "Frankfurt",
    "düsseldorf": "Düsseldorf",
    "duesseldorf": "Düsseldorf",
    "berlin": "Berlin",
    "hamburg": "Hamburg",
    "stuttgart": "Stuttgart",
    "hannover": "Hannover",
    "remote": "Remote",
    "hybrid": "Hybrid",
    "deutschland": "Germany",
    "germany": "Germany",
    "bundesweit": "Germany",
}

# Patterns for date parsing
DATE_PATTERNS = [
    "%d.%m.%Y",   # 25.07.2025
    "%d.%m.%y",   # 25.07.25
    "%Y-%m-%d",   # 2025-07-25
    "%d/%m/%Y",   # 25/07/2025
    "%B %d, %Y",  # July 25, 2025
    "%d %B %Y",   # 25 July 2025
    "%d. %B %Y",  # 25. Juli 2025 (German)
]

GERMAN_MONTHS = {
    "januar": "January",
    "februar": "February",
    "märz": "March",
    "maerz": "March",
    "april": "April",
    "mai": "May",
    "juni": "June",
    "juli": "July",
    "august": "August",
    "september": "September",
    "oktober": "October",
    "november": "November",
    "dezember": "December",
}


def _strip_html(text: Optional[str]) -> Optional[str]:
    """Remove HTML tags and normalise whitespace."""
    if text is None:
        return None
    if not text:
        return None
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or None


def _translate_german_months(text: str) -> str:
    """Replace German month names with English equivalents."""
    lower = text.lower()
    for german, english in GERMAN_MONTHS.items():
        lower = lower.replace(german, english)
    return lower


def normalize_date(raw: Optional[str]) -> Optional[date]:
    """Parse a raw date string into a Python date object."""
    if not raw:
        return None
    raw = raw.strip()
    translated = _translate_german_months(raw)
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(translated, pattern).date()
        except ValueError:
            pass
    logger.debug("Could not parse date string: %r", raw)
    return None


def normalize_location(raw: Optional[str]) -> Optional[str]:
    """Normalise a location string using the mapping table."""
    if not raw:
        return raw
    cleaned = raw.strip()
    lower = cleaned.lower()
    # Check exact match first
    if lower in LOCATION_NORMALISATION:
        return LOCATION_NORMALISATION[lower]
    # Check if any key is a substring
    for key, value in LOCATION_NORMALISATION.items():
        if key in lower:
            return value
    return cleaned


def normalize_posting(posting: JobPosting) -> JobPosting:
    """Return a new JobPosting with normalized fields."""
    normalized_location = normalize_location(posting.location)
    normalized_description = _strip_html(posting.description)
    return posting.model_copy(
        update={
            "location": normalized_location,
            "description": normalized_description,
        }
    )


def normalize_postings(postings: list[JobPosting]) -> list[JobPosting]:
    """Normalize a list of job postings."""
    result = []
    for posting in postings:
        try:
            result.append(normalize_posting(posting))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to normalize posting %r: %s", posting.url, exc)
            result.append(posting)
    return result
