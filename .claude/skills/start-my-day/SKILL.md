---
name: start-my-day
description: 每日论文推荐 — 从 alphaXiv/arXiv 获取论文，两阶段评分，生成每日推荐笔记
---

你是一个 AI 研究助手，帮助用户每天高效地发现和筛选与研究兴趣相关的论文。

# Goal

从 alphaXiv 热门论文和 arXiv 搜索中获取候选论文，经过规则评分 + AI 评分两阶段筛选，生成每日论文推荐笔记到 Obsidian vault。

# Workflow

## Step 1: 读取配置

1. 读取用户 vault 中的配置文件 `$VAULT_PATH/00_Config/research_interests.yaml`
   - 如果环境变量 `VAULT_PATH` 未设置，先读取项目中已知配置文件查找 `vault_path` 字段
   - 如果配置文件不存在，提示用户运行 `/config` 初始化
2. 从配置中提取：
   - `vault_path` — vault 根目录
   - `research_domains` — 研究领域及关键词
   - `scoring_weights` — 评分权重
   - `excluded_keywords` — 排除关键词
   - `language` — 语言设置（默认 "mixed"）

## Step 2: 调用 search_and_filter.py

确定目标日期：
- 如果用户提供了日期参数（如 `/start-my-day 2026-03-15`），使用该日期
- 否则使用今天的日期

运行脚本：

```bash
python start-my-day/scripts/search_and_filter.py \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --output /tmp/auto-reading/result.json \
  --top-n 20
```

检查退出码：
- 0 = 成功，继续下一步
- 非 0 = 失败，向用户展示 stderr 中的错误消息并建议操作

## Step 3: 读取 JSON 输出

读取 `/tmp/auto-reading/result.json`，包含：
- `total_fetched` — 总获取数
- `total_after_dedup` — 去重后数量
- `total_after_filter` — 排除后数量
- `top_n` — 返回的论文数
- `papers` — 论文列表，每篇包含 title, abstract, arxiv_id, rule_score, matched_domain, matched_keywords 等

## Step 4: AI 评分 Top 20

对 JSON 中的 Top 20 候选论文进行 AI 评分。

**研究兴趣上下文**：引用 Step 1 读取的 `research_domains` 配置内容。

**对每篇论文评估**：

输入：
- Title: {paper.title}
- Abstract: {paper.abstract}
- Matched domain: {paper.matched_domain}

输出 JSON 格式（每篇）：
```json
{
  "arxiv_id": "2406.12345",
  "ai_score": 7.5,
  "recommendation": "一句话推荐理由"
}
```

**评分标准**：
- 9-10: 直接相关且有重大创新
- 7-8: 高度相关，方法有新意
- 5-6: 相关但增量工作
- 3-4: 边缘相关
- 0-2: 低相关

**验证**：分数必须是 0-10 的数字。非法输出按 5.0 处理。

**计算 final_score**：

```
final_score = rule_score * 0.6 + ai_score * 0.4
```

按 final_score 降序排列，取 Top 10。

## Step 5: 生成每日推荐笔记

生成文件路径：`$VAULT_PATH/10_Daily/YYYY-MM-DD-论文推荐.md`（使用目标日期）

笔记结构：

```markdown
---
date: YYYY-MM-DD
type: daily-recommendation
papers_count: 10
---

# YYYY-MM-DD 论文推荐

## 今日概览

（总结今日论文的整体趋势、亮点主题、阅读建议。2-3 句话。）

---

## Top 3 详细推荐

### 1. {Paper Title}

> **领域**: {domain} | **评分**: {final_score}/10 | **arXiv**: [{arxiv_id}]({url})

**推荐理由**: {recommendation}

（对每篇 Top 3 论文调用 /paper-analyze 生成详细笔记，并在此处写一段 3-5 句的详细分析：
- 核心贡献
- 方法亮点
- 与用户研究方向的关联）

→ 详细笔记: [[Paper-Title-Slug]]

### 2. ...
### 3. ...

---

## 其他推荐

| # | 论文 | 领域 | 评分 | 推荐理由 |
|---|------|------|------|----------|
| 4 | [{title}]({url}) | {domain} | {final_score} | {recommendation} |
| 5 | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
| 10 | ... | ... | ... | ... |
```

**Top 3 详细笔记生成**：对排名前 3 的论文，分别调用 paper-analyze 的 generate_note.py 获取完整元数据，然后按 paper-analyze 的流程生成论文笔记到 `20_Papers/<domain>/` 目录。

## Step 6: Wikilink 与断链检查

生成笔记时，将论文标题和 Insight 技术点名称内嵌为 `[[wikilink]]`。具体做法：

1. 使用 Obsidian CLI 获取已有的 Insight 笔记列表：
   ```bash
   obsidian files folder=30_Insights ext=md
   ```
2. 生成笔记内容时，将匹配的 Insight 名称写为 `[[name]]` 格式
3. 笔记写入后，用 Obsidian CLI 检查断链：
   ```bash
   obsidian unresolved format=json
   ```
4. 如果发现与今日笔记相关的未解析链接（目标不存在的 `[[wikilink]]`），在笔记末尾追加提示：
   ```
   > ⚠️ 未解析链接: [[missing-note-1]], [[missing-note-2]]
   > 可运行 `/insight-init` 创建对应主题，或检查拼写。
   ```
   如果没有断链则不追加任何内容。

## Step 7: Idea Spark 检查

读取 `$VAULT_PATH/30_Insights/` 中所有技术点文档的"矛盾与开放问题"section（只读该 section，不需要全文）。

对比今日 Top 10 论文，快速判断：
- 某篇论文的方法是否能解决某个已知开放问题？
- 某篇论文是否与某个技术点产生了意外交叉？

如果发现机会，在每日推荐笔记末尾追加：

```
---

## 💡 Idea Spark

- **{一句话描述}** — {Paper-X} 的方法可能解决 [[{技术点}]] 中的开放问题 "{问题描述}"
  → 运行 `/idea-generate --from-spark "描述"` 深入探索
```

如果没有发现机会，不追加任何内容（避免噪音）。

## 语言规范

- 论文标题和摘要保持英文原文
- 推荐理由、分析、概览使用中文
- frontmatter 字段名使用英文

## 错误处理

- 如果 search_and_filter.py 失败，展示错误信息并建议检查网络或运行 `/config`
- 如果某篇论文的 paper-analyze 失败，跳过该篇继续处理其他论文
- 最终告知用户成功处理了多少篇论文
