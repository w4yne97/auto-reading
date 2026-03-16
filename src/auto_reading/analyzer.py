"""Claude-based paper analysis: summarization, classification, scoring."""

import json
import logging
import time
from dataclasses import dataclass, replace

from auto_reading.models import Paper

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_DELAYS = [1, 4, 16]  # seconds

SYSTEM_PROMPT = """You are a research paper analyst specializing in AI/ML.
Given a paper's title and abstract, produce a JSON analysis."""

USER_PROMPT_TEMPLATE = """## Paper
Title: {title}
Abstract: {abstract}

## Available Categories
{categories}

## Instructions
Analyze this paper and return JSON (no markdown fences, just raw JSON):
{{
  "summary": "2-3 paragraph summary of key contributions and methods",
  "category": "one of the available categories, or 'other'",
  "tags": ["3-5 descriptive tags, reuse existing tags when applicable"],
  "relevance_score": 0.0-1.0,
  "insights": ["2-3 key takeaways or novel ideas"]
}}

Relevance scoring guide:
- 0.8-1.0: Directly about coding agents, code generation with LLMs
- 0.5-0.8: Related (general LLM agents, tool use, code understanding)
- 0.2-0.5: Tangentially related (general NLP, ML infrastructure)
- 0.0-0.2: Minimal relevance to coding agents"""


@dataclass(frozen=True)
class AnalysisResult:
    """Result of Claude's paper analysis."""

    summary: str
    category: str
    tags: list[str]
    relevance_score: float
    insights: list[str]

    def apply_to(self, paper: Paper) -> Paper:
        """Create a new Paper with analysis results applied."""
        return replace(
            paper,
            summary=self.summary,
            category=self.category,
            tags=self.tags,
            relevance_score=self.relevance_score,
            insights=self.insights,
        )


class Analyzer:
    """Analyzes papers using the Claude API."""

    def __init__(self, client, model: str, categories: list[str]):
        self._client = client
        self._model = model
        self._categories = categories

    def analyze(self, paper: Paper) -> AnalysisResult:
        """Analyze a single paper with retry on transient errors.

        Retries up to 3 times with exponential backoff (1s, 4s, 16s).
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=paper.title,
            abstract=paper.abstract,
            categories="\n".join(f"- {c}" for c in self._categories),
        )

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                message = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                response_text = message.content[0].text
                return self._parse_response(response_text)
            except ValueError:
                raise  # JSON parse errors are not transient, don't retry
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = BACKOFF_DELAYS[attempt]
                    logger.warning(
                        "Claude API error (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        delay,
                        e,
                    )
                    time.sleep(delay)

        raise last_error  # type: ignore[misc]

    def _parse_response(self, response_text: str) -> AnalysisResult:
        """Parse Claude's JSON response into an AnalysisResult."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse Claude response as JSON: {e}\n"
                f"Response: {response_text[:500]}"
            )

        return AnalysisResult(
            summary=data["summary"],
            category=data.get("category", "other"),
            tags=data.get("tags", []),
            relevance_score=float(data.get("relevance_score", 0.0)),
            insights=data.get("insights", []),
        )
