"""GitHub fetcher for releases from tracked repositories."""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from auto_reading.fetchers.base import BaseFetcher
from auto_reading.models import Paper

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubFetcher(BaseFetcher):
    """Fetches release notes from tracked GitHub repositories.

    Source-specific config (tracked repos, auth) is passed via constructor,
    keeping the fetch() signature consistent with BaseFetcher.
    """

    def __init__(
        self, tracked_repos: list[str], token: str | None = None
    ):
        self._tracked_repos = tracked_repos
        self._headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    async def fetch(self, topics: list[str], days: int) -> list[Paper]:
        if not self._tracked_repos:
            return []
        return await self._fetch_releases(days)

    async def _fetch_releases(self, days: int) -> list[Paper]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        papers: list[Paper] = []

        async with httpx.AsyncClient(headers=self._headers) as client:
            for repo in self._tracked_repos:
                try:
                    repo_papers = await self._fetch_repo_releases(
                        client, repo, cutoff
                    )
                    papers.extend(repo_papers)
                except Exception as e:
                    logger.warning(
                        "Failed to fetch releases for %s: %s", repo, e
                    )
                    continue

        return papers

    async def _fetch_repo_releases(
        self, client: httpx.AsyncClient, repo: str, cutoff: datetime
    ) -> list[Paper]:
        url = f"{GITHUB_API}/repos/{repo}/releases"
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("GitHub API error for %s: %s", repo, e)
            return []

        releases = response.json()
        papers: list[Paper] = []

        for release in releases:
            published_str = release.get("published_at", "")
            if not published_str:
                continue

            published_dt = datetime.fromisoformat(
                published_str.replace("Z", "+00:00")
            )
            if published_dt < cutoff:
                continue

            tag = release.get("tag_name", "unknown")
            title = release.get("name") or f"{repo} {tag}"
            body = release.get("body", "") or ""
            html_url = release.get(
                "html_url", f"https://github.com/{repo}"
            )

            owner = repo.split("/")[0] if "/" in repo else repo

            paper = Paper(
                id=f"github:{repo}:{tag}",
                title=title,
                authors=[owner],
                abstract=body[:2000],
                source="github",
                source_url=html_url,
                published_at=published_dt.date(),
                fetched_at=datetime.now(),
                tags=[],
                category="other",
                status="unread",
                summary=None,
                insights=[],
                relevance_score=0.0,
            )
            papers.append(paper)

        return papers
