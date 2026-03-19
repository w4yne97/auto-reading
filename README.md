# Auto-Reading

[English](./README_EN.md) | **中文**

基于 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skills 的论文追踪、Insight 知识管理与研究创意系统。

从 [alphaXiv](https://alphaxiv.org) 和 arXiv 自动获取论文，通过规则 + AI 混合评分筛选推荐，生成结构化笔记存入 Obsidian vault，构建**主题 → 技术点**的持续演化知识体系，并从中挖掘研究 Idea。

## 工作方式

所有交互通过 Claude Code 斜杠命令完成，没有独立的 CLI。Claude 读取 SKILL.md 文件并在后台编排 Python 脚本。

```
你 ──► /start-my-day  ──► Claude 抓取 & 评分论文 ──► 每日推荐笔记
你 ──► /paper-import  ──► Claude 解析 & 导入论文 ──► 论文笔记 + Insight 关联
你 ──► /insight-init  ──► Claude 构建知识主题  ──► 持续演化的知识图谱
你 ──► /idea-generate ──► Claude 分析 gap & 交叉 ──► 研究 Idea 笔记
```

## 前置要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Python 3.12+
- [Obsidian](https://obsidian.md) 桌面端（需保持运行）
- [Obsidian CLI](https://obsidian.md/cli)（在 Settings → General 中启用并注册到 PATH）

## 安装

```bash
git clone https://github.com/w4yne97/auto-reading.git
cd auto-reading
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

### 配置 Obsidian CLI

1. 更新 Obsidian 到最新版本
2. Settings → General → 启用 "Command line interface"
3. 按提示注册 CLI 到系统 PATH
4. 重启终端，验证：`obsidian --version`

## 快速开始

```bash
cd auto-reading && claude
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

### 3. 导入已有论文

```
/paper-import 2406.12345 "https://arxiv.org/abs/1706.03762" "Attention Is All You Need" /path/to/paper.pdf
```

批量导入已读过的论文。支持 arxiv ID、URL、论文名称、本地 PDF。导入后可选择关联到 Insight 主题。

### 4. 构建知识体系

```
/insight-init RL for Coding Agent
```

创建知识主题，后续通过 `/insight-update`、`/insight-absorb`、`/insight-connect` 持续演化。

## 全部命令

### 论文发现

| 命令 | 说明 |
|------|------|
| `/start-my-day [日期]` | 每日推荐（alphaXiv + arXiv → 评分 → Top 10） |
| `/paper-search <关键词>` | 按关键词搜索 arXiv 论文 |
| `/paper-analyze <论文ID>` | 单篇论文深度分析，生成笔记 |
| `/paper-import <输入...>` | 批量导入已有论文（ID、URL、标题、PDF） |
| `/weekly-digest` | 过去 7 天的周报总结 |

### Insight 知识图谱

| 命令 | 说明 |
|------|------|
| `/insight-init <主题>` | 创建知识主题及技术点 |
| `/insight-update <主题>` | 将新论文知识融合到已有主题 |
| `/insight-absorb <主题/技术点> <来源>` | 从论文深度吸收知识到指定技术点 |
| `/insight-review <主题>` | 回顾主题现状和开放问题 |
| `/insight-connect <主题A> [主题B]` | 发现跨主题关联 |

### 研究 Idea

| 命令 | 说明 |
|------|------|
| `/idea-generate` | 从 Insight 知识库挖掘研究机会（gap + 跨领域组合） |
| `/idea-generate --from-spark "描述"` | 基于日常发现的线索深入探索 |
| `/idea-develop <idea名>` | 推进 Idea（spark→exploring→validated） |
| `/idea-review` | 全局看板：排序、停滞预警、操作建议 |
| `/idea-review <idea名>` | 单个 Idea 深度评审：新颖性、可行性、完整度 |

> `/start-my-day` 和 `/insight-update` 会自动进行轻量 Idea Spark 检查——如果新论文恰好能解决某个已知开放问题，会在笔记末尾提示。

### 配置

| 命令 | 说明 |
|------|------|
| `/reading-config` | 查看和修改研究兴趣配置 |

## Vault 结构

```
obsidian-vault/
├── 00_Config/
│   └── research_interests.yaml     # 研究领域、关键词、权重
├── 10_Daily/
│   └── 2026-03-17-论文推荐.md      # 每日推荐
├── 20_Papers/
│   ├── coding-agent/               # 按研究领域分类
│   │   └── Paper-Title.md
│   └── rl-for-code/
├── 30_Insights/
│   └── RL-for-Coding-Agent/        # Insight 知识主题
│       ├── _index.md               #   主题总览 + 技术点列表
│       ├── 算法选择-GRPO-GSPO.md    #   技术点：方法对比
│       └── 奖励模型设计.md          #   技术点：奖励设计
├── 40_Ideas/
│   ├── _dashboard.md               # Idea 全局看板
│   ├── gap-reward-long-horizon.md   # Gap 类 Idea
│   └── cross-grpo-tool-use.md      # 跨领域组合类 Idea
└── 40_Digests/
    └── 2026-W12-weekly-digest.md   # 周报
```

## 评分系统

两阶段评分，在最小化 API 成本的同时最大化相关性。

**Phase 1 — 规则评分（零成本，全量论文）**

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| 关键词匹配 | 40% | 标题 (1.5x) + 摘要 (0.8x) 关键词命中 |
| 新近性 | 20% | 7天=10, 30天=7, 90天=4, 更早=1 |
| 热度 | 30% | alphaXiv 投票数 + 访问量 |
| 类别匹配 | 10% | arXiv 分类命中=10, 未命中=0 |

**Phase 2 — AI 评分（仅 Top 20）**

Claude 在对话中评估论文质量和深度相关性。最终分 = 规则分 x 0.6 + AI 分 x 0.4。

## 架构

```
Claude Code（用户交互）
  │
  ▼
SKILL.md 编排层（.claude/skills/）
  │ 调用 Python 脚本
  ▼
入口脚本层（<skill>/scripts/*.py）
  │ import lib/
  ▼
共享 Python 库（lib/）
  ├── obsidian_cli.py         — Obsidian CLI 封装（subprocess → 类型化 API）
  ├── vault.py                — Vault 业务逻辑（扫描、去重、写入、搜索）
  ├── sources/alphaxiv.py     — alphaXiv 热门论文提取
  ├── sources/arxiv_api.py    — arXiv API 搜索 + 批量获取
  ├── resolver.py             — 输入解析（ID/URL/标题/PDF）
  ├── scoring.py              — 规则评分引擎
  └── models.py               — Paper, ScoredPaper（冻结数据类）
  │
  ▼
Obsidian CLI ──► Obsidian Vault（Markdown + YAML frontmatter）
```

SKILL.md 是自然语言工作流定义，Claude 逐步执行。Python 负责数据获取、评分和 Vault I/O（通过 Obsidian CLI）。Claude 负责 AI 分析、笔记生成和用户交互。

### Obsidian CLI 集成

所有 Vault 操作通过 [Obsidian CLI](https://obsidian.md/cli) 完成，利用 Obsidian 的内存索引实现高效搜索、属性读写和链接图查询。

```
lib/vault.py  →  lib/obsidian_cli.py  →  Obsidian CLI  →  Vault
（业务逻辑）      （subprocess 封装）      （索引搜索）      （文件系统）
```

核心能力：
- **索引搜索** — `search`、`search_context` 利用 Obsidian 全文索引
- **属性原子操作** — `get_property`、`set_property` 读写单个 frontmatter 字段
- **链接图** — `backlinks`、`outgoing_links`、`unresolved_links` 查询双向链接
- **笔记管理** — `create_note`、`read_note`、`delete_note` 管理 vault 文件

## 配置示例

```yaml
language: "mixed"  # 论文标题/摘要英文，分析中文

research_domains:
  "coding-agent":
    keywords: ["coding agent", "code generation", "code repair"]
    arxiv_categories: ["cs.AI", "cs.SE", "cs.CL"]
    priority: 5
  "rl-for-code":
    keywords: ["RLHF", "reinforcement learning", "reward model"]
    arxiv_categories: ["cs.LG", "cs.AI"]
    priority: 4

excluded_keywords: ["survey", "review", "3D", "medical"]

scoring_weights:
  keyword_match: 0.4
  recency: 0.2
  popularity: 0.3
  category_match: 0.1
```

## 开发

```bash
# 运行全部单元测试（170+ 测试，约 0.5s）
pytest

# 带覆盖率（目标 80%，当前 96%）
pytest --cov=lib --cov-report=term-missing

# 运行集成测试（需要 Obsidian 运行中）
pytest -m integration -v

# 单个模块
pytest tests/test_resolver.py -v
```

## License

MIT
