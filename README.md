# Auto-Reading

基于 [Claude Code](https://claude.ai/code) Skills 的论文追踪与 Insight 知识管理系统。

从 [alphaXiv](https://alphaxiv.org) 和 arXiv 自动获取论文，通过规则 + AI 混合评分筛选推荐，生成结构化笔记存入 Obsidian vault，并构建**主题 → 技术点**的持续演化知识体系。

## 特性

- **智能论文发现** — alphaXiv 社区热度优先，arXiv API 关键词补充
- **两阶段评分** — 规则评分（零成本筛 200+ 篇）→ Claude AI 精评估（Top 20）
- **Insight 知识图谱** — 跨论文追踪技术演进、方法对比、矛盾点
- **Obsidian 原生** — Markdown + frontmatter + wikilink，无数据库
- **对话式配置** — 通过 Claude Code 交互管理研究兴趣

## 前置要求

- [Claude Code](https://claude.ai/code)
- Python 3.12+
- [Obsidian](https://obsidian.md)（用于浏览生成的笔记）

## 安装

```bash
git clone https://github.com/w4yne97/auto-reading.git
cd auto-reading
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

## 快速开始

在项目目录下打开 Claude Code：

```bash
cd auto-reading
claude
```

### 1. 初始化配置

```
/reading-config
```

Claude 会引导你设置 vault 路径、研究领域、关键词和评分权重。

### 2. 获取今日论文推荐

```
/start-my-day
```

自动搜索 → 评分 → 生成每日推荐笔记到 `10_Daily/YYYY-MM-DD-论文推荐.md`。

### 3. 搜索特定主题

```
/paper-search reinforcement learning for code
```

### 4. 深度分析单篇论文

```
/paper-analyze 2406.12345
```

## 全部命令

| 命令 | 说明 |
|------|------|
| `/start-my-day [日期]` | 每日论文推荐（alphaXiv + arXiv → 评分 → Top 10） |
| `/paper-search <关键词>` | 按关键词搜索 arXiv 论文 |
| `/paper-analyze <论文ID>` | 单篇论文深度分析，生成笔记 |
| `/weekly-digest` | 过去 7 天的周报总结 |
| `/insight-init <主题>` | 创建 Insight 知识主题（如 "RL for Coding Agent"） |
| `/insight-update <主题>` | 将新论文知识融合到已有主题 |
| `/insight-absorb <主题/技术点> <来源>` | 从特定论文吸收知识到指定技术点 |
| `/insight-review <主题>` | 回顾主题的当前状态和开放问题 |
| `/insight-connect <主题A> [主题B]` | 发现跨主题关联 |
| `/reading-config` | 查看和修改研究兴趣配置 |

## Vault 结构

```
obsidian-vault/
├── 00_Config/
│   └── research_interests.yaml    # 研究兴趣配置
├── 10_Daily/
│   └── 2026-03-16-论文推荐.md     # 每日推荐
├── 20_Papers/
│   ├── coding-agent/              # 按研究领域分类
│   └── rl-for-code/
├── 30_Insights/
│   └── RL-for-Coding-Agent/       # Insight 主题
│       ├── _index.md              #   主题总览
│       ├── 算法选择-GRPO-GSPO.md   #   技术点
│       └── RL数据管道构建.md       #   技术点
└── 40_Digests/
    └── 2026-W11-weekly-digest.md  # 周报
```

## 架构

```
Claude Code
  │
  ▼
SKILL.md 编排层（.claude/skills/）
  │ 调用 Python 脚本
  ▼
入口脚本层（<skill>/scripts/*.py）
  │ import lib/
  ▼
共享 Python 库（lib/）
  ├── sources/alphaxiv.py   — alphaXiv 爬取
  ├── sources/arxiv_api.py  — arXiv API
  ├── scoring.py            — 规则评分引擎
  ├── vault.py              — Vault 读写
  └── models.py             — 数据模型
  │
  ▼
Obsidian Vault（Markdown 文件）
```

## 评分系统

**Phase 1 — 规则评分（零成本，全量论文）**

| 维度 | 权重 | 说明 |
|------|------|------|
| 关键词匹配 | 40% | 标题和摘要中的关键词命中 |
| 新近性 | 20% | 7天内满分，逐级递减 |
| 热度 | 30% | alphaXiv 投票数 + 访问量 |
| 类别匹配 | 10% | arXiv 分类命中 |

**Phase 2 — AI 评分（仅 Top 20）**

Claude 评估质量和深度相关性，最终分 = 规则分 × 0.6 + AI 分 × 0.4

## 配置示例

```yaml
vault_path: ~/obsidian-vault
language: "mixed"  # English titles, 中文分析

research_domains:
  "coding-agent":
    keywords: ["coding agent", "code generation", "code repair"]
    arxiv_categories: ["cs.AI", "cs.SE", "cs.CL"]
    priority: 5

excluded_keywords: ["survey", "review", "3D", "medical"]

scoring_weights:
  keyword_match: 0.4
  recency: 0.2
  popularity: 0.3
  category_match: 0.1
```

## 开发

```bash
# 运行测试
pytest

# 带覆盖率
pytest --cov=lib --cov-report=term-missing

# 单个测试文件
pytest tests/test_scoring.py -v
```

## License

MIT
