---
title: "Weekly Digest: {{ week }}"
date: {{ date }}
paper_count: {{ papers | length }}
---

# Weekly Digest: {{ week }}

## Top Papers by Relevance
{% for paper in papers | sort(attribute='relevance_score', reverse=True) %}
### {{ paper.title }} ({{ "%.2f" | format(paper.relevance_score) }})
- **Category:** {{ paper.category }}
- **Source:** [Link]({{ paper.source_url }})
- {{ paper.summary | default('No summary available') | truncate(200) }}
{% endfor %}
