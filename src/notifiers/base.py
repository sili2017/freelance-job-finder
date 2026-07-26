"""Base notifier interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import JobPosting


class BaseNotifier(ABC):
    """Abstract base class for all notification channels."""

    @abstractmethod
    def send(self, postings: List[JobPosting]) -> None:
        """Send a digest of job postings via this notification channel."""
