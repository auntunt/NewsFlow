# NewsFlow

AI-powered news aggregation, processing and distribution pipeline.

Combines the best of [Horizon](https://github.com/Thysrael/Horizon), [TrendRadar](https://github.com/sansan0/TrendRadar), and [InfoStream](https://github.com/yeyitech/infostream) into a unified, modular system.

## Features

- **Multi-source collection** — Hacker News, GitHub Trending, RSS, Chinese trending (via newsnow)
- **AI scoring & filtering** — batch-scores items with any LLM via litellm
- **YAML-driven workflows** — define your pipeline in a single config file
- **MCP server** — expose the pipeline as tools for AI agents
- **CLI** — run workflows from the command line

## Quickstart

```bash
# install
uv pip install -e .

# configure
cp .env.example .env
# edit .env: set DEEPSEEK_API_KEY (or OPENAI_API_KEY)

# run a workflow
newsflow run tech_daily

# list recent runs
newsflow list

# show filtered items from a run
newsflow show <run_id>
```

## Workflow YAML

```yaml
name: tech_daily
hours: 24

collectors:
  - type: hackernews
    limit: 60
  - type: github_trending
    limit: 30

filter:
  threshold: 7.0
  max_items: 15
```

## MCP Server

```bash
newsflow mcp
```

Exposes tools: `nf_run_workflow`, `nf_collect`, `nf_list_runs`, `nf_get_items`, `nf_get_stats`, `nf_list_workflows`.

## Architecture

```
collectors/    ← fetch raw ContentItems (HN, GitHub, RSS, newsnow...)
processors/    ← dedup + AI score + filter
generators/    ← AI rewrite for target platform  [Phase 3]
formatters/    ← wechat HTML, xiaohongshu text   [Phase 3]
publishers/    ← wechat, xiaohongshu, feishu      [Phase 4]
pipeline/      ← YAML workflow engine
mcp/           ← FastMCP server
```

## Phases

| Phase | Status | Contents |
|-------|--------|----------|
| 1 | ✅ Done | models, collectors (HN/GitHub/RSS/newsnow), config |
| 2 | ✅ Done | AI client (litellm), scorer, filter, storage, pipeline engine, MCP, CLI |
| 3 | 🔜 | generators (AI rewrite), formatters (wechat/xiaohongshu) |
| 4 | 🔜 | publishers (wechat draft, xiaohongshu, feishu webhook) |
