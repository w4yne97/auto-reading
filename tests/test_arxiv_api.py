"""Tests for arXiv API client."""

import textwrap
from datetime import date

import pytest
import responses

from lib.sources.arxiv_api import search_arxiv, fetch_paper, parse_arxiv_xml


SAMPLE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2406.12345v1</id>
        <title>Test Paper: A New Approach</title>
        <summary>This paper presents a novel method for code generation.</summary>
        <published>2026-03-10T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <arxiv:primary_category term="cs.AI"/>
        <category term="cs.AI"/>
        <category term="cs.CL"/>
      </entry>
    </feed>
""")


class TestParseArxivXml:
    def test_parse_single_entry(self):
        papers = parse_arxiv_xml(SAMPLE_XML)
        assert len(papers) == 1
        p = papers[0]
        assert p.arxiv_id == "2406.12345"
        assert p.title == "Test Paper: A New Approach"
        assert p.authors == ["Alice Smith", "Bob Jones"]
        assert "novel method" in p.abstract
        assert p.published == date(2026, 3, 10)
        assert p.categories == ["cs.AI", "cs.CL"]
        assert p.source == "arxiv"

    def test_parse_empty_feed(self):
        xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        papers = parse_arxiv_xml(xml)
        assert papers == []

    def test_extract_arxiv_id_from_url(self):
        papers = parse_arxiv_xml(SAMPLE_XML)
        assert papers[0].arxiv_id == "2406.12345"


class TestSearchArxiv:
    @responses.activate
    def test_search_returns_papers(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        papers = search_arxiv(
            keywords=["code generation"],
            categories=["cs.AI"],
            max_results=10,
            days=30,
        )
        assert len(papers) == 1
        assert papers[0].arxiv_id == "2406.12345"

    @responses.activate
    def test_search_retries_on_503(self):
        responses.add(responses.GET, "https://export.arxiv.org/api/query", status=503)
        responses.add(responses.GET, "https://export.arxiv.org/api/query", body=SAMPLE_XML, status=200)
        papers = search_arxiv(keywords=["test"], categories=[], max_results=5, days=7)
        assert len(papers) == 1

    @responses.activate
    def test_search_fails_after_max_retries(self):
        for _ in range(3):
            responses.add(responses.GET, "https://export.arxiv.org/api/query", status=503)
        with pytest.raises(RuntimeError):
            search_arxiv(keywords=["test"], categories=[], max_results=5, days=7)


class TestFetchPaper:
    @responses.activate
    def test_fetch_single_paper(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        paper = fetch_paper("2406.12345")
        assert paper is not None
        assert paper.arxiv_id == "2406.12345"

    @responses.activate
    def test_fetch_nonexistent_paper(self):
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )
        paper = fetch_paper("9999.99999")
        assert paper is None
