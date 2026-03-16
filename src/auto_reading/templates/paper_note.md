---
title: "{{ paper.title }}"
authors: [{{ paper.authors | join(', ') }}]
source: {{ paper.source }}
url: {{ paper.source_url }}
date: {{ paper.published_at.isoformat() }}
tags: [{{ paper.tags | join(', ') }}]
category: {{ paper.category }}
relevance: {{ paper.relevance_score }}
status: {{ paper.status }}
---

## Summary
{{ paper.summary or '(Not yet analyzed)' }}

## Key Insights
{% if paper.insights %}{% for insight in paper.insights %}- {{ insight }}
{% endfor %}{% else %}- (Not yet analyzed)
{% endif %}
## My Notes
(Add your notes here)
