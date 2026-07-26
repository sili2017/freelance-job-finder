"""Ranking and relevance summarization for job postings."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .models import JobPosting

logger = logging.getLogger(__name__)

# Default keyword weights — higher means more relevant
DEFAULT_WEIGHTS: Dict[str, float] = {
    # Core MuleSoft terms
    "mulesoft": 10.0,
    "anypoint": 9.0,
    # Core TIBCO terms
    "tibco amx bpm": 10.0,
    "amx bpm": 10.0,
    "tibco bwce": 9.0,
    "tibco bw": 8.0,
    "businessworks": 8.0,
    "tibco ems": 7.0,
    "business events": 7.0,
    "tibco": 6.0,
    # Integration roles
    "integration architect": 8.0,
    "integration developer": 7.0,
    "api developer": 6.0,
    "esb": 5.0,
    # Generic terms (lower weight)
    "microservices": 3.0,
}

# Locations that get a boost
BOOSTED_LOCATIONS = {
    "berlin",
    "frankfurt",
    "munich",
    "hamburg",
    "stuttgart",
    "düsseldorf",
    "cologne",
    "remote",
    "germany",
}


class Summarizer(ABC):
    """Abstract interface for generating a human-readable relevance summary."""

    @abstractmethod
    def summarize(self, posting: JobPosting) -> str:
        """Return a relevance summary string for the given posting."""


class RuleBasedSummarizer(Summarizer):
    """Default rule-based summarizer (no external API required)."""

    def summarize(self, posting: JobPosting) -> str:
        if not posting.matched_keywords:
            return "No specific keyword match"

        score = posting.relevance_score
        if score >= 15:
            strength = "Strong match"
        elif score >= 8:
            strength = "Good match"
        else:
            strength = "Partial match"

        kw_str = ", ".join(posting.matched_keywords[:5])
        parts = [f"{strength}: {kw_str}"]
        if posting.location:
            parts.append(posting.location)
        return "; ".join(parts)


class Ranker:
    """Scores and ranks JobPostings by relevance."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        location_boost: float = 1.5,
        summarizer: Optional[Summarizer] = None,
    ) -> None:
        self._weights = weights or DEFAULT_WEIGHTS
        self._location_boost = location_boost
        self._summarizer: Summarizer = summarizer or RuleBasedSummarizer()

    def _score(self, posting: JobPosting) -> float:
        """Compute numeric relevance score for a posting."""
        score = 0.0
        matched: List[str] = []
        text = " ".join(
            filter(None, [posting.title, posting.description])
        ).lower()

        for keyword, weight in self._weights.items():
            if keyword.lower() in text:
                score += weight
                matched.append(keyword)

        # Also credit already-matched keywords stored on the posting
        for kw in posting.matched_keywords:
            kw_lower = kw.lower()
            if kw_lower not in [m.lower() for m in matched]:
                score += self._weights.get(kw_lower, 2.0)
                matched.append(kw)

        # Location boost
        if posting.location and posting.location.lower() in BOOSTED_LOCATIONS:
            score *= self._location_boost

        # Store matched keywords back
        object.__setattr__(posting, "matched_keywords", list(dict.fromkeys(matched)))
        return score

    def rank(self, postings: List[JobPosting]) -> List[JobPosting]:
        """Score, summarize, and sort postings descending by relevance_score."""
        scored: List[JobPosting] = []
        for posting in postings:
            score = self._score(posting)
            updated = posting.model_copy(
                update={"relevance_score": score}
            )
            # Set matched keywords from what _score found
            updated = updated.model_copy(
                update={"matched_keywords": posting.matched_keywords}
            )
            summary = self._summarizer.summarize(updated)
            updated = updated.model_copy(update={"relevance_summary": summary})
            scored.append(updated)

        scored.sort(key=lambda p: p.relevance_score, reverse=True)
        logger.info("Ranked %d postings", len(scored))
        return scored
