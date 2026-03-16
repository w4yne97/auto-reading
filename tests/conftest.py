"""Shared test fixtures."""

import json
import textwrap
from pathlib import Path

import pytest
import yaml


SAMPLE_CONFIG = {
    "vault_path": "/tmp/test-vault",
    "language": "mixed",
    "research_domains": {
        "coding-agent": {
            "keywords": ["coding agent", "code generation", "code repair"],
            "arxiv_categories": ["cs.AI", "cs.SE", "cs.CL"],
            "priority": 5,
        },
        "rl-for-code": {
            "keywords": ["RLHF", "reinforcement learning", "reward model"],
            "arxiv_categories": ["cs.LG", "cs.AI"],
            "priority": 4,
        },
    },
    "excluded_keywords": ["survey", "3D"],
    "scoring_weights": {
        "keyword_match": 0.4,
        "recency": 0.2,
        "popularity": 0.3,
        "category_match": 0.1,
    },
}


SAMPLE_ARXIV_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2406.12345v1</id>
        <title>A Coding Agent for Code Generation</title>
        <summary>This paper presents a novel coding agent for code generation using reinforcement learning.</summary>
        <published>2026-03-10T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <arxiv:primary_category term="cs.AI"/>
        <category term="cs.AI"/>
        <category term="cs.CL"/>
      </entry>
      <entry>
        <id>http://arxiv.org/abs/2406.67890v1</id>
        <title>Reward Model Training with RLHF</title>
        <summary>We present a reward model trained with RLHF for code repair tasks.</summary>
        <published>2026-03-12T00:00:00Z</published>
        <author><name>Charlie Lee</name></author>
        <arxiv:primary_category term="cs.LG"/>
        <category term="cs.LG"/>
        <category term="cs.AI"/>
      </entry>
    </feed>
""")


SAMPLE_SSR_DATA = {
    "pages": [{
        "papers": [
            {
                "universal_paper_id": "2603.12228",
                "title": "Neural Code Agent",
                "paper_summary": {"abstract": "A coding agent with code generation capabilities."},
                "authors": [{"name": "Alice"}],
                "publication_date": "2026-03-12T17:49:30.000Z",
                "total_votes": 39,
                "visits_count": {"all": 1277},
                "topics": ["Computer Science", "cs.AI", "cs.LG"],
            },
        ],
    }],
}


def make_alphaxiv_html(ssr_data: dict) -> str:
    """Build a minimal HTML page with embedded SSR JSON."""
    json_str = json.dumps(ssr_data)
    return f"<html><script>self.$_TSR={json_str};</script></html>"


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    """Create a temporary config YAML file."""
    path = tmp_path / "research_interests.yaml"
    path.write_text(yaml.dump(SAMPLE_CONFIG, allow_unicode=True))
    return path


@pytest.fixture()
def vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault directory structure."""
    vault = tmp_path / "vault"
    (vault / "20_Papers" / "coding-agent").mkdir(parents=True)
    (vault / "10_Daily").mkdir(parents=True)
    (vault / "30_Insights").mkdir(parents=True)
    return vault


@pytest.fixture()
def output_path(tmp_path: Path) -> Path:
    """Create a temporary output path."""
    out = tmp_path / "output" / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out
