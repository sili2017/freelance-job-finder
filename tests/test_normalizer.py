"""Tests for normalizer module."""

from __future__ import annotations

from datetime import date

import pytest

from src.models import JobPosting
from src.normalizer import (
    normalize_date,
    normalize_location,
    normalize_posting,
    normalize_postings,
    _strip_html,
)


class TestStripHtml:
    def test_removes_html_tags(self) -> None:
        assert _strip_html("<b>Hello</b> <i>World</i>") == "Hello World"

    def test_collapses_whitespace(self) -> None:
        assert _strip_html("  foo   bar  ") == "foo bar"

    def test_none_returns_none(self) -> None:
        assert _strip_html(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert _strip_html("") is None

    def test_complex_html(self) -> None:
        html = "<div class='job'><p>We need a <strong>MuleSoft</strong> expert.</p></div>"
        result = _strip_html(html)
        assert result == "We need a MuleSoft expert."


class TestNormalizeDate:
    def test_german_dot_format(self) -> None:
        assert normalize_date("25.07.2025") == date(2025, 7, 25)

    def test_iso_format(self) -> None:
        assert normalize_date("2025-07-25") == date(2025, 7, 25)

    def test_german_month_name(self) -> None:
        result = normalize_date("25. Juli 2025")
        assert result == date(2025, 7, 25)

    def test_invalid_returns_none(self) -> None:
        assert normalize_date("not-a-date") is None

    def test_none_returns_none(self) -> None:
        assert normalize_date(None) is None

    def test_empty_returns_none(self) -> None:
        assert normalize_date("") is None

    def test_slash_format(self) -> None:
        assert normalize_date("25/07/2025") == date(2025, 7, 25)


class TestNormalizeLocation:
    def test_muenchen_to_munich(self) -> None:
        assert normalize_location("München") == "Munich"

    def test_koeln_to_cologne(self) -> None:
        assert normalize_location("Köln") == "Cologne"

    def test_remote_stays_remote(self) -> None:
        assert normalize_location("Remote") == "Remote"

    def test_germany_normalised(self) -> None:
        assert normalize_location("Deutschland") == "Germany"

    def test_berlin_stays_berlin(self) -> None:
        assert normalize_location("Berlin") == "Berlin"

    def test_none_returns_none(self) -> None:
        assert normalize_location(None) is None

    def test_unknown_location_passes_through(self) -> None:
        result = normalize_location("SomeUnknownCity")
        assert result == "SomeUnknownCity"

    def test_case_insensitive(self) -> None:
        assert normalize_location("münchen") == "Munich"
        assert normalize_location("MÜNCHEN") == "Munich"

    def test_substring_match(self) -> None:
        # "Frankfurt am Main" should normalize to Frankfurt
        result = normalize_location("Frankfurt am Main")
        assert result == "Frankfurt"


class TestNormalizePosting:
    def _make_posting(self, **kwargs: object) -> JobPosting:
        defaults = {
            "title": "Test Job",
            "url": "https://example.com/job/1",
            "source_site": "example.com",
        }
        defaults.update(kwargs)
        return JobPosting(**defaults)  # type: ignore[arg-type]

    def test_normalizes_location(self) -> None:
        posting = self._make_posting(location="München")
        result = normalize_posting(posting)
        assert result.location == "Munich"

    def test_strips_html_from_description(self) -> None:
        posting = self._make_posting(description="<b>Great</b> <i>opportunity</i>")
        result = normalize_posting(posting)
        assert result.description == "Great opportunity"

    def test_url_unchanged(self) -> None:
        url = "https://example.com/job/42"
        posting = self._make_posting(url=url)
        result = normalize_posting(posting)
        assert result.url == url


class TestNormalizePostings:
    def test_empty_list(self) -> None:
        assert normalize_postings([]) == []

    def test_multiple_postings(self) -> None:
        postings = [
            JobPosting(
                title="Job A",
                url="https://example.com/1",
                source_site="x",
                location="Köln",
            ),
            JobPosting(
                title="Job B",
                url="https://example.com/2",
                source_site="x",
                location="München",
            ),
        ]
        results = normalize_postings(postings)
        assert results[0].location == "Cologne"
        assert results[1].location == "Munich"
