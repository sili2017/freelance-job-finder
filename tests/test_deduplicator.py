"""Tests for deduplicator module."""

from __future__ import annotations

import pytest

from src.deduplicator import Deduplicator, _fuzzy_similarity
from src.models import JobPosting
from src.storage import Storage


def make_posting(url: str, title: str = "MuleSoft Developer", company: str = "Acme") -> JobPosting:
    return JobPosting(
        title=title,
        company=company,
        url=url,
        source_site="example.com",
    )


@pytest.fixture()
def in_memory_storage(tmp_path: object) -> Storage:
    """Create an in-memory SQLite storage for testing."""
    db_path = tmp_path / "test.db"  # type: ignore[operator]
    return Storage(db_path)


class TestFuzzySimilarity:
    def test_identical_strings(self) -> None:
        assert _fuzzy_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self) -> None:
        assert _fuzzy_similarity("abc", "xyz") < 0.5

    def test_similar_strings(self) -> None:
        ratio = _fuzzy_similarity("mulesoft developer", "mulesoft developer contract")
        assert ratio > 0.7


class TestDeduplicator:
    def test_filter_new_empty(self, in_memory_storage: Storage) -> None:
        dedup = Deduplicator(in_memory_storage)
        assert dedup.filter_new([]) == []

    def test_all_new_postings_returned(self, in_memory_storage: Storage) -> None:
        dedup = Deduplicator(in_memory_storage)
        postings = [
            make_posting("https://example.com/1", title="MuleSoft Developer", company="CompanyA"),
            make_posting("https://example.com/2", title="TIBCO Developer", company="CompanyB"),
        ]
        result = dedup.filter_new(postings)
        assert len(result) == 2

    def test_seen_postings_filtered(self, in_memory_storage: Storage) -> None:
        dedup = Deduplicator(in_memory_storage)
        posting = make_posting("https://example.com/1")

        # First call – should return it
        result1 = dedup.filter_new([posting])
        assert len(result1) == 1

        # Second call – should be filtered
        result2 = dedup.filter_new([posting])
        assert len(result2) == 0

    def test_fuzzy_dedup_within_batch(self, in_memory_storage: Storage) -> None:
        dedup = Deduplicator(in_memory_storage, fuzzy_threshold=0.85)
        # Nearly identical title+company → should deduplicate within batch
        p1 = make_posting("https://example.com/1", title="MuleSoft Developer", company="Acme")
        p2 = make_posting(
            "https://example.com/2",
            title="MuleSoft Developer",  # same title
            company="Acme",  # same company
        )
        result = dedup.filter_new([p1, p2])
        # Both have different URLs but identical fuzzy keys → only first kept
        assert len(result) == 1

    def test_different_urls_same_title_different_company_not_deduped(
        self, in_memory_storage: Storage
    ) -> None:
        dedup = Deduplicator(in_memory_storage, fuzzy_threshold=0.85)
        p1 = make_posting("https://example.com/1", title="MuleSoft Dev", company="CompanyA")
        p2 = make_posting("https://example.com/2", title="TIBCO Dev", company="CompanyB")
        result = dedup.filter_new([p1, p2])
        assert len(result) == 2

    def test_marks_postings_as_seen(self, in_memory_storage: Storage) -> None:
        dedup = Deduplicator(in_memory_storage)
        posting = make_posting("https://example.com/unique")
        dedup.filter_new([posting])

        # Verify it's now in storage
        assert in_memory_storage.has_seen(posting.stable_hash)
