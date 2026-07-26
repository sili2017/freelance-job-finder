"""Deduplication of job postings."""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import List

from .models import JobPosting
from .storage import Storage

logger = logging.getLogger(__name__)

# Minimum fuzzy similarity ratio to consider two postings as duplicates
FUZZY_THRESHOLD = 0.85


def _fuzzy_similarity(a: str, b: str) -> float:
    """Return SequenceMatcher ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()


class Deduplicator:
    """
    Deduplicates a list of JobPostings:
    1. Primary: exact canonical URL match (via stable_hash in Storage).
    2. Secondary: fuzzy title+company similarity within the current batch.
    """

    def __init__(self, storage: Storage, fuzzy_threshold: float = FUZZY_THRESHOLD) -> None:
        self._storage = storage
        self._threshold = fuzzy_threshold

    def filter_new(self, postings: List[JobPosting]) -> List[JobPosting]:
        """
        Return only postings that have not been seen before.

        Marks newly returned postings as seen in storage.
        """
        # Step 1: filter by URL hash against persistent storage
        unseen = []
        for posting in postings:
            if self._storage.has_seen(posting.stable_hash):
                logger.debug("Duplicate (DB): %s", posting.url)
            else:
                unseen.append(posting)

        # Step 2: fuzzy dedup within the unseen batch (in-memory)
        deduplicated: List[JobPosting] = []
        seen_keys: List[str] = []

        for posting in unseen:
            key = posting.fuzzy_key
            is_dup = any(
                _fuzzy_similarity(key, existing) >= self._threshold
                for existing in seen_keys
            )
            if is_dup:
                logger.debug("Duplicate (fuzzy): %s", posting.title)
            else:
                deduplicated.append(posting)
                seen_keys.append(key)

        # Step 3: persist newly seen hashes
        entries = [
            {
                "hash": p.stable_hash,
                "url": p.url,
                "title": p.title,
                "source_site": p.source_site,
            }
            for p in deduplicated
        ]
        if entries:
            self._storage.mark_seen_bulk(entries)

        logger.info(
            "Deduplication: %d in → %d unseen (after DB) → %d new",
            len(postings),
            len(unseen),
            len(deduplicated),
        )
        return deduplicated
