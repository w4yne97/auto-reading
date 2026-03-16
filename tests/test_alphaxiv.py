"""Tests for alphaXiv scraper."""

import json

import pytest
import responses

from lib.sources.alphaxiv import fetch_trending, parse_ssr_json, AlphaXivError


# Minimal SSR JSON fixture embedded in HTML
SAMPLE_SSR_DATA = {
    "pages": [{
        "papers": [
            {
                "universal_paper_id": "2603.12228",
                "title": "Neural Thickets",
                "paper_summary": {"abstract": "A test abstract about RL."},
                "authors": [{"name": "Alice"}, {"name": "Bob"}],
                "publication_date": "2026-03-12T17:49:30.000Z",
                "total_votes": 39,
                "visits_count": {"all": 1277},
                "topics": ["Computer Science", "cs.AI", "cs.LG"],
            },
            {
                "universal_paper_id": "2603.10165",
                "title": "OpenClaw-RL",
                "paper_summary": {"abstract": "Train any agent by talking."},
                "authors": [{"name": "Charlie"}],
                "publication_date": "2026-03-10T18:59:01.000Z",
                "total_votes": 122,
                "visits_count": {"all": 4151},
                "topics": ["Computer Science", "cs.AI"],
            },
        ],
    }],
}


def _make_html(ssr_data: dict) -> str:
    """Build a minimal HTML page with embedded SSR JSON."""
    json_str = json.dumps(ssr_data)
    return f'<html><script>self.$_TSR={json_str};</script></html>'


class TestParseSsrJson:
    def test_parse_valid_ssr(self):
        html = _make_html(SAMPLE_SSR_DATA)
        papers = parse_ssr_json(html)
        assert len(papers) == 2
        assert papers[0].arxiv_id == "2603.12228"
        assert papers[0].title == "Neural Thickets"
        assert papers[0].alphaxiv_votes == 39
        assert papers[0].alphaxiv_visits == 1277
        assert papers[0].source == "alphaxiv"

    def test_parse_no_ssr_raises(self):
        html = "<html><body>No data</body></html>"
        with pytest.raises(AlphaXivError):
            parse_ssr_json(html)

    def test_parse_empty_papers(self):
        data = {"pages": [{"papers": []}]}
        html = _make_html(data)
        papers = parse_ssr_json(html)
        assert papers == []


class TestFetchTrending:
    @responses.activate
    def test_fetch_returns_papers(self):
        html = _make_html(SAMPLE_SSR_DATA)
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=html,
            status=200,
        )
        papers = fetch_trending(max_pages=1)
        assert len(papers) == 2
        assert papers[0].arxiv_id == "2603.12228"
        assert papers[1].alphaxiv_votes == 122

    @responses.activate
    def test_fetch_raises_on_server_error(self):
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            status=500,
        )
        with pytest.raises(AlphaXivError):
            fetch_trending(max_pages=1)

    @responses.activate
    def test_fetch_raises_on_connection_error(self):
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=responses.ConnectionError("timeout"),
        )
        with pytest.raises(AlphaXivError):
            fetch_trending(max_pages=1)
