"""Tests for data models."""

from __future__ import annotations

from datetime import date

import pytest

from src.models import JobPosting, RunSummary


class TestJobPosting:
    def test_minimal_posting(self) -> None:
        posting = JobPosting(
            title="MuleSoft Developer",
            url="https://example.com/job/1",
            source_site="example.com",
        )
        assert posting.title == "MuleSoft Developer"
        assert posting.url == "https://example.com/job/1"
        assert posting.source_site == "example.com"
        assert posting.matched_keywords == []
        assert posting.relevance_score == 0.0

    def test_title_stripped(self) -> None:
        posting = JobPosting(
            title="  TIBCO Developer  ",
            url="https://example.com/job/2",
            source_site="example.com",
        )
        assert posting.title == "TIBCO Developer"

    def test_url_stripped(self) -> None:
        posting = JobPosting(
            title="Job",
            url="  https://example.com/job/3  ",
            source_site="example.com",
        )
        assert posting.url == "https://example.com/job/3"

    def test_stable_hash_is_url_based(self) -> None:
        p1 = JobPosting(
            title="Job A",
            url="https://example.com/job/1",
            source_site="example.com",
        )
        p2 = JobPosting(
            title="Job B",  # Different title, same URL
            url="https://example.com/job/1",
            source_site="example.com",
        )
        assert p1.stable_hash == p2.stable_hash

    def test_stable_hash_differs_for_different_urls(self) -> None:
        p1 = JobPosting(
            title="Job",
            url="https://example.com/job/1",
            source_site="example.com",
        )
        p2 = JobPosting(
            title="Job",
            url="https://example.com/job/2",
            source_site="example.com",
        )
        assert p1.stable_hash != p2.stable_hash

    def test_fuzzy_key(self) -> None:
        posting = JobPosting(
            title="MuleSoft Architect",
            company="Acme Corp",
            url="https://example.com/job/1",
            source_site="example.com",
        )
        assert posting.fuzzy_key == "mulesoft architect|acme corp"

    def test_fuzzy_key_no_company(self) -> None:
        posting = JobPosting(
            title="TIBCO Developer",
            url="https://example.com/job/1",
            source_site="example.com",
        )
        assert posting.fuzzy_key == "tibco developer|"

    def test_full_posting(self) -> None:
        posting = JobPosting(
            title="Integration Architect",
            company="TechCo",
            location="Berlin",
            url="https://example.com/job/5",
            posted_date=date(2025, 7, 25),
            rate="800 EUR/day",
            source_site="freelancermap.de",
            description="MuleSoft integration project",
            matched_keywords=["MuleSoft", "Integration Architect"],
            relevance_score=18.5,
            relevance_summary="Strong match: MuleSoft, Integration Architect; Berlin",
        )
        assert posting.location == "Berlin"
        assert posting.posted_date == date(2025, 7, 25)
        assert len(posting.matched_keywords) == 2


class TestRunSummary:
    def test_defaults(self) -> None:
        summary = RunSummary()
        assert summary.total_fetched == 0
        assert summary.total_new == 0
        assert summary.sites_searched == []
        assert summary.errors == []
