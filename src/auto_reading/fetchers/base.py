"""Abstract base class for paper fetchers."""

from abc import ABC, abstractmethod

from auto_reading.models import Paper


class BaseFetcher(ABC):
    """Base class for all paper source fetchers.

    Source-specific configuration (e.g., tracked repos, auth tokens)
    should be passed via the constructor, so that fetch() has a
    uniform signature across all fetchers.
    """

    @abstractmethod
    async def fetch(self, topics: list[str], days: int) -> list[Paper]:
        """Fetch papers matching topics from the last N days.

        Args:
            topics: List of topic keywords to search for.
            days: Number of days to look back.

        Returns:
            List of Paper objects (unanalyzed — summary/insights/score empty).
        """
        ...
