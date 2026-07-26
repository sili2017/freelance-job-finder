"""Tests for ranker module."""

from __future__ import annotations

import pytest

from src.models import JobPosting
from src.ranker import DEFAULT_WEIGHTS, RuleBasedSummarizer, Ranker


def make_posting(
    title: str = "Developer",
    description: str = "",
    location: str = "",
    matched_keywords: list[str] | None = None,
    relevance_score: float = 0.0,
) -> JobPosting:
    return JobPosting(
        title=title,
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        source_site="example.com",
        description=description,
        location=location or None,
        matched_keywords=matched_keywords or [],
        relevance_score=relevance_score,
    )


class TestRuleBasedSummarizer:
    def test_no_keywords(self) -> None:
        summarizer = RuleBasedSummarizer()
        posting = make_posting()
        result = summarizer.summarize(posting)
        assert "No specific keyword match" in result

    def test_strong_match(self) -> None:
        summarizer = RuleBasedSummarizer()
        posting = make_posting(
            matched_keywords=["mulesoft", "anypoint"],
            relevance_score=20.0,
        )
        result = summarizer.summarize(posting)
        assert "Strong match" in result

    def test_good_match(self) -> None:
        summarizer = RuleBasedSummarizer()
        posting = make_posting(
            matched_keywords=["tibco"],
            relevance_score=10.0,
        )
        result = summarizer.summarize(posting)
        assert "Good match" in result

    def test_partial_match(self) -> None:
        summarizer = RuleBasedSummarizer()
        posting = make_posting(
            matched_keywords=["microservices"],
            relevance_score=3.0,
        )
        result = summarizer.summarize(posting)
        assert "Partial match" in result

    def test_location_included_in_summary(self) -> None:
        summarizer = RuleBasedSummarizer()
        posting = make_posting(
            matched_keywords=["mulesoft"],
            relevance_score=20.0,
            location="Berlin",
        )
        result = summarizer.summarize(posting)
        assert "Berlin" in result


class TestRanker:
    def test_empty_list(self) -> None:
        ranker = Ranker()
        assert ranker.rank([]) == []

    def test_mulesoft_scores_higher_than_microservices(self) -> None:
        ranker = Ranker()
        p_mule = make_posting(title="MuleSoft Developer", description="MuleSoft Anypoint")
        p_micro = make_posting(title="Microservices Developer", description="Microservices")
        ranked = ranker.rank([p_micro, p_mule])
        # MuleSoft should be first
        assert ranked[0].title == "MuleSoft Developer"

    def test_location_boost_applied(self) -> None:
        ranker = Ranker(location_boost=2.0)
        p_berlin = make_posting(
            title="MuleSoft Dev Berlin", description="MuleSoft", location="berlin"
        )
        p_unknown = make_posting(
            title="MuleSoft Dev Unknown", description="MuleSoft", location="SomeUnknownCity"
        )
        ranked = ranker.rank([p_unknown, p_berlin])
        assert ranked[0].location == "berlin"

    def test_postings_sorted_descending(self) -> None:
        ranker = Ranker()
        p1 = make_posting(title="MuleSoft Expert", description="MuleSoft Anypoint TIBCO BW")
        p2 = make_posting(title="Microservices Dev", description="Microservices only")
        ranked = ranker.rank([p2, p1])
        scores = [p.relevance_score for p in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_relevance_summary_set(self) -> None:
        ranker = Ranker()
        posting = make_posting(title="MuleSoft Developer", description="MuleSoft Anypoint")
        ranked = ranker.rank([posting])
        assert ranked[0].relevance_summary is not None

    def test_custom_weights(self) -> None:
        custom_weights = {"esb": 100.0}
        ranker = Ranker(weights=custom_weights)
        p_esb = make_posting(title="ESB Developer", description="ESB architecture")
        p_mule = make_posting(title="MuleSoft Dev", description="MuleSoft")
        ranked = ranker.rank([p_mule, p_esb])
        assert ranked[0].title == "ESB Developer"

    def test_tibco_amx_bpm_high_priority(self) -> None:
        ranker = Ranker()
        p_amx = make_posting(title="AMX BPM Developer", description="TIBCO AMX BPM")
        p_micro = make_posting(title="Microservices Dev", description="Microservices")
        ranked = ranker.rank([p_micro, p_amx])
        assert ranked[0].title == "AMX BPM Developer"
