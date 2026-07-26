"""Data models for the freelance job finder."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class JobPosting(BaseModel):
    """Represents a single freelance job posting."""

    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    url: str
    posted_date: Optional[date] = None
    rate: Optional[str] = None
    source_site: str
    description: Optional[str] = None
    matched_keywords: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    relevance_summary: Optional[str] = None

    @field_validator("title", "company", "location", "description", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def stable_hash(self) -> str:
        """Return a stable hash for deduplication (based on URL)."""
        return hashlib.sha256(self.url.encode("utf-8")).hexdigest()

    @property
    def fuzzy_key(self) -> str:
        """Return a key used for fuzzy deduplication (title + company)."""
        company = self.company or ""
        return f"{self.title.lower()}|{company.lower()}"

    def model_post_init(self, __context: object) -> None:  # noqa: ANN001
        """Ensure URL is stripped."""
        object.__setattr__(self, "url", self.url.strip())


class SearchConfig(BaseModel):
    """Configuration for a search run."""

    keywords: List[str]
    locations: List[str]
    enabled_sites: List[str]


class RunSummary(BaseModel):
    """Summary of a single run."""

    run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_fetched: int = 0
    total_new: int = 0
    sites_searched: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
