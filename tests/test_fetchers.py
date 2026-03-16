"""Tests for paper fetchers."""

import httpx
import pytest
import respx

from auto_reading.fetchers.base import BaseFetcher
from auto_reading.fetchers.alphaarxiv import AlphaRxivFetcher
from auto_reading.fetchers.github import GitHubFetcher

SAMPLE_ALPHAARXIV_HTML = """
<html>
<body>
<div class="paper-list">
  <div class="paper-card" data-arxiv-id="2406.12345">
    <h2 class="paper-title">
      <a href="https://arxiv.org/abs/2406.12345">CodeAgent: Autonomous Coding</a>
    </h2>
    <div class="paper-authors">Alice Smith, Bob Jones</div>
    <div class="paper-abstract">
      We present CodeAgent, a system for autonomous code generation using LLMs.
    </div>
    <div class="paper-date">2026-03-15</div>
  </div>
  <div class="paper-card" data-arxiv-id="2406.67890">
    <h2 class="paper-title">
      <a href="https://arxiv.org/abs/2406.67890">Unrelated Biology Paper</a>
    </h2>
    <div class="paper-authors">Carol White</div>
    <div class="paper-abstract">
      A study on protein folding mechanisms in extreme environments.
    </div>
    <div class="paper-date">2026-03-14</div>
  </div>
</div>
</body>
</html>
"""

SAMPLE_GITHUB_RELEASES_JSON = [
    {
        "tag_name": "v0.50.0",
        "name": "Aider v0.50.0",
        "body": "## What's new\n- Added multi-file editing\n- Improved context handling",
        "published_at": "2026-03-14T10:00:00Z",
        "html_url": "https://github.com/paul-gauthier/aider/releases/tag/v0.50.0",
    },
    {
        "tag_name": "v0.49.0",
        "name": "Aider v0.49.0",
        "body": "Bug fixes and improvements",
        "published_at": "2026-03-07T10:00:00Z",
        "html_url": "https://github.com/paul-gauthier/aider/releases/tag/v0.49.0",
    },
]


def test_base_fetcher_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseFetcher()


@pytest.mark.asyncio
@respx.mock
async def test_alphaarxiv_fetch_parses_papers():
    respx.get("https://alphaarxiv.org/").respond(
        200, html=SAMPLE_ALPHAARXIV_HTML
    )
    fetcher = AlphaRxivFetcher()
    papers = await fetcher.fetch(topics=["coding agent"], days=7)
    assert len(papers) >= 1
    paper = papers[0]
    assert paper.id == "arxiv:2406.12345"
    assert paper.source == "alphaarxiv"
    assert paper.source_url == "https://arxiv.org/abs/2406.12345"
    assert paper.summary is None
    assert paper.status == "unread"


@pytest.mark.asyncio
@respx.mock
async def test_alphaarxiv_fetch_handles_http_error():
    respx.get("https://alphaarxiv.org/").respond(500)
    fetcher = AlphaRxivFetcher()
    papers = await fetcher.fetch(topics=["coding agent"], days=7)
    assert papers == []


@pytest.mark.asyncio
@respx.mock
async def test_alphaarxiv_fetch_handles_malformed_html():
    respx.get("https://alphaarxiv.org/").respond(
        200, html="<html><body>No papers here</body></html>"
    )
    fetcher = AlphaRxivFetcher()
    papers = await fetcher.fetch(topics=["coding agent"], days=7)
    assert papers == []


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_releases():
    respx.get(
        "https://api.github.com/repos/paul-gauthier/aider/releases"
    ).respond(200, json=SAMPLE_GITHUB_RELEASES_JSON)
    fetcher = GitHubFetcher(tracked_repos=["paul-gauthier/aider"])
    papers = await fetcher.fetch(topics=["coding-agent"], days=7)
    assert len(papers) >= 1
    paper = papers[0]
    assert paper.id == "github:paul-gauthier/aider:v0.50.0"
    assert paper.source == "github"
    assert "aider" in paper.title.lower() or "Aider" in paper.title


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_releases_handles_error():
    respx.get(
        "https://api.github.com/repos/paul-gauthier/aider/releases"
    ).respond(404)
    fetcher = GitHubFetcher(tracked_repos=["paul-gauthier/aider"])
    papers = await fetcher.fetch(topics=["coding-agent"], days=7)
    assert papers == []


@pytest.mark.asyncio
@respx.mock
async def test_github_fetch_no_tracked_repos():
    fetcher = GitHubFetcher(tracked_repos=[])
    papers = await fetcher.fetch(topics=["coding-agent"], days=7)
    assert papers == []
